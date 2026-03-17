from sqlalchemy.future import select
from database.models import Provider, ProviderAccount
from database.session import AsyncSessionLocal

async def get_route(account):
    """
    Motor de roteamento segmentado (WHITE, BLACK, RED) com verificação de contingência.
    """
    async with AsyncSessionLocal() as db:
        segment = getattr(account, 'segment', 'BLACK').upper() if getattr(account, 'segment', None) else "BLACK"

        # --- LÓGICA WHITE ---
        if segment == "WHITE" and getattr(account, 'fixed_provider_id', None):
            return account.fixed_provider_id

        # --- LÓGICA RED (Cluster de Contingência) ---
        if segment == "RED":
            query = (
                select(Provider, ProviderAccount)
                .join(ProviderAccount)
                .where(
                    Provider.segment_tags == 'RED_CLUSTER',
                    ProviderAccount.is_active == True
                )
                .order_by(Provider.priority.desc())
            )
            res = await db.execute(query)
            candidates = res.all()

            for prov, pa in candidates:
                # Verifica se ainda tem margem no limite diário
                if pa.current_daily_volume < pa.daily_limit or pa.daily_limit == 0:
                    return prov.id
            
            return None # Nenhum motor RED disponível

        # --- LÓGICA BLACK (Global Default) ---
        query = (
            select(Provider, ProviderAccount)
            .join(ProviderAccount)
            .where(ProviderAccount.is_active == True)
            .order_by(Provider.priority.desc())
        )
        res = await db.execute(query)
        match = res.all()
        return match[0][0].id if match else None
