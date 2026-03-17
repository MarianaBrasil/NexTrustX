from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.models import App, Transaction, Provider, ProviderAccount, NocTicket, TicketType, TicketStatus
from core.switcher import SwitcherEngine

from drivers.mistic_driver import MisticDriver
from drivers.elitepay_driver import ElitePayDriver
from drivers.picpay_checkout_driver import PicPayCheckoutDriver
from drivers.fixed_pix_driver import FixedPixDriver

# 🚨 A nossa nova Sirene
from services.noc import notify_critical

router = APIRouter(prefix="/v1/payments", tags=["Payments"])

async def get_authenticated_app(x_api_key: str, db: AsyncSession) -> App:
    result = await db.execute(select(App).where(App.api_key == x_api_key))
    app = result.scalars().first()
    if not app: raise HTTPException(status_code=401, detail="API Key inválida")
    return app

# ==================================================
# 🟦 FLUXO STANDARD & HIGH-TICKET (/pix)
# ==================================================
@router.post("/pix")
async def create_pix(
    payload: dict, 
    background_tasks: BackgroundTasks, 
    x_api_key: str = Header(...), 
    db: AsyncSession = Depends(get_db)
):
    app = await get_authenticated_app(x_api_key, db)
    amount = float(payload.get("amount", 0.0))
    order_id = payload.get("order_id")

    res = {}
    provider_name = ""
    provider_id = None
    is_manual_validation = False
    ticket_desc = ""

    if amount >= 500.00:
        query = await db.execute(select(ProviderAccount).join(Provider).where(Provider.name == "picpay_checkout", ProviderAccount.is_active == True))
        picpay_route = query.scalars().first()
        fallback_to_fixo = False

        if picpay_route:
            try:
                creds = picpay_route.credentials_encrypted
                driver = PicPayCheckoutDriver(client_id=creds["client_id"], client_secret=creds["client_secret"])
                res = await driver.create_payment(amount, order_id, "https://api.dark.lat/v1/webhooks/picpay/in")
                provider_name = "picpay_checkout"
                provider_id = picpay_route.provider_id
            except Exception as e:
                fallback_to_fixo = True
        else:
            fallback_to_fixo = True

        if fallback_to_fixo:
            query_fixo = await db.execute(select(ProviderAccount).join(Provider).where(Provider.name == "pix_fixo_matriz", ProviderAccount.is_active == True))
            fixo_route = query_fixo.scalars().first()
            if not fixo_route: raise HTTPException(status_code=500, detail="Nenhum gateway High-Ticket disponível.")
            
            creds = fixo_route.credentials_encrypted
            driver = FixedPixDriver(pix_key=creds.get("pix_key", "financeiro@darkpay.lat"))
            res = await driver.create_payment(amount, order_id)
            provider_name = "pix_fixo_matriz"
            provider_id = fixo_route.provider_id
            is_manual_validation = True
            ticket_desc = f"⚠️ [FALLBACK HIGH-TICKET] Validar PIX de R$ {amount:.2f}. Ref: {order_id}"
    else:
        switcher = SwitcherEngine(db)
        best_route = await switcher.get_best_route(account_id=app.account_id, amount=amount, method="pix")
        provider_name = best_route.provider.name
        creds = best_route.credentials_encrypted
        provider_id = best_route.provider_id

        if provider_name.startswith("mistic"):
            driver = MisticDriver(client_id=creds["client_id"], client_secret=creds["client_secret"])
        elif provider_name.startswith("elitepay"):
            driver = ElitePayDriver(client_id=creds["client_id"], client_secret=creds["client_secret"])
        
        res = await driver.create_pix_deposit(amount, order_id, "Cliente", "00000000000")

    if not res.get("success"):
        raise HTTPException(status_code=400, detail=f"Falha no gateway {provider_name}: {res.get('error')}")

    if is_manual_validation:
        ticket = NocTicket(ticket_type=TicketType.MANUAL_VALIDATION, status=TicketStatus.PENDING, amount=amount, provider_id=provider_id, description=ticket_desc)
        db.add(ticket)
        # 🚨 TOCA A SIRENE EM SEGUNDO PLANO
        background_tasks.add_task(notify_critical, ticket_desc)

    status_tx = "pending_manual" if is_manual_validation else "pending"
    tx = Transaction(app_id=app.id, provider_id=provider_id, provider_reference=res.get("transaction_id"), amount=amount, method="pix", status=status_tx)
    db.add(tx)
    await db.commit()

    return {"success": True, "nexus_id": tx.id, "provider_used": provider_name, "pix_code": res.get("pix_code"), "manual_validation_required": is_manual_validation}

# ==================================================
# 🚨 FLUXO RED (Urgência Operacional / Crypto Instantânea)
# ==================================================
@router.post("/red/pix")
async def create_red_pix(
    payload: dict, 
    background_tasks: BackgroundTasks, 
    x_api_key: str = Header(...), 
    db: AsyncSession = Depends(get_db)
):
    app = await get_authenticated_app(x_api_key, db)
    amount = float(payload.get("amount", 0.0))
    order_id = payload.get("order_id")

    query_fixo = await db.execute(select(ProviderAccount).join(Provider).where(Provider.name == "pix_fixo_matriz"))
    fixo_route = query_fixo.scalars().first()
    if not fixo_route: raise HTTPException(status_code=500, detail="Matriz RED não configurada.")
    
    creds = fixo_route.credentials_encrypted
    driver = FixedPixDriver(pix_key=creds.get("pix_key", "financeiro@darkpay.lat"))
    res = await driver.create_payment(amount, order_id)
    
    if not res.get("success"): raise HTTPException(status_code=400, detail="Falha na geração RED.")

    fee_estimate = amount * 0.25
    ticket_desc = f"🔴 [FLUXO RED] URGÊNCIA! Validar entrada de R$ {amount:.2f}. Fee retida: R$ {fee_estimate:.2f}. Liberar Crypto Imediato para Cliente {app.name}. Ref: {order_id}"
    
    ticket = NocTicket(
        ticket_type=TicketType.MANUAL_VALIDATION, 
        status=TicketStatus.PENDING, 
        amount=amount, 
        provider_id=fixo_route.provider_id, 
        description=ticket_desc
    )
    db.add(ticket)
    
    # 🚨 TOCA A SIRENE EM SEGUNDO PLANO
    background_tasks.add_task(notify_critical, ticket_desc)

    tx = Transaction(app_id=app.id, provider_id=fixo_route.provider_id, provider_reference=res.get("transaction_id"), amount=amount, method="pix_red", status="pending_manual")
    db.add(tx)
    await db.commit()

    return {"success": True, "nexus_id": tx.id, "provider_used": "pix_fixo_matriz_red", "pix_code": res.get("pix_code"), "manual_validation_required": True, "route": "RED"}
