import asyncio
import sys
import os
from decimal import Decimal
sys.path.append(os.getcwd())

from database.session import AsyncSessionLocal
from database.models import Account, App, Transaction, Balance
from core.ledger import LedgerEngine
from services.payout import process_payout

async def run_test():
    async with AsyncSessionLocal() as db:
        print("🧪 Iniciando Teste de Ciclo Completo (Segmento RED)...")
        
        # 1. Criar Cliente Teste
        acc = Account(name="CLIENTE_URGENTE_TEST", segment="RED")
        db.add(acc)
        await db.flush()
        
        app = App(account_id=acc.id, name="TestApp")
        db.add(app)
        await db.flush()
        
        # 2. Simular Entrada de R$ 1000,00
        tx_in = Transaction(
            app_id=app.id, 
            amount=Decimal('1000.00'), 
            currency="BRL", 
            method="PIX", 
            type="IN", 
            status="pending"
        )
        db.add(tx_in)
        await db.commit()
        print(f"✅ Entrada criada: R$ {tx_in.amount}")

        # 3. Liquidar (Deve cobrar 25% = R$ 250,00. Saldo deve ser R$ 750,00)
        ledger = LedgerEngine(db)
        await ledger.settle_transaction(tx_in.id)
        print("✅ Liquidação RED concluída (Taxa 25% aplicada).")

        # 4. Verificar Saldo
        res_bal = await db.execute(select(Balance).where(Balance.account_id == acc.id))
        bal = res_bal.scalars().first()
        print(f"💰 Saldo disponível para o cliente: R$ {bal.available_balance}")
        
        if bal.available_balance != Decimal('750.00'):
            print("❌ ERRO NO SALDO!")
            return

        # 5. Tentar Saque de R$ 500,00 (RED paga 0% no saque conforme fee_engine)
        tx_out = Transaction(
            app_id=app.id, 
            amount=Decimal('500.00'), 
            currency="BRL", 
            method="PIX", 
            type="OUT", 
            status="pending"
        )
        db.add(tx_out)
        await db.commit()
        
        print(f"🚀 Processando Saída de R$ 500,00...")
        payout_res = await process_payout(tx_out.id)
        
        if "error" in payout_res:
            print(f"❌ Erro no Payout: {payout_res['error']}")
        else:
            # Re-checar saldo final (750 - 500 = 250)
            await db.refresh(bal)
            print(f"✨ Ciclo Finalizado. Saldo Restante: R$ {bal.available_balance}")
            if bal.available_balance == Decimal('250.00'):
                print("🏆 TESTE GLOBAL APROVADO. SISTEMA ESTÁ SEGURO.")

if __name__ == "__main__":
    asyncio.run(run_test())
