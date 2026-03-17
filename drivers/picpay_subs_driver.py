import httpx
from typing import Dict, Any

class PicPaySubscriptionsDriver:
    """
    Driver DarkPay Nexus para PicPay Assinaturas.
    Foco: Criação de planos recorrentes e gestão de subscritores.
    """
    def __init__(self, picpay_token: str):
        self.picpay_token = picpay_token
        # URL da API de Assinaturas (Recorrência)
        self.base_url = "https://appws.picpay.com/ecommerce/public/subscriptions"
        
        self.headers = {
            "x-picpay-token": self.picpay_token,
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
    # 📋 CRIAR UM NOVO PLANO MENSAL/ANUAL
    # ==========================================
    async def create_plan(self, reference_id: str, name: str, amount: float) -> Dict[str, Any]:
        """Gera um plano de cobrança (ex: Mensalidade VIP)"""
        payload = {
            "referenceId": reference_id,
            "name": name,
            "value": amount,
            "billingCycle": "monthly" # Hardcoded mensal para exemplo
        }
        res = await self._request("POST", "/plans", json=payload)
        
        if res["success"]:
            return {"success": True, "plan_id": res["data"].get("referenceId"), "payment_url": res["data"].get("paymentUrl")}
        return res

    # ==========================================
    # 👤 ASSINAR UM PLANO (SUBSCREVER CLIENTE)
    # ==========================================
    async def subscribe_customer(self, plan_reference: str, subscription_id: str, customer_info: Dict[str, str]) -> Dict[str, Any]:
        """Associa um cliente a um plano existente"""
        payload = {
            "referenceId": subscription_id,
            "planReferenceId": plan_reference,
            "buyer": customer_info # {firstName, lastName, document, email, phone}
        }
        return await self._request("POST", "/subscribers", json=payload)

    # ==========================================
    # 🛑 CANCELAR ASSINATURA
    # ==========================================
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Interrompe as cobranças recorrentes de um subscritor"""
        return await self._request("PUT", f"/subscribers/{subscription_id}/cancel")
