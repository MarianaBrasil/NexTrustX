import asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from database.session import AsyncSessionLocal
from database.models import Account, ProviderAccount

# Importando os nossos Drivers
from drivers.mistic_driver import MisticDriver
from drivers.elitepay_driver import ElitePayDriver
from drivers.picpay_checkout_driver import PicPayCheckoutDriver

async def run_diagnostics():
    async with AsyncSessionLocal() as db:
        print("🔍 Iniciando Diagnóstico de Gateways (NOC DarkPay)...\n")

        # Puxa o projeto XDeals Ingressos e as suas rotas
        account = (await db.execute(select(Account).where(Account.name == "XDeals Ingressos"))).scalars().first()
        if not account:
            print("❌ Conta não encontrada.")
            return

        query = select(ProviderAccount).options(joinedload(ProviderAccount.provider)).where(ProviderAccount.account_id == account.id)
        routes = (await db.execute(query)).scalars().all()

        for route in routes:
            prov_name = route.provider.name
            creds = route.credentials_encrypted
            print(f"📡 Testando Rota: [{prov_name.upper()}]...")

            try:
                # -----------------------------------------
                # TESTE MISTIC (Pede o Saldo da Conta)
                # -----------------------------------------
                if "mistic" in prov_name:
                    driver = MisticDriver(creds["client_id"], creds["client_secret"])
                    res = await driver.get_balance()
                    if res.get("success"):
                        print(f"   ✅ SUCESSO! Conexão estabelecida. (Dados: {res.get('data')})\n")
                    else:
                        print(f"   ❌ FALHA: {res.get('error')} - {res.get('details')}\n")

                # -----------------------------------------
                # TESTE PICPAY (Tenta gerar o Token OAuth2)
                # -----------------------------------------
                elif "picpay" in prov_name:
                    driver = PicPayCheckoutDriver(creds["client_id"], creds["client_secret"])
                    try:
                        token = await driver._get_access_token()
                        print(f"   ✅ SUCESSO! Token PicPay gerado (Autenticação Perfeita).\n")
                    except Exception as e:
                        print(f"   ❌ FALHA na Autenticação PicPay: {e}\n")

                # -----------------------------------------
                # TESTE ELITEPAY (Gera um PIX de R$ 1,00 Falso)
                # -----------------------------------------
                elif "elitepay" in prov_name:
                    driver = ElitePayDriver(creds["client_id"], creds["client_secret"])
                    res = await driver.create_pix_deposit(1.00, f"TESTE-NOC-{prov_name}", "NOC DarkPay", "00000000000")
                    if res.get("success"):
                        print(f"   ✅ SUCESSO! Conexão ElitePay OK. PIX Gerado.\n")
                    else:
                        print(f"   ❌ FALHA: {res.get('error')} - {res.get('details')}\n")

            except Exception as e:
                print(f"   ⚠️ ERRO INTERNO AO TESTAR {prov_name}: {e}\n")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
