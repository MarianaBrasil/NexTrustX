import asyncio
from decimal import Decimal
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from database.session import AsyncSessionLocal
from database.models import Transaction, Balance, App, LedgerEntry
from services.fee_engine import calculate_transaction_fee
from services.notifier import NOC

async def process_payout(transaction_id: str):
    """
    Executa o saque (Payout) com proteção de concorrência e precisão Decimal.
    """
    async with AsyncSessionLocal() as db:
        # 1. Bloqueia a transação e carrega relações
        result = await db.execute(
            select(Transaction)
            .options(joinedload(Transaction.app).joinedload(App.account))
            .where(Transaction.id == transaction_id)
            .with_for_update()
        )
        tx = result.scalars().first()

        if not tx or tx.status != "pending":
            return {"error": "Transação inválida ou já processada"}

        # 2. Bloqueia o saldo do cliente para verificação
        bal_res = await db.execute(
            select(Balance)
            .where(Balance.account_id == tx.app.account_id, Balance.currency == tx.currency)
            .with_for_update()
        )
        balance = bal_res.scalars().first()

        # 3. Calcular Taxas de Saída (OUT)
        # Identifica se é rede cripto para taxas de rede
        is_crypto = "crypto" in tx.method.lower()
        fee_amount, total_to_deduct = calculate_transaction_fee(
            tx.app.account, tx.amount, "OUT", is_bep20=is_crypto
        )
        
        # O custo total para o cliente é: Valor solicitado + Taxa da NexTrustX
        # Nota: net_amount aqui no fee_engine para 'OUT' funciona como o montante total a retirar
        required_funds = Decimal(str(tx.amount)) + fee_amount

        if not balance or balance.available_balance < required_funds:
            tx.status = "failed"
            await db.commit()
            return {"error": "Saldo insuficiente", "required": float(required_funds)}

        # 4. Execução Contabilística (Antes de chamar o driver externo)
        balance.available_balance -= required_funds
        
        debit_entry = LedgerEntry(
            account_id=tx.app.account_id,
            transaction_id=tx.id,
            currency=tx.currency,
            amount=Decimal(str(tx.amount)),
            entry_type="payout_debit"
        )
        fee_entry = LedgerEntry(
            account_id=tx.app.account_id,
            transaction_id=tx.id,
            currency=tx.currency,
            amount=fee_amount,
            entry_type="payout_fee"
        )
        
        db.add_all([debit_entry, fee_entry])
        
        # 5. Aqui chamarias o Driver Real (Mistic/Elite/etc)
        # Simulando sucesso do driver:
        tx.status = "completed"
        
        await db.commit()
        
        # Alerta NOC
        await NOC.internal_alert("INFO", f"💸 *Saída Processada*\nCliente: {tx.app.account.name}\nValor: R$ {tx.amount}\nTaxa: R$ {fee_amount}")
        
        return {"status": "success", "tx_id": tx.id, "fee": float(fee_amount)}
