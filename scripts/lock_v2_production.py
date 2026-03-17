import asyncio
import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount, Account

async def lock_production():
    async with AsyncSessionLocal() as db:
        print("🔐 TRANCANDO ARQUITETURA V2 (Credenciais, Limites e Taxas)...")
        
        acc_res = await db.execute(select(Account).where(Account.name.ilike('%Matriz%')))
        account = acc_res.scalars().first()
        if not account:
            account = (await db.execute(select(Account))).scalars().first()

        # O DNA COMPLETO DO TEU PROJETO (Prioridades + Custos + Credenciais)
        # Usamos 'ci' e 'cs' para Elites/Mistics pois os drivers V2 agora exigem isso.
        infrastructure = [
            {
                "name": "elitepay_2", "priority": 100, "limit": 1000.0,
                "creds": {"ci": "ep_b58aa8f10b0a09a01cc77317e100ae45", "cs": "eps_c6c4ba1d88a7509767763781eca278254660016522325c3c0bb0892c873f3232"},
                "costs": {"pix_in": {"percent": 0.04, "fixed": 0.75}, "pix_out": {"percent": 0.00, "fixed": 0.75}, "crypto_out": {"percent": 0.04, "fixed": 0.00}}
            },
            {
                "name": "elitepay_3", "priority": 90, "limit": 1000.0,
                "creds": {"ci": "ep_3bfc6076c54b8ed566fa522099cefb7e", "cs": "eps_e6ba997b0ed13d3160a044056b5cf5c329e79d238dea205aa1d35daca3b1e4bc"},
                "costs": {"pix_in": {"percent": 0.04, "fixed": 0.75}, "pix_out": {"percent": 0.00, "fixed": 0.75}, "crypto_out": {"percent": 0.04, "fixed": 0.00}}
            },
            {
                "name": "mistic_1", "priority": 80, "limit": 1000.0,
                "creds": {"ci": "Cci_1qg71qxjwvbhe9f", "cs": "cs_vvkhx2poewxmg2wnd6xbqnxkz"},
                "costs": {"pix_in": {"percent": 0.00, "fixed": 0.50}, "pix_out": {"percent": 0.00, "fixed": 0.50}, "crypto_out": {"percent": 0.00, "fixed": 0.00, "network_fee": 3.00}}
            },
            {
                "name": "elitepay_1", "priority": 70, "limit": 1000.0,
                "creds": {"ci": "ep_bd78ca410220cbbaeda9c64123101ba2", "cs": "eps_9476c5ea000637c35f3886fb72291eafd81ead30370135f78770c779cabffef4"},
                "costs": {"pix_in": {"percent": 0.08, "fixed": 2.00}, "pix_out": {"percent": 0.00, "fixed": 2.50}, "crypto_out": {"percent": 0.04, "fixed": 0.00}}
            },
            {
                "name": "mistic_2", "priority": 60, "limit": 1000.0,
                "creds": {"ci": "ci_gznu4skfuaomw1m", "cs": "cs_7r0m3m0v61mdbeppzl7a6a6ns"},
                "costs": {"pix_in": {"percent": 0.07, "fixed": 1.00}, "pix_out": {"percent": 0.00, "fixed": 1.00}, "crypto_out": {"percent": 0.00, "fixed": 0.00, "network_fee": 3.00}}
            },
            {
                "name": "picpay_checkout", "priority": 20, "limit": 25000.0,
                "creds": {"client_id": "320185a8-5b1e-4f4c-843c-f71b5a933bae", "client_secret": "xSCu3c5iPTyLC95Ye5zYLHdNeKtmbk6V"},
                "costs": {"pix_in": {"percent": 0.00, "fixed": 0.00}}
            },
            {
                "name": "nowpayments_1", "priority": 40, "limit": 0.0,
                "creds": {"api_key": "VH2H5WJ-JTX47AW-P71B0BD-1EEVWRH"},
                "costs": {"crypto_in": {"percent": 0.01, "fixed": 0.00}}
            }
        ]

        for data in infrastructure:
            prov_res = await db.execute(select(Provider).where(Provider.name == data['name']))
            prov = prov_res.scalars().first()
            if not prov:
                prov = Provider(name=data['name'], type='pix' if 'now' not in data['name'] else 'crypto', priority=data['priority'])
                db.add(prov); await db.flush()
            else:
                prov.priority = data['priority']

            pa_res = await db.execute(select(ProviderAccount).where(ProviderAccount.provider_id == prov.id))
            pa = pa_res.scalars().first()
            
            if pa:
                pa.credentials_encrypted = data['creds']
                pa.daily_limit = data['limit']
                pa.cost_config = data['costs']
                pa.is_active = True
            else:
                db.add(ProviderAccount(
                    provider_id=prov.id, account_id=account.id, 
                    credentials_encrypted=data['creds'], daily_limit=data['limit'], 
                    cost_config=data['costs'], is_active=True
                ))
            print(f"✅ Rota {data['name'].upper()} selada (Taxas e Limites injetados).")

        await db.commit()
        print("\n🚀 INFRAESTRUTURA V2 PRONTA E COERENTE PARA PRODUÇÃO.")

asyncio.run(lock_production())
