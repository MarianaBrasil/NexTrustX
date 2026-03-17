import asyncio
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount, Account

async def setup_elite_2():
    async with AsyncSessionLocal() as db:
        print("⚙️ A iniciar injeção do Gateway ELITE 2 no Lote 1...")

        # 1. Procurar a conta Matriz (Dona do Gateway)
        acc_query = await db.execute(select(Account).where(Account.name == "DarkMarket Matriz"))
        account = acc_query.scalars().first()
        
        if not account:
            # Fallback caso usemos o primeiro registro
            account = (await db.execute(select(Account))).scalars().first()

        # 2. Criar o Provider ELITE 2
        prov_query = await db.execute(select(Provider).where(Provider.name == 'elitepay_2'))
        provider = prov_query.scalars().first()
        
        if not provider:
            # Prioridade 80 (Ganha da Mistic e Elite 1, mas perde para o PIX Fixo 999)
            provider = Provider(name='elitepay_2', type='elitepay', priority=80) 
            db.add(provider)
            await db.flush()

        # 3. Configurar o Cofre do Gateway (Limites e Taxas)
        cred_query = await db.execute(
            select(ProviderAccount)
            .where(ProviderAccount.provider_id == provider.id)
        )
        provider_account = cred_query.scalars().first()
        
        # Estrutura de Custos Exata da Elite 2
        costs = {
            "pix_in_percent": 0.04,
            "pix_in_fixed": 0.75,
            "withdraw_fixed": 0.75,
            "crypto_out_percent": 0.04,
            "crypto_min": 20.0,
            "crypto_max": 3000.0
        }

        creds = {"client_id": "ELITE2_KEY_AQUI", "client_secret": "ELITE2_SECRET_AQUI"}
        
        if not provider_account:
            provider_account = ProviderAccount(
                provider_id=provider.id,
                account_id=account.id,
                credentials_encrypted=creds,
                is_active=True,
                daily_limit=1000.0,      # 🚨 O Limite de R$ 1000/dia
                current_daily_volume=0.0,
                cost_config=costs
            )
            db.add(provider_account)
        else:
            provider_account.credentials_encrypted = creds
            provider_account.daily_limit = 1000.0
            provider_account.cost_config = costs
            provider_account.is_active = True
            
        await db.commit()
        print(f"✅ ALVO TRANCADO: ELITE 2 configurada com Prioridade Máxima no Lote 1!")
        print(f"   Limite Diário: R$ 1.000,00")
        print(f"   Taxas PIX IN: 4% + R$ 0.75")

if __name__ == "__main__":
    asyncio.run(setup_elite_2())
