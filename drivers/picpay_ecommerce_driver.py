import httpx
from typing import Dict, Any

class PicPayEcommerceDriver:
    """
    Driver DarkPay Nexus para PicPay E-commerce (Cash-In Avulso).
    Foco: Geração de QR Code e Deep Links para pagamento via app PicPay.
    """
    def __init__(self, picpay_token: str):
        self.picpay_token = picpay_token
        # URL oficial de produção para E-commerce
        self.base_url = "https://appws.picpay.com/ecommerce/public"
        
        self.headers = {
            "x-picpay-token": self.picpay_token,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Motor interno de requisições padronizado do Nexus"""
        async with httpx.AsyncClient() as client:
            try:
                res = await client.request(method, f"{self.base_url}{endpoint}", headers=self.headers, **kwargs)
                res.raise_for_status()
                
                # O PicPay pode devolver 204 No Content (ex: em cancelamentos)
                data = res.json() if res.content else {}
                return {"success": True, "data": data}
                
            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                return {
                    "success": False, 
                    "error": f"HTTP {e.response.status_code}", 
                    "details": error_data
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    # ==========================================
    # 📥 CASH-IN (GERAR COBRANÇA PICPAY)
    # ==========================================
    async def create_payment(
        self, 
        reference_id: str, 
        amount: float, 
        buyer_first_name: str, 
        buyer_document: str, 
        buyer_email: str, 
        return_url: str, 
        callback_url: str
    ) -> Dict[str, Any]:
        """
        Gera um pagamento. Devolve o link de pagamento e o QR Code.
        """
        payload = {
            "referenceId": reference_id,
            "callbackUrl": callback_url,
            "returnUrl": return_url, # Para onde o PicPay redireciona o cliente após pagar
            "value": amount,
            "buyer": {
                "firstName": buyer_first_name,
                "lastName": "Cliente",
                "document": buyer_document,
                "email": buyer_email
            }
        }
        
        res = await self._request("POST", "/payments", json=payload)
        
        # Padronização Nexus: Traduzimos a resposta do PicPay para a "língua" da DarkPay
        if res["success"]:
            data = res["data"]
            return {
                "success": True,
                "transaction_id": data.get("referenceId"),
                "payment_url": data.get("paymentUrl"),
                "qr_code": data.get("qrcode", {}).get("base64"),
                "expires_at": data.get("expiresAt")
            }
        return res

    # ==========================================
    # 🔍 CONSULTA DE STATUS
    # ==========================================
    async def get_status(self, reference_id: str) -> Dict[str, Any]:
        """Consulta o status de um pagamento pendente no PicPay"""
        return await self._request("GET", f"/payments/{reference_id}/status")

    # ==========================================
    # 🛑 CANCELAMENTO / ESTORNO
    # ==========================================
    async def cancel_payment(self, reference_id: str, authorization_id: str = None) -> Dict[str, Any]:
        """
        Cancela uma transação pendente ou solicita estorno de uma transação paga.
        """
        payload = {"authorizationId": authorization_id} if authorization_id else {}
        return await self._request("POST", f"/payments/{reference_id}/cancellations", json=payload)
