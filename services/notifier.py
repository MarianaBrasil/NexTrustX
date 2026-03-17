import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv() # Carrega o .env

class NOC:
    """Sistema Central de Notificações DarkPay Nexus"""
    
    @staticmethod
    async def _send_discord(webhook_url: str, title: str, message: str, color: int):
        if not webhook_url: return
        payload = {"username": "DarkPay Oracle", "embeds": [{"title": title, "description": message, "color": color}]}
        async with httpx.AsyncClient() as client:
            try: await client.post(webhook_url, json=payload)
            except: pass

    @staticmethod
    async def _send_telegram(token: str, chat_id: str, message: str):
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        async with httpx.AsyncClient() as client:
            try: await client.post(url, json=payload)
            except: pass

    @classmethod
    async def internal_alert(cls, level: str, message: str):
        """Notifica a equipa da DarkPay (NOC)"""
        colors = {"INFO": 3447003, "SUCCESS": 65280, "WARNING": 16776960, "CRITICAL": 16711680}
        color = colors.get(level, 3447003)
        title = f"[{level}] Alerta NOC"
        text = f"🏦 *DARKPAY NOC [{level}]*\n\n{message}"

        if level in ["WARNING", "CRITICAL"]:
            # Rota para o NOC de Intervenção
            discord_url = os.getenv("NOC_CRITICAL_DISCORD")
            tg_token = os.getenv("NOC_CRITICAL_TG_TOKEN")
            tg_chat = os.getenv("NOC_CRITICAL_TG_CHAT")
        else:
            # Rota para o NOC de Reporting Diário
            discord_url = os.getenv("NOC_REPORTING_DISCORD")
            tg_token = os.getenv("NOC_REPORTING_TG_TOKEN")
            tg_chat = os.getenv("NOC_REPORTING_TG_CHAT")

        await asyncio.gather(
            cls._send_discord(discord_url, title, message, color),
            cls._send_telegram(tg_token, tg_chat, text)
        )

    @classmethod
    async def client_alert(cls, app: any, message: str):
        """Notifica o Cliente (ex: XDeals) nos seus próprios canais"""
        title = "💰 Notificação de Recebimento"
        text = f"✨ *NexTrustX / {app.name}*\n\n{message}"
        
        # Puxa os dados da tabela Apps do banco de dados
        await asyncio.gather(
            cls._send_discord(app.discord_webhook, title, message, 65280),
            cls._send_telegram(os.getenv("NOC_REPORTING_TG_TOKEN"), app.telegram_chat_id, text) # Assumindo o Bot da empresa
        )
