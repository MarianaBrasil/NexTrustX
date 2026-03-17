import httpx
from typing import Dict, Any

class PicPayPixDriver:
    """
    Driver DarkPay Nexus para PicPay PIX Nativo (Cash-In de Alta Velocidade).
    Foco: Geração exclusiva de PIX sem passar pelo motor de cartões.
    """
    def __init__(self, picpay_token: str):
        self.picpay_token = picpay_token
        # URL oficial da API PIX do PicPay
        self.base_url = "https://api.picpay.com/pix"
        
        self.headers = {
            "Authorization": f"Bearer {self.picpay_token}", # Atenção: A API PIX usa Bearer Token, diferente do E-commerce
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.request(method, f"{self.base_url}{endpoint}", headers=self.headers, **kwargs)
                res.raise_for_status()
                return {"success": True, "data": res.json()}
            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response.text else {}
                return {"success": False, "error": f"HTTP {e.response.status_code}", "details": error_data}
            except Exception as e:
                return {"success": False, "error": str(e)}

    # ==========================================
    # 📥 GERAR QR CODE PIX
    # ==========================================
    async def create_pix_charge(self, reference_id: str, amount: float, expires_in_seconds: int = 600) -> Dict[str, Any]:
        """Gera um PIX com expiração controlada (Padrão: 10 minutos)"""
        payload = {
            "referenceId": reference_id,
            "value": amount,
            "expiresIn": expires_in_seconds
        }
        
        res = await self._request("POST", "/qrcodes", json=payload)
        
        # Tradução para o dialeto DarkPay Nexus
        if res["success"]:
            data = res["data"]
            return {
                "success": True,
                "transaction_id": data.get("referenceId"),
                "pix_code": data.get("qrcode"), # O Payload do Copia e Cola
                "qr_code_url": data.get("qrcodeLink"), # Imagem do QR Code gerada pelo BCB
                "status": "pending"
            }
        return res

    # ==========================================
    # 🔍 CONSULTA DE STATUS PIX
    # ==========================================
    async def check_pix_status(self, reference_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/qrcodes/{reference_id}/status")
