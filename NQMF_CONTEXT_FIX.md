# NQMF Context Length Fix

## Problem
The NQMF extraction was failing with error:
```
Error code: 400 - {'error': {'message': "This model's maximum context length is 128000 tokens. 
However, your messages resulted in 816485 tokens. Please reduce the length of the messages.", 
'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}}
```

## Root Cause
The RAG pipeline was configured to retrieve up to **1000 chunks** (`TOP_K_COMPREHENSIVE = 1000`) and then include the **full text** of all these chunks in the LLM prompt. This resulted in prompts exceeding the 128K token limit of the OpenAI model.

## Solution Implemented

### 1. Reduced TOP_K_COMPREHENSIVE (config.py)
- **Before**: `TOP_K_COMPREHENSIVE: int = 1000`
- **After**: `TOP_K_COMPREHENSIVE: int = 50`
- This limits the initial retrieval to 50 most relevant chunks instead of 1000

### 2. Added MAX_EVIDENCE_CHUNK_LENGTH (config.py)
- **New setting**: `MAX_EVIDENCE_CHUNK_LENGTH: int = 1500`
- Limits each chunk's text to 1500 characters in the LLM prompt
- Prevents individual chunks from consuming excessive tokens

### 3. Implemented Chunk Text Truncation (llm_extractor.py)
- Modified `_build_nqmf_user_prompt()` to truncate chunk text:
  ```python
  chunk_text = chunk.text
  if len(chunk_text) > max_chunk_length:
      chunk_text = chunk_text[:max_chunk_length] + "... [truncated]"
  ```

### 4. Added Hard Limit on Evidence Chunks (llm_extractor.py)
- Modified `extract_nqmf()` to enforce maximum of 30 chunks:
  ```python
  MAX_CHUNKS_FOR_NQMF = 30
  if len(evidence_chunks) > MAX_CHUNKS_FOR_NQMF:
      evidence_chunks = evidence_chunks[:MAX_CHUNKS_FOR_NQMF]
  ```
- Keeps only the top-ranked chunks (already sorted by relevance)

## Impact

### Token Estimation
With these changes, the maximum context size per parameter extraction is approximately:
- **System prompt**: ~3,000 tokens
- **Evidence chunks**: 30 chunks × 1,500 chars ≈ 45,000 chars ≈ 11,250 tokens
- **User prompt overhead**: ~500 tokens
- **Total**: ~15,000 tokens (well within 128K limit)

### Trade-offs
- **Pro**: Prevents context overflow errors
- **Pro**: Faster processing (fewer chunks to process)
- **Pro**: More focused extraction (only most relevant chunks)
- **Con**: May miss some edge cases if relevant info is in chunks ranked 31-50
- **Mitigation**: The hybrid retrieval (BM25 + vector) ensures top 30 chunks are highly relevant

## Testing Recommendation
1. Restart the backend server to load the new configuration
2. Re-run the NQMF extraction that was failing
3. Monitor the logs for any "Truncating evidence" warnings
4. Verify the extraction quality is maintained

## Files Modified
1. `backend/rag_pipeline/config.py`
2. `backend/rag_pipeline/extraction/llm_extractor.py`
