# backend/rag_pipeline/config.py
"""
Configuration for RAG Pipeline
Integrates with existing .env configuration
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class RAGConfig:
    """Configuration for RAG Pipeline"""
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    
    # Deployment names from .env
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-model")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "extraction-model")
    
    # Azure Document Intelligence (OCR Fallback)
    AZURE_DI_ENDPOINT: str = os.getenv("DI_endpoint", "")
    AZURE_DI_KEY: str = os.getenv("DI_key", "")
    
    # Qdrant Configuration
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL")  # Default to None to allow path fallback
    QDRANT_PATH: Optional[str] = os.getenv("QDRANT_PATH")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION: str = "DSCR_GUIDELINES"  # New collection for production RAG
    
    # LLM Parameters (Deterministic)
    EXTRACTION_TEMPERATURE: float = 0.0  # Deterministic extraction
    VERIFICATION_TEMPERATURE: float = 0.0  # Deterministic verification
    MAX_TOKENS: int = 4096
    
    # Chunking Parameters
    CHUNK_SIZE: int = 500  # tokens
    CHUNK_OVERLAP: int = 50  # tokens
    MAX_CHUNK_SIZE: int = 1000  # tokens
    
    # Retrieval Parameters
    TOP_K_BM25: int = 10
    TOP_K_VECTOR: int = 10
    TOP_K_FINAL: int = 5
    TOP_K_COMPREHENSIVE: int = 1000  # "All" matches
    BM25_WEIGHT: float = 0.3
    VECTOR_WEIGHT: float = 0.7
    
    # Table Detection Keywords
    TABLE_KEYWORDS: list = [
        "LTV", "FICO", "DSCR", "DTI", "matrix", "tier", "rate",
        "minimum", "maximum", "range", "score", "ratio"
    ]
    
    # Section Detection Patterns
    HEADING_PATTERNS: list = [
        r"^[A-Z\s]{3,}$",  # ALL CAPS
        r"^\d+\.\s+[A-Z]",  # Numbered sections
        r"^[A-Z][a-z]+\s+[A-Z]",  # Title Case
    ]
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.path.join(os.getcwd(), "logs", "rag_pipeline")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_fields = [
            ("AZURE_OPENAI_API_KEY", cls.AZURE_OPENAI_API_KEY),
            ("AZURE_OPENAI_ENDPOINT", cls.AZURE_OPENAI_ENDPOINT),
            ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", cls.AZURE_OPENAI_EMBEDDING_DEPLOYMENT),
            ("AZURE_OPENAI_DEPLOYMENT_NAME", cls.AZURE_OPENAI_DEPLOYMENT_NAME),
        ]
        
        missing = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing.append(field_name)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_embedding_config(cls) -> dict:
        """Get embedding configuration for Azure OpenAI"""
        return {
            "api_key": cls.AZURE_OPENAI_API_KEY,
            "endpoint": cls.AZURE_OPENAI_ENDPOINT,
            "api_version": cls.AZURE_OPENAI_API_VERSION,
            "deployment": cls.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        }
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """Get LLM configuration for Azure OpenAI"""
        return {
            "api_key": cls.AZURE_OPENAI_API_KEY,
            "endpoint": cls.AZURE_OPENAI_ENDPOINT,
            "api_version": cls.AZURE_OPENAI_API_VERSION,
            "deployment": cls.AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": cls.EXTRACTION_TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS
        }
    
    @classmethod
    def get_qdrant_config(cls) -> dict:
        """Get Qdrant configuration"""
        return {
            "url": cls.QDRANT_URL,
            "path": cls.QDRANT_PATH,
            "api_key": cls.QDRANT_API_KEY,
            "collection_name": cls.QDRANT_COLLECTION
        }


# Validate configuration on import
try:
    RAGConfig.validate()
except ValueError as e:
    print(f"[WARN] RAG Configuration validation failed: {e}")
