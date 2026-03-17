import asyncio
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount, Account

async def setup_pix_fixo():
    async with AsyncSessionLocal() as db:
        # 1. Procurar a conta principal (ex: XDeals)
        acc_query = await db.execute(select(Account))
        account = acc_query.scalars().first()
        
        if not account:
            print("❌ Nenhuma conta encontrada. Cria a conta primeiro!")
            return

        # 2. Criar ou Atualizar o Provider (O Motor)
        prov_query = await db.execute(select(Provider).where(Provider.name == 'pix_fixo_matriz'))
        provider = prov_query.scalars().first()
        
        if not provider:
            provider = Provider(name='pix_fixo_matriz', type='pix_fixo', priority=1) # Prioridade 1 (Máxima)
            db.add(provider)
            await db.commit()
            await db.refresh(provider)

        # 3. Criar ou Atualizar a ProviderAccount (O Cofre com a Chave e Limites)
        cred_query = await db.execute(
            select(ProviderAccount)
            .where(ProviderAccount.provider_id == provider.id, ProviderAccount.account_id == account.id)
        )
        provider_account = cred_query.scalars().first()
        
        creds = {"pix_key": "013b653e-ee5a-42e0-a365-2e8138cb5d70"}
        
        if not provider_account:
            provider_account = ProviderAccount(
                provider_id=provider.id,
                account_id=account.id,
                credentials_encrypted=creds,
                is_active=True,
                daily_limit=30000.0,
                current_daily_volume=0.0
            )
            db.add(provider_account)
        else:
            provider_account.credentials_encrypted = creds
            provider_account.daily_limit = 30000.0
            provider_account.is_active = True
            
        await db.commit()
        print("✅ ALVO TRANCADO: Gateway PIX Fixo (RP_PJ001) configurado com Limite de R$ 30.000!")

if __name__ == "__main__":
    asyncio.run(setup_pix_fixo())
