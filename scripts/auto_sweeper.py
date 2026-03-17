import asyncio
import httpx
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models import ProviderAccount, Provider, NocTicket, TicketType, TicketStatus

# ==========================================
# CONFIGURAÇÃO DINÂMICA DO VARREDOR
# ==========================================
SWEEPER_CONFIG = {
    "mistic_1": {
        "is_active": True,
        "mode": "ALERT_ONLY",             # Mantemos em ALERT_ONLY para gerar o ticket de teste
        "threshold_brl": 1000.00,         
        "target_wallet_bep20": "0x1234567890abcdef1234567890abcdef12345678", 
        "api_url": "https://api.mistic.com/v1/withdraw/crypto" 
    }
}

async def trigger_noc_alert(db, provider_name, amount):
    """Cria um alerta vermelho no Painel de Administração"""
    ticket = NocTicket(
        ticket_type=TicketType.MANUAL_CASHOUT,
        status=TicketStatus.PENDING,
        amount=amount,
        description=f"[SWEEPER] O gateway {provider_name} atingiu R$ {amount}. O Varredor está em modo ALERT_ONLY. Requer cash-out manual BEP20."
    )
    db.add(ticket)
    await db.commit()
    print(f"🚨 Alerta NOC gerado no banco de dados para o gateway: {provider_name.upper()}.")

async def execute_bep20_cashout(provider_name, config, amount, credentials):
    """Chama a API do Gateway para enviar USDT BEP20 para a tua Wallet"""
    print(f"💸 Iniciando Cash-out Automático BEP20 de {provider_name} para a Wallet {config['target_wallet_bep20']}...")
    await asyncio.sleep(1)
    print(f"✅ [SIMULAÇÃO] R$ {amount} convertidos e enviados em BEP20 com sucesso!")

async def run_sweeper():
    print("🧹 Iniciando Varredura de Liquidez (Sweeper)...")
    async with AsyncSessionLocal() as db:
        # CORREÇÃO: Usar selectinload para carregar a relação 'provider' de forma assíncrona logo de início
        query = select(ProviderAccount).options(selectinload(ProviderAccount.provider)).where(ProviderAccount.is_active == True)
        result = await db.execute(query)
        accounts = result.scalars().all()

        for account in accounts:
            provider_name = account.provider.name
            config = SWEEPER_CONFIG.get(provider_name)
            
            if not config or not config["is_active"]:
                continue

            # Simulação de saldo retido no Gateway
            current_balance = 1500.00 
            
            if current_balance >= config["threshold_brl"]:
                print(f"⚠️ Gatilho ativado para {provider_name.upper()}: Saldo (R$ {current_balance}) >= Limite (R$ {config['threshold_brl']})")
                
                if config["mode"] == "ALERT_ONLY":
                    await trigger_noc_alert(db, provider_name, current_balance)
                elif config["mode"] == "AUTO_CASHOUT":
                    await execute_bep20_cashout(provider_name, config, current_balance, account.credentials_encrypted)

if __name__ == "__main__":
    asyncio.run(run_sweeper())
