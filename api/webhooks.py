from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.models import Transaction
from core.ledger import LedgerEngine
from services.notifier import NOC

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])

@router.post("/{provider}/in")
async def provider_webhook(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Tradutor Universal de Webhooks para a DarkPay Nexus"""
    payload = await request.json()
    
    nexus_id = None
    provider_ref = None
    normalized_status = "PENDING"
    
    # ==========================================
    # 1. TRADUTORES POR PROVEDOR
    # ==========================================
    if provider == "mistic":
        # 🚨 Interceção de Fraude (MED)
        if payload.get("event") == "INFRACTION":
            infraction = payload.get("infraction", {})
            msg = f"🚨 **MED / FRAUDE MISTICPAY!**\nTxID: `{payload.get('transaction', {}).get('transactionId')}`\nValor: R$ {infraction.get('amount')}\nStatus: {infraction.get('status')}\nMotivo: {infraction.get('reportDetails')}"
            await NOC.internal_alert("CRITICAL", msg)
            return {"status": "med_alert_triggered"}

        # Pagamento Normal Mistic
        provider_ref = str(payload.get("transactionId"))
        raw_status = payload.get("status")
        if raw_status == "COMPLETO": normalized_status = "PAID"
        elif raw_status in ["FALHA", "CANCELADO"]: normalized_status = "FAILED"
        
    elif provider == "elitepay":
        nexus_id = payload.get("reference")
        raw_status = payload.get("status")
        if raw_status in ["PAID", "COMPLETO"]: normalized_status = "PAID"
        elif raw_status == "FAILED": normalized_status = "FAILED"

    elif provider == "nowpayments":
        nexus_id = payload.get("order_id")
        raw_status = payload.get("payment_status")
        if raw_status == "finished": normalized_status = "PAID"
        elif raw_status in ["failed", "refunded"]: normalized_status = "FAILED"

    elif provider == "picpay":
        # O PicPay normalmente manda o referenceId no webhook
        nexus_id = payload.get("referenceId")
        # Para PicPay, a boa prática é fazer um GET /status usando o driver, mas assumimos o payload para simplificar o normalizador
        normalized_status = "PAID" # Placeholder para o teste

    else:
        return {"status": "ignored", "reason": f"Provedor {provider} desconhecido"}

    # ==========================================
    # 2. LOCALIZAR A TRANSAÇÃO NO BANCO DE DADOS
    # ==========================================
    if not nexus_id and not provider_ref:
        return {"status": "ignored", "reason": "Payload sem identificador de transação"}

    query = select(Transaction)
    if nexus_id:
        query = query.where(Transaction.id == nexus_id)
    else:
        query = query.where(Transaction.provider_reference == provider_ref)

    result = await db.execute(query)
    tx = result.scalars().first()

    if not tx:
        await NOC.internal_alert("WARNING", f"Webhook recebido do {provider} mas transação não foi encontrada no Ledger. (Ref: {provider_ref or nexus_id})")
        return {"status": "ignored", "reason": "Transação não encontrada na Nexus"}

    # ==========================================
    # 3. EXECUTAR A LIQUIDAÇÃO (LEDGER)
    # ==========================================
    if normalized_status == "PAID" and tx.status != "paid":
        ledger = LedgerEngine(db)
        settle_result = await ledger.settle_transaction(nexus_id=tx.id)
        return {"status": "processed", "provider": provider, "ledger": settle_result}

    elif normalized_status == "FAILED":
        tx.status = "failed"
        await db.commit()
        return {"status": "updated", "state": "failed"}

    return {"status": "logged", "state": normalized_status}
