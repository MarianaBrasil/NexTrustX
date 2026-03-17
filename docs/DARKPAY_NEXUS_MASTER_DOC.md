# 🌌 DARKPAY NEXUS V2 - DOCUMENTO MESTRE DE ARQUITETURA
**Tipo:** Payment Orchestration, Digital Banking, Cripto-Liquidação & BaaS (Banking as a Service)
**Fase Atual:** V2.5 (Motor Core Validado, API Live, Frontend NOC em Desenvolvimento)

## 1. VISÃO GLOBAL E TOPOLOGIA
A DarkPay Nexus deixou de ser um simples gateway para se tornar numa Câmara de Compensação (Clearing House) completa. A arquitetura é fisicamente desacoplada para garantir segurança de nível militar (Zero Trust) e escalabilidade global.

* **A Casa das Máquinas (Backend):** VPS Linux isolada. Roda o motor Python (FastAPI), o banco de dados relacional (PostgreSQL) e o sistema de filas (Redis). Nenhuma interface gráfica existe aqui.
* **O Centro de Comandos (NOC Admin):** Frontend em Vercel (Next.js/React). Domínio `admin.dark.lat`. Consome a API da VPS. Exclusivo para operadores do sistema.
* **A Montra do Cliente (Corporate):** Frontend em Vercel (Next.js/React). Domínio `dashboard.nextrustx.com`. Protegido por Cloudflare (WAF/Anti-DDoS). Interface White-label para clientes (ex: XDeals).

## 2. O CICLO DE LIQUIDEZ (OS 3 FLUXOS)

### FASE 1: Pay-in (Entrada de Fluxos / Aquisição)
* **Smart Routing (Orquestrador Dinâmico):** Quando um cliente gera um PIX, o motor avalia milissegundo a milissegundo qual o melhor caminho com base em:
    1.  **Prioridade:** (Ex: Mistic = 10, PicPay = 20, ElitePay = 30).
    2.  **Status (Disjuntor):** O gateway está `is_active = True`?
    3.  **Odómetros (Limites):** O volume diário já estourou?
* **Alta Disponibilidade (Failover Automático):** Se a Mistic falhar (HTTP 401/500), o sistema "salta" invisivelmente para a ElitePay. O cliente final nunca percebe a falha.
* **Gateways Homologados:** MisticPay (Primário), PicPay Checkout (Link de Pagamento), ElitePay (Secundário/Contingência).

### FASE 2: Split Routing & Motor Ledger (O Cofre)
* **Contabilidade Imutável:** Utiliza o modelo de dupla entrada. Valores entram como `pending_balance` e, após o webhook de confirmação, movem-se para `available_balance`.
* **Regras de Split:** A liquidez é matematicamente fatiada no momento da confirmação:
    * % Cliente Final (Ex: XDeals).
    * % DarkPay (Revenue / Fee de Processamento).
    * % Colaboradores / Fornecedores (Distribuição de lucros).

### FASE 3: Settlement & Cash-out (Saídas / Liquidação)
* **Liquidação Fiat (BRL/EUR):** Saídas via PIX ou transferências internacionais (SEPA) diretamente para as contas bancárias dos clientes.
* **Liquidação Crypto (Web3):** Conversão automática de saldo BRL para USDT (BEP20/ERC20) via Gateways ou NowPayments, com envio direto para Cold Wallets (Autocustódia) ou Wallets de Clientes.

## 3. SISTEMA DE NOC E INTERVENÇÃO MANUAL
Nem todos os fluxos podem ser 100% automatizados (ex: restrições de APIs de terceiros como o PicPay).
* **NOC Tickets (`NocTicket`):** Se fundos ficarem retidos num gateway sem API de cash-out, o sistema gera um alerta visual no Dashboard do Administrador.
* **Ação do Operador:** O operador do NOC visualiza o ticket (ex: "Extrair R$ 5.000 do PicPay"), realiza o saque manualmente na app bancária para a conta matriz, e clica em "Liquidado" no painel, sincronizando o Ledger.

## 4. ARQUITETURA MULTI-TENANT (SECURITY BY DESIGN)
**Objetivo:** 1 Driver Python para Infinitas Credenciais.
* O código da DarkPay nunca guarda chaves "hardcoded". O banco de dados (tabela `provider_accounts`) atua como um "Cofre Criptografado". 
* Quando a requisição chega, o sistema injeta as chaves do cliente correto no driver em tempo de execução.

## 5. INFRAESTRUTURA TÉCNICA (PORTAS)
* **API Gateway (FastAPI):** Porta Interna `8081` (CORS configurado para os Frontends Vercel).
* **Database (PostgreSQL):** Porta Interna `5433` (Isolado da V1).
* **Queue/Cache (Redis):** Porta Interna `6380`.
