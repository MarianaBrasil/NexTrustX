from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from database.models import Transaction, LedgerEntry, Balance, App
from services.notifier import NOC

class LedgerEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    def calculate_fees(self, amount: float, method: str, fee_config: dict) -> float:
        """Motor inteligente de precificação"""
        # Ex: method = "pix_in", "crypto_exchange", "internal_transfer"
        rules = fee_config.get(method, {})
        
        # Padrão de segurança se a filial não tiver regra: 5% + R$ 1.00
        base_percent = rules.get("percent", 0.05)
        fixed_fee = rules.get("fixed", 1.00)
        
        # Lógica condicional (Se o valor for menor que X, a taxa muda)
        threshold = rules.get("threshold_amount")
        if threshold and amount < threshold:
            base_percent = rules.get("threshold_percent", base_percent)
            fixed_fee = rules.get("threshold_fixed", fixed_fee)
            
        fee = (amount * base_percent) + fixed_fee
        return round(fee, 2)

    async def settle_transaction(self, nexus_id: str):
        result = await self.db.execute(
            select(Transaction)
            .options(joinedload(Transaction.app).joinedload(App.account))
            .where(Transaction.id == nexus_id)
        )
        tx = result.scalars().first()
        
        if not tx: raise HTTPException(status_code=404, detail="Transação não encontrada")
        if tx.status == "paid": return {"status": "already_paid"}

        bal_res = await self.db.execute(select(Balance).where(Balance.account_id == tx.app.account_id, Balance.currency == tx.currency))
        balance = bal_res.scalars().first()

        # 🎯 CHAMA O MOTOR DE CÁLCULO INTELIGENTE
        fee_amount = self.calculate_fees(tx.amount, tx.method, tx.app.account.fee_config)
        
        # Prevenção: A taxa nunca pode ser maior que o valor do pagamento
        if fee_amount > tx.amount: fee_amount = tx.amount
        net_amount = round(tx.amount - fee_amount, 2)

        credit_entry = LedgerEntry(account_id=tx.app.account_id, transaction_id=tx.id, currency=tx.currency, amount=net_amount, entry_type="credit")
        fee_entry = LedgerEntry(account_id=tx.app.account_id, transaction_id=tx.id, currency=tx.currency, amount=fee_amount, entry_type="fee")
        
        self.db.add_all([credit_entry, fee_entry])
        tx.status = "paid"
        if balance: balance.available_balance += net_amount

        await self.db.commit()

        # NOC Alerts...
        tier = tx.app.account.tier
        msg_internal = f"Pagamento!\nID: `{tx.id}`\nSubsidiária: {tx.app.account.name} (Tier: {tier})\nValor: R$ {tx.amount}\nFee: R$ {fee_amount}"
        await NOC.internal_alert("SUCCESS", msg_internal)
        
        if tx.app.telegram_chat_id or tx.app.discord_webhook:
            msg_client = f"Recebimento!\nProjeto: {tx.app.name}\nLíquido: R$ {net_amount}"
            await NOC.client_alert(tx.app, msg_client)

        return {"status": "settled", "net_amount": net_amount, "fee_collected": fee_amount}
