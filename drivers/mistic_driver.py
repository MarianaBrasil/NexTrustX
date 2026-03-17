import httpx
from typing import Dict, Any

class MisticDriver:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.misticpay.com/api"
        self.headers = {
            "ci": self.client_id,
            "cs": self.client_secret,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.request(method, f"{self.base_url}{endpoint}", headers=self.headers, **kwargs)
                data = res.json() if res.text else {}
                return {"success": res.status_code < 400, "data": data, "status": res.status_code}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_balance(self) -> Dict[str, Any]:
        res = await self._request("GET", "/users/balance")
        if res["success"] and "data" in res["data"]:
            return {"success": True, "data": res["data"]["data"]}
        return res
