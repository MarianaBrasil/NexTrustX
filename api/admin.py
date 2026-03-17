from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database.session import get_db
from database.models import NocTicket, TicketStatus, Transaction, Balance, LedgerEntry

# 📡 Importamos a nossa metralhadora de Webhooks
from services.webhooks import send_webhook

admin_router = APIRouter(prefix="/v1/admin", tags=["NOC Admin"])

@admin_router.post("/tickets/{ticket_id}/transit")
async def ticket_mark_transit(ticket_id: str, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(NocTicket).where(NocTicket.id == ticket_id))
    ticket = query.scalars().first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    ticket.status = TicketStatus.IN_PROGRESS
    tx_query = await db.execute(select(Transaction).where(Transaction.amount == ticket.amount, Transaction.status == "pending_manual"))
    transaction = tx_query.scalars().first()
    if transaction: transaction.status = "processing_web3"
    
    await db.commit()
    return {"success": True, "message": "BRL Confirmado."}

@admin_router.post("/tickets/{ticket_id}/settle")
async def ticket_settle_funds(ticket_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(NocTicket).where(NocTicket.id == ticket_id))
    ticket = query.scalars().first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket não encontrado")

    tx_query = await db.execute(
        select(Transaction).options(selectinload(Transaction.app)).where(Transaction.amount == ticket.amount, Transaction.status.in_(["pending_manual", "processing_web3"]))
    )
    transaction = tx_query.scalars().first()
    if not transaction: raise HTTPException(status_code=404, detail="Transação não encontrada")

    fee_rate = 0.25 if transaction.method == "pix_red" else 0.05
    fee_amount = transaction.amount * fee_rate
    net_amount = transaction.amount - fee_amount

    bal_query = await db.execute(select(Balance).where(Balance.account_id == transaction.app.account_id))
    balance = bal_query.scalars().first()
    balance.available_balance += net_amount

    ticket.status = TicketStatus.RESOLVED
    transaction.status = "PAID"

    db.add(LedgerEntry(account_id=transaction.app.account_id, transaction_id=transaction.id, amount=net_amount, entry_type="CREDIT"))
    db.add(LedgerEntry(account_id=transaction.app.account_id, transaction_id=transaction.id, amount=fee_amount, entry_type="FEE_DEDUCTION"))
    
    await db.commit()

    # 📡 DISPARO DO WEBHOOK (PAY-IN CONCLUÍDO)
    webhook_url = transaction.app.payout_settings.get("webhook_url") if transaction.app.payout_settings else None
    if webhook_url:
        payload = {"transaction_id": transaction.id, "amount": transaction.amount, "net_amount": net_amount, "status": "PAID", "type": "PAY_IN"}
        background_tasks.add_task(send_webhook, webhook_url, "payment.success", payload, transaction.app.api_key)

    return {"success": True, "message": f"Liquidação de R$ {net_amount:.2f} concluída."}

@admin_router.post("/tickets/{ticket_id}/approve_withdraw")
async def approve_withdrawal(ticket_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = await db.execute(select(NocTicket).where(NocTicket.id == ticket_id))
    ticket = query.scalars().first()
    if not ticket: raise HTTPException(status_code=404, detail="Ticket não encontrado")

    tx_query = await db.execute(
        select(Transaction).options(selectinload(Transaction.app)).where(Transaction.amount == ticket.amount, Transaction.status == "processing")
    )
    transaction = tx_query.scalars().first()
    if not transaction: raise HTTPException(status_code=404, detail="Transação de saque não encontrada")

    bal_query = await db.execute(select(Balance).where(Balance.account_id == transaction.app.account_id))
    balance = bal_query.scalars().first()
    balance.pending_balance -= transaction.amount 

    ticket.status = TicketStatus.RESOLVED
    transaction.status = "PAID"

    db.add(LedgerEntry(account_id=transaction.app.account_id, transaction_id=transaction.id, amount=transaction.amount, entry_type="DEBIT_CASHOUT"))
    await db.commit()
    
    # 📡 DISPARO DO WEBHOOK (CASH-OUT CONCLUÍDO)
    webhook_url = transaction.app.payout_settings.get("webhook_url") if transaction.app.payout_settings else None
    if webhook_url:
        payload = {"transaction_id": transaction.id, "amount": transaction.amount, "status": "PAID", "type": "CASH_OUT"}
        background_tasks.add_task(send_webhook, webhook_url, "withdrawal.success", payload, transaction.app.api_key)

    return {"success": True, "message": f"Saque de R$ {transaction.amount:.2f} aprovado e finalizado no Ledger."}
