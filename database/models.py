from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    segment = Column(String, default="BLACK") # WHITE, BLACK, RED
    tier = Column(String, default="GOLD")    # Legado
    is_active = Column(Boolean, default=True)
    fee_config = Column(JSON, default={})    # Configurações personalizadas
    apps = relationship("App", back_populates="account")

class App(Base):
    __tablename__ = "apps"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    name = Column(String)
    api_key = Column(String, unique=True)
    payout_settings = Column(JSON, default={})
    account = relationship("Account", back_populates="apps")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    app_id = Column(Integer, ForeignKey("apps.id"))
    amount = Column(Numeric(20, 4))
    currency = Column(String, default="BRL")
    method = Column(String) # PIX, CRYPTO
    type = Column(String)   # IN, OUT
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    app = relationship("App")

class Balance(Base):
    __tablename__ = "balances"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    currency = Column(String, default="BRL")
    available_balance = Column(Numeric(20, 4), default=0.0)
    pending_balance = Column(Numeric(20, 4), default=0.0)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    transaction_id = Column(String, ForeignKey("transactions.id"))
    currency = Column(String)
    amount = Column(Numeric(20, 4))
    entry_type = Column(String) # credit, fee_markup, payout_debit, payout_fee
    created_at = Column(DateTime, default=datetime.utcnow)

class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    priority = Column(Integer, default=100)
    segment_tags = Column(String, default="GLOBAL")
    is_active = Column(Boolean, default=True)

class ProviderAccount(Base):
    __tablename__ = "provider_accounts"
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    daily_limit = Column(Numeric(20, 4), default=0.0)
    current_daily_volume = Column(Numeric(20, 4), default=0.0)
    is_active = Column(Boolean, default=True)
