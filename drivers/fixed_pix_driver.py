class FixedPixDriver:
    """Driver DarkPay para Chaves PIX Fixas (Geração Local EMV)"""
    def __init__(self, pix_key: str, merchant_name: str = "DarkPay Nexus", merchant_city: str = "Sao Paulo"):
        self.pix_key = pix_key
        self.merchant_name = merchant_name[:25]
        self.merchant_city = merchant_city[:15]

    def _crc16(self, data: str) -> str:
        """Calcula o Checksum CRC16-CCITT-FALSE obrigatório do Banco Central"""
        crc = 0xFFFF
        for byte in data.encode('utf-8'):
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        return f"{crc:04X}"

    def _format(self, id_str: str, value: str) -> str:
        return f"{id_str}{len(value):02d}{value}"

    async def create_payment(self, amount: float, reference: str) -> dict:
        """Gera a string PIX Copia e Cola para um valor específico"""
        try:
            # Estrutura padrão EMV do Banco Central do Brasil
            payload = "000201"
            
            # Informação da Conta (Chave PIX)
            gui = self._format("00", "BR.GOV.BCB.PIX")
            key = self._format("01", self.pix_key)
            account_info = self._format("26", gui + key)
            payload += account_info
            
            payload += "52040000" # Categoria (0000 = Não informada)
            payload += "5303986"  # Moeda (986 = BRL)
            
            # Valor
            amount_str = f"{amount:.2f}"
            payload += self._format("54", amount_str)
            
            payload += "5802BR" # País
            payload += self._format("59", self.merchant_name)
            payload += self._format("60", self.merchant_city)
            
            # TxID (Identificador da transação)
            txid = self._format("05", reference[:25])
            payload += self._format("62", txid)
            
            # Adiciona o ID do CRC16 (6304) e calcula o código
            payload += "6304"
            crc = self._crc16(payload)
            pix_copia_e_cola = payload + crc
            
            return {
                "success": True,
                "transaction_id": reference,
                "pix_code": pix_copia_e_cola,
                "qr_code_url": None, # O Frontend (Next.js) gerará a imagem a partir da string
                "status": "PENDING_MANUAL" # Status especial para o NOC
            }
        except Exception as e:
            return {"success": False, "error": f"Erro ao gerar PIX Fixo: {str(e)}"}
