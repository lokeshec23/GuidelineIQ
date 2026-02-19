# GuidelineIQ AI Coding Agent Instructions

## Project Overview
**GuidelineIQ** is a mortgage guideline extraction and comparison platform. It uses RAG (Retrieval-Augmented Generation) to parse mortgage PDF guidelines, extract structured parameters (DSCR/credit rules), and generate side-by-side comparisons via LLM analysis.

### Core Tech Stack
- **Backend**: FastAPI + SQLAlchemy (async) + SQL Server + MongoDB
- **Frontend**: React 19 + Vite + Ant Design + TailwindCSS
- **RAG Pipeline**: Qdrant (semantic search) + BM25 (keyword search) + Azure OpenAI embeddings
- **PDF Processing**: pdfplumber (primary) → Azure OCR (fallback)

---

## Architecture Patterns

### 1. **Backend Service Layer (FastAPI Router Pattern)**
All routes are organized by domain in `/backend/{domain}/routes.py` with supporting modules:
- `routes.py`: HTTP endpoints with FastAPI dependencies (auth, file upload, SSE streams)
- `schemas.py`: Pydantic models for request/response validation
- `models.py`: Database models (SQL or MongoDB)
- `service.py`: Core business logic (optional, used in chat/)

**File Upload + Background Processing Pattern** (ingest, compare):
```python
# Endpoint immediately returns session_id
# Background task processes asynchronously
# Frontend tracks progress via Server-Sent Events (SSE)
background_tasks.add_task(process_fn, session_id=uuid, ...)
return IngestResponse(status="processing", session_id=session_id)

# Progress tracked in `progress_store` dict with lock (progress.py)
```

### 2. **Dual Database Model**
- **SQL Server** (primary): Users, authentication, DSCR parameters, ingest/compare history metadata
- **MongoDB**: `ingest_history`, `compare_history` - stores extracted data & preview JSON for reprocessing
- **Hybrid Example**: `ingest_history` stored in MongoDB, but indexed in SQL `IngestHistory` for querying

### 3. **RAG Pipeline Architecture**
Located in `/backend/rag_pipeline/`:
```
PDF → pdfplumber/OCR Parser 
  → Section-Aware Chunker (tracks section_path hierarchy)
  → Embedder (Azure OpenAI text-embedding-3-large)
  → Qdrant Index (collection: "DSCR_GUIDELINES")
  
Query → Hybrid Retriever (BM25 keywords + vector semantic)
  → LLM Extractor (temperature=0 for deterministic output)
  → LLM Verifier (dual-pass QA)
```

**Qdrant Collection Metadata**: `lender`, `program`, `version`, `section_path`, `chunk_type` (NARRATIVE/TABLE/HEADING)

### 4. **DSCR Template Comparison (Primary Comparison Method)**
- **46 fixed DSCR parameters** defined in `/backend/ingest/dscr_config.py` serve as comparison baseline
- **Fuzzy matching** (difflib + containment logic) maps uploaded Excel rows to template parameters
- **Chunked LLM Processing**: Parameters split into groups (~10 per chunk), each processed independently
- **Output**: Excel with template parameters as rows, "Guideline 1" / "Guideline 2" columns, comparison notes

**Key Implementation Files**:
- [backend/compare/dscr_template_processor.py](backend/compare/dscr_template_processor.py) - template matching & LLM chunking
- [backend/compare/routes.py](backend/compare/routes.py#L254) - `/compare/dscr-template` endpoint (primary flow)

---

## Critical Developer Workflows

### Build & Run
**Frontend** (Vite):
```bash
cd frontend && npm install && npm run dev  # http://localhost:5173
npm run build  # Production build
```

**Backend** (FastAPI):
```bash
cd backend && pip install -r requirements.txt
python main.py  # Starts on http://localhost:8000
# Auto-runs seed_admin() + seed_dscr_params() on startup (lifespan context manager)
```

**Qdrant** (Vector DB):
```bash
docker run -p 6333:6333 qdrant/qdrant  # Required for RAG pipeline
```

### Database Initialization
- SQL Server DB created by `backend/sql_database.py::init_db()` (async) on app startup
- MongoDB connection via `from database import db_manager` (singleton)
- **Seeding**: `backend/scripts/seed_admin.py` + `seed_dscr_params.py` run on FastAPI lifespan startup

### Testing Comparison Workflow
1. Ingest PDF via `/ingest/guideline` → extracts DSCR parameters → stored in MongoDB `ingest_history`
2. Upload 2 guidelines to `/compare/dscr-template` → fuzzy-matches to 46 DSCR template → LLM comparison → Excel download
3. OR: Select 2 from history via `/compare/from-db` → regenerates Excel from preview_data → same LLM comparison

---

## Project-Specific Conventions

### 1. **Error Handling & Logging**
- All exceptions → logged via `setup_logger(__name__)` in `utils/logger.py`
- FastAPI endpoints raise `HTTPException(status_code=4xx, detail="...")` 
- Background tasks log errors but don't re-raise (logged, progress_store updated with `error` status)

### 2. **Authentication Pattern**
- JWT tokens (`access_token`, `refresh_token`) issued by `/auth/login`
- Dependency: `get_current_user_id_from_token(authorization: str = Header(...))` extracts Bearer token
- Token payload contains `sub` (user_id), `type` ("access"/"refresh")
- **Important**: Always validate token type and expiration (see [auth/utils.py](backend/auth/utils.py))

### 3. **LLM Provider Configuration**
- Single entry point: `utils/llm_provider.py` wraps OpenAI, Gemini, Azure OpenAI
- **Deterministic extraction**: Always use `temperature=0`, `top_p=1.0`
- **Models** in [backend/config.py](backend/config.py#L40): `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
- **Token limits** configured per model (e.g., gpt-4o: 128k input, 16k output)

### 4. **Prompt Management**
- System/user prompts stored per-model in MongoDB `user_settings.prompts` 
- Defaults in [backend/config.py](backend/config.py#L75) for extraction & comparison
- Frontend fetches via `/prompts/` → displays in forms → sent back with ingest/compare requests
- **Critical**: Prompts must output **valid JSON only** (no markdown, no explanations)

### 5. **Excel I/O Convention**
- All outputs use `utils/json_to_excel.py::dynamic_json_to_excel(json_data, filepath)`
- Extraction: JSON array of dicts → Excel (each dict = row)
- Comparison: Columns auto-detected from JSON keys, special handling for "guideline_1"/"guideline_2"/"comparison_notes"
- **Important**: Excel file generated from `preview_data` (JSON stored in MongoDB), not re-parsed from uploaded file

### 6. **Frontend State Management**
- No Redux; uses **React Context** for global state (auth, prompts in `src/context/`)
- Components in `src/pages/{Domain}/` mirror backend routes (IngestPage, ComparePage, HistoryPage)
- API calls via `src/services/api.js` - centralized Axios config with auth header injection
- Progress tracking: SSE (Server-Sent Events) for streaming updates during async processing

### 7. **Progress Tracking (In-Memory Store)**
- Backend: `progress_store` dict (keyed by `session_id`) updated in real-time
- Frontend: SSE stream from `/ingest/progress/{session_id}` or `/compare/progress/{session_id}`
- **Critical**: Progress updates trigger modal progress bar + download link once complete
- Cleanup: `/ingest/cleanup/{session_id}` or automatic on file download

---

## Data Flow Examples

### Ingest PDF Example
1. POST `/ingest/guideline` (files, investor, version, model_provider, model_name, prompts)
2. **Async background task** calls `process_guideline_background()`
   - Parses PDF → pdfplumber, fallback to Azure OCR
   - Chunks text with section hierarchy
   - Embeds via Azure OpenAI → stores in Qdrant
   - Extracts DSCR parameters via LLM (10 at a time, dual-pass verify)
   - Stores `preview_data` (JSON) in MongoDB `ingest_history`
3. Frontend polls SSE for progress → downloads Excel from `/ingest/download/{session_id}`

### Compare Workflow (Template-Based)
1. POST `/compare/dscr-template` (file1, file2, model_provider, model_name)
2. **Background task** `process_dscr_template_comparison()`
   - Reads both Excel files → detect parameter column (heuristic)
   - Fuzzy-match each row to 46 DSCR template parameters
   - Build comparison JSON (parameter, guideline_1, guideline_2)
   - Chunk comparison data (10 params per chunk) → send to LLM in parallel
   - LLM analyzes each chunk → returns structured JSON (gap_analysis, comparison_notes)
   - Merge LLM results + generate final Excel
3. Frontend monitors SSE → downloads Excel

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [backend/main.py](backend/main.py) | FastAPI app setup, router registration, lifespan |
| [backend/config.py](backend/config.py) | LLM models, token limits, default prompts, DB URIs |
| [backend/sql_database.py](backend/sql_database.py) | Async SQLAlchemy engine, session factory |
| [backend/rag_pipeline/pipeline.py](backend/rag_pipeline/pipeline.py) | RAG orchestration (ingest + extract) |
| [backend/ingest/dscr_config.py](backend/ingest/dscr_config.py) | 46 DSCR template parameters (baseline) |
| [backend/compare/dscr_template_processor.py](backend/compare/dscr_template_processor.py) | Fuzzy matching, LLM chunking, comparison |
| [backend/compare/routes.py](backend/compare/routes.py) | Comparison endpoints (/guidelines, /dscr-template, /from-db) |
| [backend/auth/utils.py](backend/auth/utils.py) | JWT token creation/validation |
| [frontend/src/services/api.js](frontend/src/services/api.js) | Centralized API client (ingest, compare, history) |
| [frontend/src/pages/Compare/ComparePage.jsx](frontend/src/pages/Compare/ComparePage.jsx) | Comparison UI logic (file upload, DB selection, SSE) |

---

## Common Modifications

### Adding a New DSCR Parameter
1. Add entry to [backend/ingest/dscr_config.py](backend/ingest/dscr_config.py#L6) `DSCR_GUIDELINES` list
2. Update `DSCRParameter` SQL model if storing in SQL
3. Regenerate comparison template (auto-generated, no manual steps needed)

### Changing Default Prompts
1. Edit [backend/config.py](backend/config.py#L75) `DEFAULT_*_PROMPT` constants
2. Update frontend form defaults in `src/constants/prompts.js`
3. Regenerate via admin settings API or clear MongoDB user_settings

### Adding New LLM Provider
1. Extend `utils/llm_provider.py` with new provider class
2. Add to [backend/config.py](backend/config.py#L40) `SUPPORTED_MODELS` dict
3. Update frontend model selection dropdown (`src/pages/IngestPage.jsx`, etc.)

### Debugging SSE Progress Issues
- Check `progress_store` in-memory dict (`utils/progress.py`) for session_id
- Verify task is updating via `update_progress(session_id, progress_pct, message)`
- Check browser DevTools → Network tab → SSE connection status
- Common issue: Connection timeout if task runs > 5min without progress update

---

## Testing Considerations
- **RAG Pipeline**: Requires Qdrant running + Azure/OpenAI API keys
- **Comparison**: Mock LLM responses via `unittest.mock` for unit tests (API calls expensive)
- **Async Database**: Use `pytest-asyncio` for testing async SQL operations
- **Frontend**: Vite dev server supports hot module reload; tests use Vitest

---

## Import Patterns to Preserve

**Backend imports** follow these conventions:
```python
# Standard lib
import os, json, uuid, tempfile, asyncio

# Third-party (FastAPI, SQLAlchemy, etc.)
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends

# Local modules (absolute paths from /backend/)
from config import SUPPORTED_MODELS
from utils.logger import setup_logger
from sql_database import AsyncSessionLocal
from auth.utils import verify_token
from database import db_manager  # MongoDB singleton
```

**Frontend imports** follow these conventions:
```javascript
// React + Router
import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';

// Third-party UI
import { Button, Form, Upload, Spin, Modal } from 'antd';

// Local modules
import { compareAPI, ingestAPI } from '../services/api';
import { usePrompts } from '../context/PromptContext';
```
