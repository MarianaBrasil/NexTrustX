from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from decimal import Decimal
from database.models import Transaction, LedgerEntry, Balance, App
from services.notifier import NOC
from services.fee_engine import calculate_transaction_fee

class LedgerEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def settle_transaction(self, nexus_id: str):
        # 1. Trava a Transação para evitar processamento duplo (FOR UPDATE)
        result = await self.db.execute(
            select(Transaction)
            .options(joinedload(Transaction.app).joinedload(App.account))
            .where(Transaction.id == nexus_id)
            .with_for_update() 
        )
        tx = result.scalars().first()

        if not tx: raise HTTPException(status_code=404, detail="Transação não encontrada")
        if tx.status == "paid": return {"status": "already_paid"}

        # 2. Trava o Saldo do Cliente (Atomicidade)
        bal_res = await self.db.execute(
            select(Balance)
            .where(Balance.account_id == tx.app.account_id, Balance.currency == tx.currency)
            .with_for_update()
        )
        balance = bal_res.scalars().first()
        
        if not balance:
            # Se não houver conta de saldo, criamos uma agora (Safety First)
            balance = Balance(account_id=tx.app.account_id, currency=tx.currency, available_balance=Decimal('0.0'))
            self.db.add(balance)

        # 🎯 3. CHAMA O NOVO MOTOR DECIMAL
        # Identificamos se é BEP20 pelo método ou provedor (exemplo simplificado)
        is_crypto = "crypto" in tx.method.lower()
        fee_amount, net_amount = calculate_transaction_fee(tx.app.account, tx.amount, "IN", is_bep20=is_crypto)

        # 4. Registos Contabilísticos (Double-Entry logic)
        credit_entry = LedgerEntry(
            account_id=tx.app.account_id, 
            transaction_id=tx.id, 
            currency=tx.currency, 
            amount=net_amount, 
            entry_type="credit"
        )
        
        # O lucro vai para o ledger com um marcador claro de MARKUP
        fee_entry = LedgerEntry(
            account_id=tx.app.account_id, 
            transaction_id=tx.id, 
            currency=tx.currency, 
            amount=fee_amount, 
            entry_type="fee_markup"
        )

        self.db.add_all([credit_entry, fee_entry])
        
        # Atualização Crítica
        tx.status = "paid"
        balance.available_balance += net_amount # Agora usando Decimal com segurança

        await self.db.commit()

        # Alertas do NOC
        segment = getattr(tx.app.account, 'segment', 'UNKNOWN')
        msg_internal = (
            f"✅ *Liquidação Concluída*\n"
            f"ID: `{tx.id}`\n"
            f"Segmento: {segment}\n"
            f"Valor: R$ {tx.amount}\n"
            f"Taxa Retida: R$ {fee_amount}\n"
            f"Líquido p/ Cliente: R$ {net_amount}"
        )
        await NOC.internal_alert("SUCCESS", msg_internal)

        return {"status": "settled", "net_amount": float(net_amount), "fee_collected": float(fee_amount)}
