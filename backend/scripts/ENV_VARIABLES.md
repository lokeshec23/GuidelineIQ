# Environment Variables for Admin Seed

This document lists all environment variables that can be used to configure the admin user settings during the seed process.

## Required Variables

### Admin Credentials
```bash
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_password
```

## Optional API Configuration

### Gemini API
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### OpenAI API
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Azure OpenAI Configuration
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

## Optional Model Configuration

### Default Model Settings
```bash
DEFAULT_MODEL_PROVIDER=gemini  # or "openai"
DEFAULT_MODEL_NAME=gemini-2.0-flash-exp  # or "gpt-4o", etc.
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
2. Add the required variables (admin credentials)
3. Add any optional variables you want to configure
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

# API Keys
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Azure OpenAI (if using Azure)
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Default Model
DEFAULT_MODEL_PROVIDER=gemini
DEFAULT_MODEL_NAME=gemini-2.0-flash-exp

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
- API keys are optional but required for the respective features to work
- The seed script will display which settings were successfully configured
- Settings can be updated later through the Settings page in the admin UI
