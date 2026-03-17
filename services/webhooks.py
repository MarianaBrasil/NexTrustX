import httpx
import hmac
import hashlib
import json
import asyncio
from datetime import datetime

async def send_webhook(url: str, event_type: str, data: dict, secret_key: str = None):
    """Dispara um Webhook para o cliente com assinatura HMAC-SHA256 para segurança."""
    if not url:
        return False

    payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    headers = {"Content-Type": "application/json"}

    # Se a App tiver uma api_key (que atua como secret), assinamos o payload para evitar fraudes
    if secret_key:
        signature = hmac.new(
            secret_key.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        headers["x-darkpay-signature"] = signature

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Tenta disparar o Webhook
            response = await client.post(url, content=payload_str, headers=headers)
            print(f"📡 Webhook disparado para {url} | Status: {response.status_code}")
            return response.status_code in (200, 201, 202)
        except Exception as e:
            print(f"⚠️ Falha ao disparar Webhook para {url}: {e}")
            # Em produção, aqui colocarias lógica de "Retry" (tentar novamente 3 vezes)
            return False
