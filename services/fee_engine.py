from decimal import Decimal, ROUND_HALF_UP

def calculate_transaction_fee(account, amount, method: str, is_bep20: bool = False) -> tuple[Decimal, Decimal]:
    """
    Calcula o Markup da organização e o Saldo Líquido do cliente com precisão matemática (Decimal).
    """
    segment = getattr(account, 'segment', 'BLACK').upper() if getattr(account, 'segment', None) else "BLACK"
    
    # Converter valor de entrada para Decimal blindado
    amount_dec = Decimal(str(amount))
    fee_percent = Decimal('0.0')
    fee_fixed = Decimal('0.0')

    if segment == "WHITE":
        if method == "IN":
            fee_percent, fee_fixed = Decimal('0.06'), Decimal('1.00')
        else: # OUT
            fee_percent, fee_fixed = Decimal('0.03'), Decimal('1.00')
            if is_bep20:
                fee_percent += Decimal('0.04')

    elif segment == "BLACK":
        if method == "IN":
            fee_percent = Decimal('0.10')
            if amount_dec < Decimal('100.00'):
                fee_fixed = Decimal('1.00')
        else: # OUT
            fee_percent, fee_fixed = Decimal('0.00'), Decimal('0.00')
            if is_bep20:
                fee_percent = Decimal('0.04')

    elif segment == "RED":
        # RED paga 25% na entrada e nada na saída
        if method == "IN":
            fee_percent = Decimal('0.25')
        else:
            fee_percent, fee_fixed = Decimal('0.00'), Decimal('0.00')

    # Cálculo exato com arredondamento financeiro padrão (ROUND_HALF_UP)
    total_fee = (amount_dec * fee_percent) + fee_fixed
    total_fee = total_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    net_amount = amount_dec - total_fee
    
    return total_fee, net_amount
