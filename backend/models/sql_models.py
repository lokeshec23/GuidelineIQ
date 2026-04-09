# backend/models/sql_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, LargeBinary, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime
import uuid
from sql_database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ingest_history = relationship("IngestHistory", back_populates="user", cascade="all, delete-orphan")
    compare_history = relationship("CompareHistory", back_populates="user", cascade="all, delete-orphan")
    prompts = relationship("UserPrompts", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    settings_json = Column(JSON, nullable=True) # Stores the flexible settings dictionary
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

    user = relationship("User", back_populates="settings")

class IngestHistory(Base):
    __tablename__ = "ingest_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    username = Column(String(255), nullable=True)
    investor = Column(String(255), nullable=True)
    version = Column(String(255), nullable=True)
    uploaded_file = Column(Text, nullable=True) # Filenames string
    extracted_file = Column(Text, nullable=True)
    preview_data = Column(JSON, nullable=True)
    effective_date = Column(String(255), nullable=True)
    expiry_date = Column(String(255), nullable=True)
    gridfs_file_id = Column(String(255), nullable=True) # Kept for reference, mapped to File table ID ideally
    pdf_files = Column(JSON, nullable=True) # Array of PDF metadata
    page_range = Column(String(255), nullable=True)
    guideline_type = Column(String(255), nullable=True)
    program_type = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="ingest_history")

class CompareHistory(Base):
    __tablename__ = "compare_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    username = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)
    investor = Column(String(255), nullable=True)
    version = Column(String(255), nullable=True)
    uploaded_file1 = Column(Text, nullable=True)
    uploaded_file2 = Column(Text, nullable=True)
    extracted_file = Column(Text, nullable=True)
    preview_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="compare_history")

class UserPrompts(Base):
    __tablename__ = "user_prompts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    ingest_prompts = Column(JSON, nullable=True)
    compare_prompts = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())
    
    user = relationship("User", back_populates="prompts")

class DefaultPrompts(Base):
    __tablename__ = "default_prompts"
    
    id = Column(String(36), primary_key=True, default="system_defaults")
    ingest_prompts = Column(JSON, nullable=True)
    compare_prompts = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(255), nullable=False, index=True) # Ingestion/Comparison session ID
    title = Column(String(255), nullable=True)
    last_message = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    messages = relationship("ChatSession", back_populates="conversation", cascade="all, delete-orphan")

class ChatSession(Base):
    __tablename__ = "chat_sessions" # Corresponds to individual messages in the old system logic (confusing naming in old sys)

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # session_id here might be the ingestion session or the conversation grouping. 
    # In old code, messages had `session_id` and optional `conversation_id`.
    session_id = Column(String(255), nullable=False, index=True) 
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=True)
    role = Column(String(50), nullable=False) # user / assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("ChatConversation", back_populates="messages")

class File(Base):
    """
    Replacement for GridFS. Stores file content directly in DB.
    """
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=True)
    content = Column(LargeBinary, nullable=False) # VARBINARY(MAX)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Investor(Base):
    """
    Model for Investors. Parameters can be assigned to an investor. 
    If not assigned, they are treated as 'General' parameters.
    """
    __tablename__ = "investors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    parameters = relationship("DSCRParameter", back_populates="investor", cascade="all, delete-orphan")


class DSCRParameter(Base):
    """
    Model for Parameters configuration (DSCR / Full Doc / Alt Doc).
    """
    __tablename__ = "dscr_parameters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    parameter = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)
    subcategory = Column(String(255), nullable=True)
    ppe_field = Column(String(255), nullable=True)
    guideline_type = Column(JSON, nullable=True)  # e.g. ["All"], ["DSCR", "Full Doc"]
    investor_id = Column(String(36), ForeignKey("investors.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Composite Index for performance on List Parameters call
    __table_args__ = (
        Index("ix_dscr_params_investor_cat_name", "investor_id", "category", "parameter"),
    )

    investor = relationship("Investor", back_populates="parameters")
