import asyncio
from drivers.elitepay_driver import ElitePayDriver
from drivers.mistic_driver import MisticDriver
from sqlalchemy import text
from database.session import engine

async def test():
    print("\n🚀 DIAGNÓSTICO FINAL DE LIQUIDEZ\n")
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, credentials_encrypted FROM provider_accounts WHERE is_active = True"))
        for row in res:
            db_id, creds = row
            ci = creds.get('ci') or creds.get('client_id')
            cs = creds.get('cs') or creds.get('client_secret')
            
            if not ci or not cs:
                print(f"⚠️ Conta {db_id}: Sem chaves válidas no JSON.")
                continue

            # Tentativa Dupla (Muitas vezes as APIs são intercambiáveis)
            drivers = [
                (ElitePayDriver(ci, cs), "ElitePay"),
                (MisticDriver(ci, cs), "MisticPay")
            ]

            success = False
            for d, name in drivers:
                bal = await d.get_balance()
                if bal.get("success"):
                    print(f"✅ CONTA {db_id} | {name} | SALDO: R$ {bal['data'].get('balance')}")
                    success = True
                    break
            
            if not success:
                print(f"❌ CONTA {db_id} | Falha em ambos os drivers (401/404)")

if __name__ == "__main__":
    asyncio.run(test())
