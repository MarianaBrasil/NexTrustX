import httpx
from typing import Dict, Any

class ElitePayDriver:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.elitepaybr.com/api"
        # Conforme a documentação: ci e cs
        self.headers = {
            "ci": self.client_id,
            "cs": self.client_secret,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}{endpoint}"
                res = await client.request(method, url, headers=self.headers, **kwargs)
                
                # Se não for 200, retornamos o erro para debug
                if res.status_code != 200:
                    return {"success": False, "error": f"HTTP {res.status_code}", "details": res.text}
                
                return {"success": True, "data": res.json()}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_balance(self) -> Dict[str, Any]:
        # Endpoint exato da doc: /users/balance
        return await self._request("GET", "/users/balance")

    async def create_pix_withdraw(self, amount: float, pix_key: str, pix_key_type: str, description: str = "Saque Nexus") -> Dict[str, Any]:
        # Endpoint de cashout (v1/withdraw geralmente, ajuste se necessário)
        payload = {
            "amount": amount,
            "pixKey": pix_key,
            "pixKeyType": pix_key_type,
            "description": description
        }
        return await self._request("POST", "/v1/withdraw", json=payload)
