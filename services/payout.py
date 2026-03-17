import logging
from sqlalchemy.future import select
from database.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ProviderAccount, Transaction, NocTicket, TicketStatus
from services.noc import notify_critical

# Importação dos drivers
from drivers.elitepay_driver import ElitePayDriver
from drivers.mistic_driver import MisticDriver

async def process_auto_payout(tx_id: str):
    """Tarefa de Background: Autodetecção de Driver e Liquidação"""
    from sqlalchemy.orm import sessionmaker
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 1. Localizar a Transação
        res = await db.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = res.scalars().first()
        if not tx or tx.status != "processing":
            return

        # 2. Buscar Contas Ativas
        query = await db.execute(select(ProviderAccount).where(ProviderAccount.is_active == True))
        provider_accounts = query.scalars().all()

        payout_executed = False
        
        for p_acc in provider_accounts:
            creds = p_acc.credentials_encrypted
            if not isinstance(creds, dict):
                continue

            try:
                # 3. IDENTIFICAÇÃO DINÂMICA DO DRIVER
                driver = None
                
                # Se tem chaves da ElitePay
                if 'client_id' in creds and 'client_secret' in creds:
                    driver = ElitePayDriver(creds['client_id'], creds['client_secret'])
                    provider_name = "ElitePay"
                
                # Se tem chaves da MisticPay
                elif 'ci' in creds and 'cs' in creds:
                    driver = MisticDriver(creds['ci'], creds['cs'])
                    provider_name = "MisticPay"

                if not driver:
                    continue

                # 4. CONSULTA SALDO REAL
                balance_res = await driver.get_balance()
                if not balance_res.get("success"):
                    continue
                
                data = balance_res.get("data", {})
                real_balance = float(data.get("balance", data.get("availableBalance", 0)))

                # 5. EXECUÇÃO SE HOUVER LIQUIDEZ (Margem de R$ 2.00 para taxas)
                if real_balance >= (tx.amount + 2.0):
                    # Extraímos a chave PIX do campo description ou payload
                    # (Ajuste conforme onde guardas a chave final no momento do request)
                    pix_key = tx.description.split(":")[-1].strip() if ":" in tx.description else ""
                    
                    if not pix_key:
                        continue

                    pay_res = await driver.create_pix_withdraw(
                        amount=tx.amount,
                        pix_key=pix_key,
                        pix_key_type="EVP" # Fallback para chave aleatória/EVP
                    )

                    if pay_res.get("success"):
                        payout_executed = True
                        break

            except Exception as e:
                logging.error(f"Erro no processamento automático ({p_acc.id}): {e}")
                continue

        # 6. FINALIZAÇÃO E NOTIFICAÇÃO
        if payout_executed:
            tx.status = "paid"
            # Tenta encontrar e fechar o ticket do NOC
            ticket_res = await db.execute(select(NocTicket).where(NocTicket.amount == tx.amount, NocTicket.status == TicketStatus.PENDING))
            ticket = ticket_res.scalars().first()
            if ticket:
                ticket.status = TicketStatus.RESOLVED
            
            await db.commit()
            await notify_critical(f"✅ [AUTO-PAYOUT] R$ {tx.amount} liquidado via {provider_name}.")
        else:
            await notify_critical(f"🚨 [LIQUIDEZ ZERO] Saque de R$ {tx.amount} falhou. Verifique os provedores!")

