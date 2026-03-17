import asyncio
import secrets
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models import Account, App

async def generate_api_key(prefix: str) -> str:
    return f"dk_live_{prefix}_{secrets.token_hex(16)}"

async def seed_clients():
    async with AsyncSessionLocal() as db:
        print("🌱 Iniciando criação de Clientes Oficiais (Fase Beta)...")

        # ==========================================
        # 1. CLIENTE: XDEALS (Corporate)
        # ==========================================
        query = await db.execute(select(Account).where(Account.name == "XDeals Matriz"))
        xdeals = query.scalars().first()
        if not xdeals:
            xdeals = Account(name="XDeals Matriz", fee_config={"pix_in": 0.05}) # Exemplo: 5% fee normal
            db.add(xdeals)
            await db.flush()

        # Apps da XDeals
        apps_xdeals = ["Ingressos", "Serasa", "SorteAgora"]
        for app_name in apps_xdeals:
            query = await db.execute(select(App).where(App.name == f"XDeals {app_name}"))
            if not query.scalars().first():
                api_key = await generate_api_key(app_name.lower())
                app = App(account_id=xdeals.id, name=f"XDeals {app_name}", api_key=api_key)
                db.add(app)
                print(f"✅ Criado: XDeals {app_name} | API KEY: {api_key}")

        # ==========================================
        # 2. CLIENTE: DARKMARKET (Ecossistema Interno)
        # ==========================================
        query = await db.execute(select(Account).where(Account.name == "DarkMarket Matriz"))
        darkmarket = query.scalars().first()
        if not darkmarket:
            darkmarket = Account(name="DarkMarket Matriz", fee_config={"pix_in": 0.05})
            db.add(darkmarket)
            await db.flush()

        # Apps do DarkMarket
        dark_apps = [
            {"name": "DarkPix", "prefix": "darkpix", "fee": 0.05},
            {"name": "DarkBankRED", "prefix": "red", "fee": 0.25} # 🚨 Taxa RED de 25% configurada
        ]
        
        for app_data in dark_apps:
            query = await db.execute(select(App).where(App.name == app_data["name"]))
            if not query.scalars().first():
                api_key = await generate_api_key(app_data["prefix"])
                app = App(account_id=darkmarket.id, name=app_data["name"], api_key=api_key)
                db.add(app)
                print(f"✅ Criado: {app_data['name']} | API KEY: {api_key} | FEE: {app_data['fee']*100}%")

        await db.commit()
        print("🚀 BASE DE CLIENTES PRONTA PARA PRODUÇÃO!")

if __name__ == "__main__":
    asyncio.run(seed_clients())
