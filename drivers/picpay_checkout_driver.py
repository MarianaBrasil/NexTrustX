import httpx
from typing import Dict, Any

class PicPayCheckoutDriver:
    """Driver DarkPay Nexus para PicPay Link de Pagamento (v1/paymentlink/create)"""
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = "https://api.picpay.com/oauth2/token"
        self.base_url = "https://api.picpay.com/v1/paymentlink/create"

    async def _get_access_token(self) -> str:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(self.auth_url, json=payload, headers={"Content-Type": "application/json"})
            res.raise_for_status()
            return res.json().get("access_token")

    async def create_payment(self, amount: float, reference: str, webhook_url: str) -> Dict[str, Any]:
        try: 
            token = await self._get_access_token()
        except Exception as e: 
            return {"success": False, "error": "Autenticação OAuth2 PicPay falhou", "details": str(e)}
        
        amount_cents = int(amount * 100)
        
        # 1. Limitar o order_number a 15 caracteres (Regra PicPay)
        safe_reference = str(reference)[:15]

        payload = {
            "charge": {
                "name": f"Pedido {safe_reference}",
                "description": "Pagamento Processado por Nexus",
                "order_number": safe_reference,
                "redirect_url": webhook_url,
                "payment": {
                    "methods": ["BRCODE", "CREDIT_CARD"],
                    "brcode_arrangements": ["PICPAY", "PIX"]
                },
                "amounts": {
                    "product": amount_cents,
                    "delivery": 0
                }
            },
            "options": {
                "allow_create_pix_key": True,
                "card_max_installment_number": 1 # 2. Campo obrigatório adicionado
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    self.base_url, 
                    json=payload, 
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                )
                res.raise_for_status()
                data = res.json()
                
                return {
                    "success": True,
                    "transaction_id": data.get("txid"),
                    "pix_code": data.get("brcode"), 
                    "payment_url": data.get("link"), 
                    "qr_code_url": None, 
                    "status": "PENDING"
                }
            except httpx.HTTPStatusError as e: 
                return {"success": False, "error": f"HTTP {e.response.status_code}", "details": e.response.text}
            except Exception as e: 
                return {"success": False, "error": str(e)}
