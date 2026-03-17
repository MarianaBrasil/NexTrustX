import asyncio
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount, Account

async def setup_elites():
    async with AsyncSessionLocal() as db:
        print("⚙️ A iniciar injeção/atualização das ELITES 2 e 3...")

        # 1. Procurar a conta Matriz
        acc_query = await db.execute(select(Account).where(Account.name == "DarkMarket Matriz"))
        account = acc_query.scalars().first()
        if not account:
            account = (await db.execute(select(Account))).scalars().first()

        # Estrutura de Custos partilhada
        costs = {
            "pix_in_percent": 0.04,
            "pix_in_fixed": 0.75,
            "withdraw_fixed": 0.75,
            "crypto_out_percent": 0.04,
            "crypto_min": 20.0,
            "crypto_max": 3000.0
        }

        # ==========================================
        # 🟢 CONFIGURAR ELITE 2 (PRIORIDADE 80)
        # ==========================================
        prov_query_2 = await db.execute(select(Provider).where(Provider.name == 'elitepay_2'))
        provider_2 = prov_query_2.scalars().first()
        if not provider_2:
            provider_2 = Provider(name='elitepay_2', type='elitepay', priority=80) 
            db.add(provider_2)
            await db.flush()
        else:
            provider_2.priority = 80 # Garante a prioridade máxima

        # ⚠️ INSIRA AS CREDENCIAIS DA ELITE 2 AQUI:
        creds_2 = {
            "client_id": "ep_b58aa8f10b0a09a01cc77317e100ae45", 
            "client_secret": "eps_c6c4ba1d88a7509767763781eca278254660016522325c3c0bb0892c873f3232"
        }

        cred_query_2 = await db.execute(select(ProviderAccount).where(ProviderAccount.provider_id == provider_2.id))
        pa_2 = cred_query_2.scalars().first()
        
        if not pa_2:
            pa_2 = ProviderAccount(provider_id=provider_2.id, account_id=account.id, credentials_encrypted=creds_2, is_active=True, daily_limit=1000.0, current_daily_volume=0.0, cost_config=costs)
            db.add(pa_2)
        else:
            pa_2.credentials_encrypted = creds_2
            pa_2.daily_limit = 1000.0
            pa_2.cost_config = costs
            pa_2.is_active = True

        # ==========================================
        # 🟡 CONFIGURAR ELITE 3 (PRIORIDADE 75)
        # ==========================================
        prov_query_3 = await db.execute(select(Provider).where(Provider.name == 'elitepay_3'))
        provider_3 = prov_query_3.scalars().first()
        if not provider_3:
            provider_3 = Provider(name='elitepay_3', type='elitepay', priority=75) # 2ª na fila
            db.add(provider_3)
            await db.flush()
        else:
            provider_3.priority = 75

        # ⚠️ INSIRA AS CREDENCIAIS DA ELITE 3 AQUI:
        creds_3 = {
            "client_id": "ep_3bfc6076c54b8ed566fa522099cefb7e", 
            "client_secret": "eps_e6ba997b0ed13d3160a044056b5cf5c329e79d238dea205aa1d35daca3b1e4bc"
        }

        cred_query_3 = await db.execute(select(ProviderAccount).where(ProviderAccount.provider_id == provider_3.id))
        pa_3 = cred_query_3.scalars().first()

        if not pa_3:
            pa_3 = ProviderAccount(provider_id=provider_3.id, account_id=account.id, credentials_encrypted=creds_3, is_active=True, daily_limit=1000.0, current_daily_volume=0.0, cost_config=costs)
            db.add(pa_3)
        else:
            pa_3.credentials_encrypted = creds_3
            pa_3.daily_limit = 1000.0
            pa_3.cost_config = costs
            pa_3.is_active = True

        await db.commit()
        print("✅ ELITE 2 ATUALIZADA (Prioridade 80)")
        print("✅ ELITE 3 INJETADA (Prioridade 75)")
        print("🎯 Ambas com Limite de R$ 1.000/dia e prontas a disparar!")

if __name__ == "__main__":
    asyncio.run(setup_elites())
