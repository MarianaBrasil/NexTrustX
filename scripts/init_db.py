import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from database.models import Base
from database.session import DATABASE_URL

async def init_models():
    print(f"🔄 Conectando a: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("🏗️  Derrubando tabelas antigas (Modo Staging/Dev)...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("🚀 Construindo nova arquitetura DarkPay Nexus V2...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("✅ Banco de dados inicializado com sucesso!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_models())
