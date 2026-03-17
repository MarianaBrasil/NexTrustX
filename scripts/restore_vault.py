import asyncio
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Provider, ProviderAccount, Account

async def restore():
    async with AsyncSessionLocal() as db:
        print("🛡️ Restaurando Elites e Mistics sem afetar PicPay/NowPayments...")
        
        acc_query = await db.execute(select(Account).where(Account.name.ilike('%Matriz%')))
        account = acc_query.scalars().first()
        if not account:
            account = (await db.execute(select(Account))).scalars().first()

        # Apenas estas rotas serão alteradas/criadas
        setup_data = [
            {"name": "elitepay_2", "priority": 100, "creds": {"ci": "ep_b58aa8f10b0a09a01cc77317e100ae45", "cs": "eps_c6c4ba1d88a7509767763781eca278254660016522325c3c0bb0892c873f3232"}},
            {"name": "elitepay_3", "priority": 90,  "creds": {"ci": "ep_3bfc6076c54b8ed566fa522099cefb7e", "cs": "eps_e6ba997b0ed13d3160a044056b5cf5c329e79d238dea205aa1d35daca3b1e4bc"}},
            {"name": "mistic_1",   "priority": 80,  "creds": {"ci": "Cci_1qg71qxjwvbhe9f", "cs": "cs_vvkhx2poewxmg2wnd6xbqnxkz"}},
            {"name": "elitepay_1", "priority": 70,  "creds": {"ci": "ep_bd78ca410220cbbaeda9c64123101ba2", "cs": "eps_9476c5ea000637c35f3886fb72291eafd81ead30370135f78770c779cabffef4"}},
            {"name": "mistic_2",   "priority": 60,  "creds": {"ci": "ci_gznu4skfuaomw1m", "cs": "cs_7r0m3m0v61mdbeppzl7a6a6ns"}}
        ]

        for data in setup_data:
            # Busca o provider específico pelo nome
            prov_res = await db.execute(select(Provider).where(Provider.name == data["name"]))
            prov = prov_res.scalars().first()
            if not prov:
                prov = Provider(name=data["name"], type="pix", priority=data["priority"])
                db.add(prov)
                await db.flush()
            else:
                prov.priority = data["priority"]

            # Busca a conta deste provider específico
            pa_res = await db.execute(select(ProviderAccount).where(ProviderAccount.provider_id == prov.id))
            pa = pa_res.scalars().first()
            
            if not pa:
                pa = ProviderAccount(provider_id=prov.id, account_id=account.id, credentials_encrypted=data["creds"], is_active=True)
                db.add(pa)
            else:
                # SÓ atualiza as credenciais desta conta específica
                pa.credentials_encrypted = data["creds"]
                pa.is_active = True

        await db.commit()
        print("\n✅ Sincronização concluída. PicPay e NowPayments permanecem intocados.")

if __name__ == "__main__":
    asyncio.run(restore())
