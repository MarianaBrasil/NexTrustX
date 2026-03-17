import asyncio
from database.session import AsyncSessionLocal
from database.models import Account, App, Provider, ProviderAccount, Balance, User

async def seed():
    async with AsyncSessionLocal() as db:
        print("🌱 Construindo a Árvore de Holdings e Subsidiárias...")
        
        elitepay = Provider(name="elitepay", type="pix", priority=20)
        db.add(elitepay)
        await db.flush()

        # ==========================================
        # 1. HOLDING MÃE (A entidade legal)
        # ==========================================
        holding_xdeals = Account(name="XDeals Group", account_type="HOLDING", tier="DIAMOND")
        db.add(holding_xdeals)
        await db.flush()
        
        # CEO tem acesso à Holding (e futuramente herdará às filiais)
        db.add(User(account_id=holding_xdeals.id, name="Ghost CEO", email="ceo@xdeals.online", role="owner"))

        # ==========================================
        # 2. FILIAL A: INGRESSOS (Taxa: 3% + 0.50 R$)
        # ==========================================
        fee_ingressos = {
            "pix_in": {"percent": 0.03, "fixed": 0.50},
            "internal_transfer": {"percent": 0.0, "fixed": 0.0} # Movimentos internos a 0%
        }
        filial_ingressos = Account(name="XDeals Ingressos", parent_id=holding_xdeals.id, account_type="SUBSIDIARY", tier="DIAMOND", fee_config=fee_ingressos)
        db.add(filial_ingressos)
        await db.flush()

        db.add(App(account_id=filial_ingressos.id, name="Checkout Ingressos", api_key="dk_test_ingressos_001"))
        db.add(Balance(account_id=filial_ingressos.id, currency="BRL"))
        db.add(ProviderAccount(provider_id=elitepay.id, account_id=filial_ingressos.id, credentials_encrypted={"client_id": "elite", "client_secret": "elite"}))

        # ==========================================
        # 3. FILIAL B: SORTE AGORA (Taxa com Condicional!)
        # Se for > R$ 50: 8% + 1.00 R$. Se for < R$ 50: 10% + 2.00 R$
        # ==========================================
        fee_sorte = {
            "pix_in": {
                "percent": 0.08, "fixed": 1.00,
                "threshold_amount": 50.00,
                "threshold_percent": 0.10, "threshold_fixed": 2.00
            }
        }
        filial_sorte = Account(name="Sorte Agora", parent_id=holding_xdeals.id, account_type="SUBSIDIARY", tier="PLATINUM", fee_config=fee_sorte)
        db.add(filial_sorte)
        await db.flush()

        db.add(App(account_id=filial_sorte.id, name="Bot SorteAgora", api_key="dk_test_sorte_001"))
        db.add(Balance(account_id=filial_sorte.id, currency="BRL"))
        db.add(ProviderAccount(provider_id=elitepay.id, account_id=filial_sorte.id, credentials_encrypted={"client_id": "elite", "client_secret": "elite"}))

        await db.commit()
        print("✅ Ecossistema Corporativo Criado!")
        print("- Chave API Ingressos: dk_test_ingressos_001")
        print("- Chave API SorteAgora: dk_test_sorte_001")

if __name__ == "__main__":
    asyncio.run(seed())
