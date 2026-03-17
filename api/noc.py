from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount
import time

noc_router = APIRouter(prefix="/v2/noc", tags=["NOC - Command Center"])
NOC_SECRET_TOKEN = "NeXtrustX_NOC_V2_Alpha"

async def verify_noc_access(x_noc_token: str = Header(None)):
    if x_noc_token != NOC_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Acesso Proibido")

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
                "daily_limit": pa.daily_limit,
                "costs": pa.cost_config,
                "health": "OK" if pa.is_active else "OFFLINE"
            })
        return {"timestamp": time.time(), "status": "Ready", "engines": engines}

@noc_router.patch("/engine/{engine_name}/toggle", dependencies=[Depends(verify_noc_access)])
async def toggle_engine(engine_name: str, active: bool):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProviderAccount).join(Provider).where(Provider.name == engine_name.lower())
        )
        pa = result.scalars().first()
        if not pa:
            raise HTTPException(status_code=404, detail="Motor não encontrado")

        pa.is_active = active
        await db.commit()
        return {"status": "success", "engine": engine_name, "new_state": "ACTIVE" if active else "DISABLED"}

@noc_router.patch("/engine/{engine_name}/priority", dependencies=[Depends(verify_noc_access)])
async def set_priority(engine_name: str, priority: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Provider).where(Provider.name == engine_name.lower()))
        prov = result.scalars().first()
        if not prov:
            raise HTTPException(status_code=404, detail="Motor não encontrado")

        prov.priority = priority
        await db.commit()
        return {"status": "success", "engine": engine_name, "new_priority": priority}
