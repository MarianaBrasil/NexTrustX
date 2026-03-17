import httpx
from typing import Dict, Any, Optional

class NowPaymentsDriver:
    """
    Driver DarkPay Nexus para NowPayments (Crypto Gateway).
    Ferramenta completa: Pagamentos, Faturas, Câmbio e Taxas da Rede.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.nowpayments.io/v1"
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Motor de requisições base para a NowPayments"""
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
    # 📡 ESTADO DA API E MOEDAS SUPORTADAS
    # ==========================================
    async def get_api_status(self) -> Dict[str, Any]:
        """Verifica se a API da NowPayments está operacional"""
        return await self._request("GET", "/status")

    async def get_currencies(self) -> Dict[str, Any]:
        """Lista todas as moedas e redes suportadas (ex: btc, usdttrc20)"""
        return await self._request("GET", "/currencies")

    # ==========================================
    # 💱 CÁMBIO E LIMITES (ESTIMATIVAS)
    # ==========================================
    async def get_estimate_price(self, amount: float, currency_from: str, currency_to: str) -> Dict[str, Any]:
        """
        Calcula a conversão exata. 
        Ex: Quantos 'usdttrc20' preciso para pagar 50 'usd'.
        """
        params = {"amount": amount, "currency_from": currency_from, "currency_to": currency_to}
        return await self._request("GET", "/estimate", params=params)

    async def get_minimum_payment_amount(self, currency_from: str, currency_to: str) -> Dict[str, Any]:
        """Retorna o valor mínimo exigido para criar um pagamento devido às taxas da rede"""
        params = {"currency_from": currency_from, "currency_to": currency_to}
        return await self._request("GET", "/min-amount", params=params)

    # ==========================================
    # 💳 PAGAMENTO DIRETO (API PAYMENT)
    # ==========================================
    async def create_payment(
        self, 
        price_amount: float, 
        price_currency: str, 
        pay_currency: str, 
        order_id: str, 
        ipn_callback_url: str,
        order_description: Optional[str] = "DarkPay Nexus Payment"
    ) -> Dict[str, Any]:
        """
        Cria um endereço de pagamento crypto específico para esta transação.
        Devolve o endereço da wallet e o valor exato a depositar.
        """
        payload = {
            "price_amount": price_amount,
            "price_currency": price_currency, # Moeda base (ex: usd, brl)
            "pay_currency": pay_currency,     # Criptomoeda a pagar (ex: usdttrc20)
            "ipn_callback_url": ipn_callback_url,
            "order_id": order_id,
            "order_description": order_description
        }
        res = await self._request("POST", "/payment", json=payload)
        
        # Tradução para o dialeto Nexus
        if res["success"]:
            data = res["data"]
            return {
                "success": True,
                "transaction_id": data.get("payment_id"),
                "pay_address": data.get("pay_address"),
                "pay_amount": data.get("pay_amount"),
                "pay_currency": data.get("pay_currency"),
                "status": data.get("payment_status")
            }
        return res

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Consulta o status de um pagamento (waiting, confirming, confirmed, failed)"""
        return await self._request("GET", f"/payment/{payment_id}")

    # ==========================================
    # 🧾 FATURAS (INVOICE API - URL AMIGÁVEL)
    # ==========================================
    async def create_invoice(
        self, 
        price_amount: float, 
        price_currency: str, 
        order_id: str,
        ipn_callback_url: str
    ) -> Dict[str, Any]:
        """
        Cria uma Fatura com link de pagamento amigável hospedado pela NowPayments.
        O cliente pode escolher a moeda na hora de pagar.
        """
        payload = {
            "price_amount": price_amount,
            "price_currency": price_currency,
            "ipn_callback_url": ipn_callback_url,
            "order_id": order_id
        }
        return await self._request("POST", "/invoice", json=payload)
