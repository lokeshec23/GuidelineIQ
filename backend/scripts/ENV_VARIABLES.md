# Environment Variables for Admin Seed

This document lists all environment variables that can be used to configure the admin user settings during the seed process.

## Required Variables

### Admin Credentials
```bash
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_password
```

## API Configuration

### Azure OpenAI (Required)
```bash
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

## Model Configuration

### Default Model Settings
```bash
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o
```

### LLM Parameters
```bash
DEFAULT_TEMPERATURE=0.3
DEFAULT_MAX_TOKENS=8192
DEFAULT_TOP_P=0.95
```

### PDF Processing
```bash
DEFAULT_PAGES_PER_CHUNK=5
```

### Comparison Settings
```bash
COMPARISON_CHUNK_SIZE=10
MAX_COMPARISON_CHUNKS=0  # 0 means no limit
```

## Usage

1. Create a `.env` file in the `backend` directory
2. Add the required variables (admin credentials + Azure OpenAI)
3. Add any optional parameters you want to configure
4. Run the seed script:

```bash
cd backend
python scripts/seed_admin.py
```

## Example .env File

```bash
# Admin Credentials (Required)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@guidelineiq.com
ADMIN_PASSWORD=SecurePassword123!

# Azure OpenAI (Required)
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model

# Default Model
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4o

# LLM Parameters
DEFAULT_TEMPERATURE=0.3
DEFAULT_MAX_TOKENS=8192
DEFAULT_TOP_P=0.95

# Processing Settings
DEFAULT_PAGES_PER_CHUNK=5
COMPARISON_CHUNK_SIZE=10
MAX_COMPARISON_CHUNKS=0
```

## Notes

- If a variable is not set, the script will use default values where applicable
- Azure OpenAI credentials are required for ingestion, comparison, and chatbot features
- The seed script will display which settings were successfully configured
- Settings can be updated later through the Settings page in the admin UI
