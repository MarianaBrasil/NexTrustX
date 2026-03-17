# 📚 DARKPAY NEXUS - MANUAL DE DRIVERS DE API

Este documento detalha as capacidades reais e os métodos disponíveis em cada Driver isolado dentro da pasta `drivers/` da arquitetura DarkPay Nexus V2. Cada driver padroniza a comunicação externa, traduzindo respostas de terceiros para o formato interno do nosso Orquestrador (Switcher).

---

## 1. 🟢 ElitePayBr (`elitepay_driver.py`)
**Tipo:** PIX Nativo & Liquidação Crypto Exclusiva.
**Autenticação:** `x-client-id` e `x-client-secret`.

| Método | Endpoint Alvo | Funcionalidade |
|--------|--------------|----------------|
| `get_balance()` | `GET /users/balance` | Consulta saldo atual do cliente na plataforma. |
| `create_pix_deposit()` | `POST /v1/deposit` | **Cash-in.** Gera QR Code e Copia-e-Cola (PIX dinâmico). |
| `create_pix_withdraw()` | `POST /v1/withdraw` | **Cash-out.** Envia PIX (Saque/Payout) para chaves CPF, CNPJ, Email, etc. |
| `check_transaction_status()` | `GET /transactions/check` | Consulta se uma transação (id) foi paga, pendente ou falhou. |
| `get_crypto_quote()` | `GET /v1/crypto/quote` | Rota pública. Retorna a cotação BRL/USDT atual e as taxas da rede. |
| `create_crypto_withdraw()` | `POST /v1/crypto/withdraw` | Converte Saldo BRL para USDT (BEP20) e liquida numa wallet externa. |

---

## 2. 🟢 PicPay E-commerce (`picpay_ecommerce_driver.py`)
**Tipo:** Checkout Transparente (Cartões e Saldo App).
**Autenticação:** `x-picpay-token`.

| Método | Endpoint Alvo | Funcionalidade |
|--------|--------------|----------------|
| `create_payment()` | `POST /payments` | **Cash-in.** Gera intenção de pagamento com Deep Link e QR Code da app PicPay. |
| `get_status()` | `GET /payments/{id}/status` | Verifica o estado da transação no ecossistema PicPay. |
| `cancel_payment()` | `POST /payments/{id}/cancellations` | Pede o estorno (refund) ou cancela uma transação gerada. |

---

## 3. 🟢 PicPay PIX Nativo (`picpay_pix_driver.py`)
**Tipo:** Geração de PIX Direto e Dinâmico.
**Autenticação:** Bearer Token.

| Método | Endpoint Alvo | Funcionalidade |
|--------|--------------|----------------|
| `create_pix_charge()` | `POST /qrcodes` | **Cash-in.** Gera apenas dados PIX em altíssima velocidade (sem checkout completo). |
| `check_pix_status()` | `GET /qrcodes/{id}/status` | Validação de estado específica para QR Codes nativos do Banco Central. |

---

## 4. 🟢 PicPay Assinaturas (`picpay_subs_driver.py`)
**Tipo:** Pagamentos Recorrentes e Tokenização.
**Autenticação:** `x-picpay-token`.

| Método | Endpoint Alvo | Funcionalidade |
|--------|--------------|----------------|
| `create_plan()` | `POST /plans` | Cria um plano de mensalidade/anuidade na plataforma. |
| `subscribe_customer()`| `POST /subscribers` | Vincula os dados de um cliente a um plano criado (inicia a cobrança). |
| `cancel_subscription()`| `PUT /subscribers/{id}/cancel` | Cancela uma assinatura ativa (churn). |

---

## 5. 🟢 NowPayments (`nowpayments_driver.py`)
**Tipo:** Crypto Gateway Global (Mais de 300 criptomoedas).
**Autenticação:** `x-api-key`.

| Método | Endpoint Alvo | Funcionalidade |
|--------|--------------|----------------|
| `get_api_status()` | `GET /status` | Verifica o uptime da plataforma NowPayments. |
| `get_currencies()` | `GET /currencies` | Lista as moedas ativas e redes operacionais (BTC, ETH, USDTTRC20). |
| `get_estimate_price()` | `GET /estimate` | Retorna a cotação matemática entre Moeda Fiat e Crypto. |
| `get_minimum_payment...`| `GET /min-amount` | Calcula o valor mínimo aceitável devido às taxas de rede (gas fees). |
| `create_payment()` | `POST /payment` | **Cash-in direto.** Gera endereço de wallet único e valor exato a depositar em crypto. |
| `get_payment_status()` | `GET /payment/{id}` | Confirma os blocos na rede e valida se a transação está *Confirmed*. |
| `create_invoice()` | `POST /invoice` | Gera link de pagamento hospedado. O cliente escolhe a moeda que prefere pagar. |

---
**Nota Arquitetónica:**
O Orquestrador do Nexus interage primariamente com os métodos de `create_payment` ou `create_pix_deposit`. O sistema é desenhado de forma isolada (`Separation of Concerns`), garantindo que se uma API externa sofrer alterações, apenas o seu Driver será modificado, sem afetar o Motor Central de roteamento.
