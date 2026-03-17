import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def notify_critical(message: str):
    """Dispara os alertas para o Telegram e Discord em simultâneo"""
    tg_token = os.getenv("NOC_CRITICAL_TG_TOKEN")
    tg_chat = os.getenv("NOC_CRITICAL_TG_CHAT")
    discord_webhook = os.getenv("NOC_CRITICAL_DISCORD")

    async with httpx.AsyncClient() as client:
        tasks = []
        
        # Preparar o tiro para o Telegram
        if tg_token and tg_chat:
            tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload_tg = {"chat_id": tg_chat, "text": message}
            tasks.append(client.post(tg_url, json=payload_tg))
        
        # Preparar o tiro para o Discord
        if discord_webhook:
            payload_discord = {"content": f"**🚨 ALERTA NOC:**\n{message}"}
            tasks.append(client.post(discord_webhook, json=payload_discord))
            
        # Disparar todas as sirenes ao mesmo tempo
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
