from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from database.models import ProviderAccount

class SwitcherEngine:
    """Motor de Roteamento Inteligente DarkPay Nexus"""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_best_route(self, account_id: str, amount: float, method: str = "pix") -> ProviderAccount:
        # 1. Busca todos os provedores ATIVOS ligados a esta conta
        query = (
            select(ProviderAccount)
            .options(joinedload(ProviderAccount.provider))
            .where(
                ProviderAccount.account_id == account_id,
                ProviderAccount.is_active == True
            )
        )
        result = await self.db.execute(query)
        available_routes = result.scalars().all()

        if not available_routes:
            raise HTTPException(status_code=400, detail="Nenhuma rota ativa configurada para esta conta.")

        valid_routes = []
        for route in available_routes:
            # Verifica se o método bate certo (ex: PIX vs Crypto)
            if route.provider.type != method:
                continue
            
            # 2. VERIFICAÇÃO DE SAÚDE E LIMITES
            # Se daily_limit for 0, consideramos ilimitado.
            if route.daily_limit > 0:
                if (route.current_daily_volume + amount) > route.daily_limit:
                    continue # 🛑 Limite estourado! Salta para o próximo provedor.

            valid_routes.append(route)

        if not valid_routes:
            raise HTTPException(status_code=400, detail="Operação negada: Todas as rotas disponíveis atingiram o limite de volume diário ou não suportam o método.")

        # 3. ORDENAÇÃO POR PRIORIDADE (Podes depois evoluir para ordenar por "Custo Mais Baixo")
        valid_routes.sort(key=lambda x: x.provider.priority)

        # Retorna o vencedor (A Rota 1)
        best_route = valid_routes[0]
        
        return best_route
