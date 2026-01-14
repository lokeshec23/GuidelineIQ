# Azure OpenAI Configuration Guide

## Quick Setup

Based on your Azure OpenAI configuration, add this to your `.env` file:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://-oai.openai.azure.com
AZURE_OPENAI_API_KEY=46c387a4d08e43939514bf855bcb8e17
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model
```

## Steps to Apply Configuration

### 1. Update Environment Variables

Create or update your `.env` file in the backend directory with the configuration above.

### 2. Re-run the Admin Seed Script

This will update your admin settings with the embedding deployment:

```bash
cd backend
python scripts/seed_admin.py
```

Expected output:
```
✅ Admin user already exists: user@user.com
🔧 Initializing admin settings from environment variables...
✅ Admin settings initialized successfully!
   ✓ OpenAI API Key: ********************8e17
   ✓ Azure Endpoint: https://-oai.openai.azure.com
   ✓ Azure Chat Deployment: gpt-35-turbo
   ✓ Azure Embedding Deployment: embedding-model
```

### 3. Restart Your Backend Server

Stop and restart your FastAPI server to load the new configuration:

```bash
# Stop the current server (Ctrl+C)
# Then restart
uvicorn main:app --reload --port 8000
```

## What Changed

### Files Modified

1. **[rag_service.py](file:///c:/Users/LDNA40022/Lokesh/GuidelineIQ/backend/chat/rag_service.py)**
   - Now uses `embedding-model` as default deployment
   - Separates chat and embedding deployments

2. **[settings/schemas.py](file:///c:/Users/LDNA40022/Lokesh/GuidelineIQ/backend/settings/schemas.py)**
   - Added `openai_embedding_deployment` field

3. **[scripts/seed_admin.py](file:///c:/Users/LDNA40022/Lokesh/GuidelineIQ/backend/scripts/seed_admin.py)**
   - Loads `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` from environment
   - Defaults to `embedding-model` if not specified

4. **[processor.py](file:///c:/Users/LDNA40022/Lokesh/GuidelineIQ/backend/ingest/processor.py)** & **[dscr_extractor.py](file:///c:/Users/LDNA40022/Lokesh/GuidelineIQ/backend/ingest/dscr_extractor.py)**
   - Updated to use `embedding-model` as default

## Verification

After restarting, test the embedding generation:

1. Upload a PDF through your frontend
2. Check the terminal logs - you should see:
   ```
   ⚡ Generating embeddings for X chunks from PDF 1...
   ✅ RAG: Stored X chunks from PDF 1 in Vector DB.
   ```
3. **No more 404 errors** about `DeploymentNotFound`

## Troubleshooting

### Still getting 404 errors?

1. Verify your Azure deployment name is exactly `embedding-model`
2. Check Azure portal to confirm the deployment exists
3. Ensure the deployment is in the same resource as your endpoint

### Different deployment name?

If your embedding deployment has a different name, update the `.env` file:
```env
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-actual-deployment-name
```

Then re-run the seed script.
