from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./finai.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    business_name    = Column(String(255), nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    is_active        = Column(Boolean, default=True)
    plan             = Column(String(20), default="free")
    created_at       = Column(DateTime, default=datetime.utcnow)
    transactions     = relationship("Transaction", back_populates="owner", cascade="all, delete-orphan")
    budgets          = relationship("Budget",      back_populates="owner", cascade="all, delete-orphan")
    chat_messages    = relationship("ChatMessage", back_populates="owner", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date        = Column(DateTime, default=datetime.utcnow)
    description = Column(String(500))
    amount      = Column(Float)
    type        = Column(String(20))
    category    = Column(String(100))
    merchant    = Column(String(200))
    currency    = Column(String(10), default="EGP")
    owner       = relationship("User", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category   = Column(String(100), nullable=False)
    amount     = Column(Float, nullable=False)
    month      = Column(String(7), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner      = relationship("User", back_populates="budgets")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role       = Column(String(20))
    content    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner      = relationship("User", back_populates="chat_messages")


def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()