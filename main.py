from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.payments import router as payments_router
from api.webhooks import router as webhooks_router
from api.admin import admin_router
from api.client import client_router
from api.noc import noc_router  # <-- Importando o NOC

app = FastAPI(title="DarkPay Nexus V2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)
app.include_router(webhooks_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(noc_router) # <-- Comando de Missão Ativo!

@app.get("/health")
async def health_check():
    return {"status": "online", "system": "Nexus Smart Routing Engine"}
