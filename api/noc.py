from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.future import select
from sqlalchemy import text
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount
import time
import os

noc_router = APIRouter(prefix="/v2/noc", tags=["NOC - Command Center"])

# Token agora é lido com segurança das variáveis de ambiente
NOC_SECRET_TOKEN = os.getenv("NOC_SECRET_TOKEN", "fallback_token_seguro")

async def verify_noc_access(x_noc_token: str = Header(None)):
    if x_noc_token != NOC_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Acesso Proibido")

async def log_audit(db, request: Request, action: str, target: str, details: str):
    """Regista a ação no rasto de auditoria"""
    ip = request.client.host
    query = text("INSERT INTO audit_logs (ip_address, action, target_engine, details) VALUES (:ip, :action, :target, :details)")
    await db.execute(query, {"ip": ip, "action": action, "target": target, "details": details})
    await db.commit()

@noc_router.get("/engines", dependencies=[Depends(verify_noc_access)])
async def get_engines_health():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Provider, ProviderAccount)
            .join(ProviderAccount)
            .order_by(Provider.priority.desc())
        )
        
        engines = []
        for prov, pa in result.all():
            engines.append({
                "id": prov.id,
                "name": prov.name.upper(),
                "priority": prov.priority,
                "active": pa.is_active,
                "is_critical": getattr(prov, 'is_critical', False),
                "tags": getattr(prov, 'segment_tags', 'GLOBAL'),
                "health": "OK" if pa.is_active else "OFFLINE"
            })
        return {"timestamp": time.time(), "engines": engines}

@noc_router.patch("/engine/{engine_name}/toggle", dependencies=[Depends(verify_noc_access)])
async def toggle_engine(engine_name: str, active: bool, request: Request):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProviderAccount).join(Provider).where(Provider.name == engine_name.lower())
        )
        pa = result.scalars().first()
        if not pa:
            raise HTTPException(status_code=404, detail="Motor não encontrado")

        old_state = "ACTIVE" if pa.is_active else "DISABLED"
        new_state = "ACTIVE" if active else "DISABLED"
        
        pa.is_active = active
        
        # Log de Auditoria
        await log_audit(db, request, "TOGGLE_STATE", engine_name, f"Mudança de {old_state} para {new_state}")
        
        await db.commit()
        return {"status": "success", "engine": engine_name, "new_state": new_state}

@noc_router.patch("/engine/{engine_name}/priority", dependencies=[Depends(verify_noc_access)])
async def set_priority(engine_name: str, priority: int, request: Request):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Provider).where(Provider.name == engine_name.lower()))
        prov = result.scalars().first()
        if not prov:
            raise HTTPException(status_code=404, detail="Motor não encontrado")

        old_priority = prov.priority
        prov.priority = priority
        
        # Log de Auditoria
        await log_audit(db, request, "SET_PRIORITY", engine_name, f"Prioridade alterada de {old_priority} para {priority}")
        
        await db.commit()
        return {"status": "success", "engine": engine_name, "new_priority": priority}
