import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, JSON, Integer, Enum
from sqlalchemy.orm import relationship, backref
from database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class TicketStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class TicketType(enum.Enum):
    MANUAL_CASHOUT = "MANUAL_CASHOUT"
    REFUND_REVIEW = "REFUND_REVIEW"
    RISK_ALERT = "RISK_ALERT"
    MANUAL_VALIDATION = "MANUAL_VALIDATION"

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=generate_uuid)
    parent_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    name = Column(String, nullable=False)
    document = Column(String, nullable=True)
    account_type = Column(String, default="SUBSIDIARY")
    tier = Column(String, default="GOLD")
    fee_config = Column(JSON, nullable=False, default={})
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    subsidiaries = relationship("Account", backref=backref('parent', remote_side=[id]))
    apps = relationship("App", back_populates="account")
    balances = relationship("Balance", back_populates="account")
    users = relationship("User", back_populates="account")
    provider_accounts = relationship("ProviderAccount", back_populates="account")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="admin")
    account = relationship("Account", back_populates="users")

class App(Base):
    __tablename__ = "apps"
    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"))
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    discord_webhook = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    
    # 🏦 O LIVRO DE ENDEREÇOS DO CLIENTE (Carteiras Crypto e PIX)
    payout_settings = Column(JSON, default={}) 
    
    status = Column(String, default="active")

    account = relationship("Account", back_populates="apps")
    transactions = relationship("Transaction", back_populates="app")

class Provider(Base):
    __tablename__ = "providers"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default="active")
    priority = Column(Integer, default=10)
    provider_accounts = relationship("ProviderAccount", back_populates="provider")

class ProviderAccount(Base):
    __tablename__ = "provider_accounts"
    id = Column(String, primary_key=True, default=generate_uuid)
    provider_id = Column(String, ForeignKey("providers.id"))
    account_id = Column(String, ForeignKey("accounts.id"))
    credentials_encrypted = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    daily_limit = Column(Float, default=0.0)
    current_daily_volume = Column(Float, default=0.0)
    cost_config = Column(JSON, default={})
    status = Column(String, default="active")
    provider = relationship("Provider", back_populates="provider_accounts")
    account = relationship("Account", back_populates="provider_accounts")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=generate_uuid)
    app_id = Column(String, ForeignKey("apps.id"))
    provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    provider_reference = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="BRL")
    method = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    app = relationship("App", back_populates="transactions")

class Balance(Base):
    __tablename__ = "balances"
    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"))
    currency = Column(String, default="BRL")
    available_balance = Column(Float, default=0.0)
    pending_balance = Column(Float, default=0.0)
    account = relationship("Account", back_populates="balances")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(String, primary_key=True, default=generate_uuid)
    account_id = Column(String, ForeignKey("accounts.id"))
    transaction_id = Column(String, ForeignKey("transactions.id"))
    currency = Column(String, default="BRL")
    amount = Column(Float, nullable=False)
    entry_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class NocTicket(Base):
    __tablename__ = "noc_tickets"
    id = Column(String, primary_key=True, default=generate_uuid)
    ticket_type = Column(Enum(TicketType), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.PENDING, nullable=False)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    amount = Column(Float, nullable=True)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    provider = relationship("Provider")
