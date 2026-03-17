from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, date

from database.session import get_db
from database.models import App, Account, Balance, Transaction, NocTicket, TicketType, TicketStatus
from services.noc import notify_critical
from services.payout import process_auto_payout

client_router = APIRouter(prefix="/v1/client", tags=["Portal do Cliente"])

async def get_app_from_key(x_api_key: str = Header(...), db: AsyncSession = Depends(get_db)):
    # Agora carregamos apenas o App, pois o Tier está no payout_settings do projeto
    query = await db.execute(
        select(App).where(App.api_key == x_api_key)
    )
    app = query.scalars().first()
    if not app:
        raise HTTPException(status_code=401, detail="Chave API inválida.")
    return app

@client_router.get("/dashboard")
async def get_client_dashboard(app: App = Depends(get_app_from_key), db: AsyncSession = Depends(get_db)):
    bal_query = await db.execute(select(Balance).where(Balance.account_id == app.account_id))
    balance = bal_query.scalars().first()
    
    # Busca o tier do projeto ou assume WHITE como padrão de onboarding
    tier = (app.payout_settings or {}).get("tier", "WHITE").upper()

    return {
        "success": True,
        "data": {
            "project_name": app.name,
            "project_tier": tier,
            "available_balance": balance.available_balance if balance else 0.0,
            "pending_balance": balance.pending_balance if balance else 0.0
        }
    }

@client_router.post("/withdraw")
async def request_withdrawal(payload: dict, background_tasks: BackgroundTasks, app: App = Depends(get_app_from_key), db: AsyncSession = Depends(get_db)):
    amount = float(payload.get("amount", 0.0))
    method = payload.get("method", "pix")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido.")

    # 1. Verificação de Saldo
    bal_query = await db.execute(select(Balance).where(Balance.account_id == app.account_id))
    balance = bal_query.scalars().first()

    if not balance or balance.available_balance < amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    # 2. Resgate de Tier e Preferências do Projeto
    settings = app.payout_settings or {}
    tier = settings.get("tier", "WHITE").upper()
    destination = settings.get("pix_key") if method == "pix" else settings.get("usdt_wallet")

    if not destination:
        raise HTTPException(status_code=400, detail=f"Destino {method} não configurado para este projeto.")

    # 3. Congelamento Ledger (Available -> Pending)
    balance.available_balance -= amount
    balance.pending_balance += amount

    # 4. Registo da Transação
    tx = Transaction(app_id=app.id, amount=amount, method=f"payout_{method}", status="processing")
    db.add(tx)
    await db.flush()

    # 5. Lógica Híbrida de Decisão
    # RED: Sempre para o NOC para circular Crypto
    if tier == "RED":
        ticket_type = TicketType.MANUAL_CASHOUT # Poderíamos criar um CRYPTO_CONVERSION
        msg = f"🔴 [PROJECT RED] {app.name} solicitou R$ {amount}. Retido para circulação Crypto."
        background_tasks.add_task(notify_critical, msg)
    
    # BLACK: Tenta Automático, mas avisa o NOC para monitorizar liquidez
    elif tier == "BLACK":
        background_tasks.add_task(process_auto_payout, tx.id)
        msg = f"⚫ [PROJECT BLACK] {app.name} solicitou R$ {amount}. Processando com monitorização de liquidez."
        background_tasks.add_task(notify_critical, msg)

    # WHITE (ou padrão): Via Verde
    else:
        background_tasks.add_task(process_auto_payout, tx.id)
        msg = f"⚪ [PROJECT WHITE] {app.name} solicitou R$ {amount}. Auto-payout iniciado."

    # Criar Ticket de Auditoria
    ticket = NocTicket(
        ticket_type=TicketType.MANUAL_CASHOUT,
        status=TicketStatus.PENDING,
        amount=amount,
        description=f"Projeto {app.name} ({tier}): {msg}"
    )
    db.add(ticket)
    
    await db.commit()

    return {
        "success": True, 
        "transaction_id": tx.id, 
        "project_tier": tier,
        "message": "Solicitação em processamento."
    }
