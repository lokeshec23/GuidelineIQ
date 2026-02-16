# DSCR Template-Based Comparison Implementation

## Overview
This implementation adds DSCR parameter template-based comparison to the GuidelineIQ platform. Instead of relying solely on fuzzy matching between two Excel files, this new approach uses the fixed 46-parameter template from `dscr_config.py` to structure the comparison output.

## Files Created/Modified

### 1. **New File: `backend/compare/dscr_template_processor.py`**
   - **Purpose**: Main comparison processor using DSCR_GUIDELINES template
   - **Key Functions**:
     - `process_dscr_template_comparison()`: Main entry point for template-based comparison
     - `build_dscr_template_comparison()`: Maps data from both guidelines to the 46 DSCR parameters
     - `run_parallel_dscr_comparison()`: Processes comparison in parallel chunks using LLM
     - `parse_and_validate_dscr_response()`: Validates LLM output

### 2. **Modified: `backend/compare/routes.py`**
   - **Changes**: 
     - Added import for `process_dscr_template_comparison`
     - Added new endpoint: `POST /compare/dscr-template`
   
   **New Endpoint Details:**
   - **URL**: `/compare/dscr-template`
   - **Method**: POST
   - **Body**: FormData with:
     - `file1`: Excel file (first guideline)
     - `file2`: Excel file (second guideline)
     - `model_provider`: "openai" (Azure OpenAI)
     - `model_name`: Model name
     - `system_prompt`: (optional) LLM system prompt
     - `user_prompt`: (optional) LLM user prompt
   - **Returns**: CompareResponse with session_id

## How It Works

### Step-by-Step Process:

1. **Load Guidelines**
   - Reads both Excel files into JSON format
   - Example: File1 has 38 parameters, File2 has 42 parameters

2. **Template Mapping**
   - Uses all 46 parameters from `DSCR_GUIDELINES` as the baseline
   - For each template parameter:
     - Searches for matching row in Guideline 1 (by parameter name)
     - Searches for matching row in Guideline 2 (by parameter name)
     - Creates a comparison entry even if parameter is missing from one or both guidelines

3. **LLM Comparison**
   - Chunks the 46 parameters (default: 10 parameters per chunk)
   - Sends each chunk to LLM for analysis
   - LLM extracts key values and generates comparison notes

4. **Excel Output Generation**
   - Creates structured Excel with columns:
     - **DSCR PARAMETERS**: Parameter name (e.g., "Purchase", "Credit Score Requirements")
     - **VARIANCE CATEGORIES**: Category (e.g., "Eligible Transactions", "Credit / Housing")
     - **SUB CATEGORY**: Always "Feature Eligibility"
     - **PPE FIELD TYPE**: "Hard" or "Soft"
     - **[File1 Name]**: Extracted value from first guideline
     - **[File2 Name]**: Extracted value from second guideline
     - **COMPARISON NOTES**: LLM-generated analysis

### Example Output Structure:

| DSCR PARAMETERS | VARIANCE CATEGORIES | SUB CATEGORY | PPE FIELD TYPE | Sharp_DSCR_v1.xlsx | NQM_DSCR_v2.xlsx | COMPARISON NOTES |
|----------------|---------------------|--------------|----------------|-------------------|------------------|------------------|
| Purchase | Eligible Transactions | Feature Eligibility | Hard | Allowed with min 660 FICO | Allowed with min 680 FICO | NQM has slightly stricter credit requirements |
| Credit Score Requirements | Credit / Housing | Feature Eligibility | Hard | Min 660 for standard | Min 680 for standard | NQM requires 20 points higher credit score |
| 2-1 Buydown | Eligible Transactions | Feature Eligibility | Soft | Not present | Allowed with restrictions | Sharp does not offer this product feature |

## Advantages Over Previous Approach

### Old Approach (Fuzzy Matching):
- ✗ Only compares parameters that exist in both files
- ✗ Missing parameters are not highlighted
- ✗ No standardized structure
- ✗ Variable column count depending on input files

### New Approach (DSCR Template):
- ✓ **Always shows all 46 parameters** (comprehensive comparison)
- ✓ **Highlights missing parameters** ("Not present" in guideline)
- ✓ **Standardized structure** matching ingestion format
- ✓ **Consistent columns** regardless of input files
- ✓ **Easier to track product changes** over time

## API Usage

### Frontend Integration

```javascript
// Example: Upload two DSCR guideline Excel files for comparison
const formData = new FormData();
formData.append('file1', file1); // First Excel file
formData.append('file2', file2); // Second Excel file
formData.append('model_provider', 'openai');
formData.append('model_name', 'gpt-4');
formData.append('system_prompt', ''); // Optional
formData.append('user_prompt', ''); // Optional

const response = await fetch('/compare/dscr-template', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const { session_id } = await response.json();

// Monitor progress via SSE
const eventSource = new EventSource(`/compare/progress/${session_id}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.message}`);
  
  if (data.status === 'completed') {
    // Download the result
    window.location.href = `/compare/download/${session_id}`;
    eventSource.close();
  }
};
```

### Backend Testing (curl)

```bash
curl -X POST "http://localhost:8000/compare/dscr-template" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file1=@guideline1.xlsx" \
  -F "file2=@guideline2.xlsx" \
  -F "model_provider=openai" \
  -F "model_name=gpt-4"
```

## Configuration

### DSCR_GUIDELINES Template Source
The 46 parameters are defined in:
```
backend/ingest/dscr_config.py
```

To add/modify/remove parameters, update the `DSCR_GUIDELINES` list in that file.

### LLM Settings
- Default chunk size: 10 parameters
- Configurable in user settings: `comparison_chunk_size`
- Temperature: 0.3 (for consistent responses)
- Max tokens: 8192

## Error Handling

- **Invalid file types**: Returns 400 error with message
- **Missing API keys**: Returns 403 error
- **LLM failures**: Chunks are retried; failed chunks logged separately
- **Invalid parameter names**: Uses fuzzy matching (case-insensitive, whitespace-normalized)

## Future Enhancements

1. **Add from-DB support**: Allow selecting two ingested guidelines from history for DSCR template comparison
2. **Custom templates**: Allow users to define their own parameter templates
3. **Diff visualization**: Highlight changes in a more visual format
4. **Export to multiple formats**: PDF, CSV, JSON
5. **Batch comparison**: Compare multiple versions at once (e.g., v1 vs v2 vs v3)

## Testing

### Manual Test Steps:

1. **Prepare Test Files**:
   - Get two Excel files with DSCR parameters
   - Ensure they have `DSCR_Parameters` column

2. **Start Backend**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

3. **Test API Endpoint**:
   - Use Postman or curl to call `/compare/dscr-template`
   - Upload two files
   - Monitor progress via `/compare/progress/{session_id}`

4. **Verify Output**:
   - Download Excel from `/compare/download/{session_id}`
   - Verify all 46 parameters are present
   - Check comparison notes quality

### Unit Tests (TODO):
- Test `build_dscr_template_comparison()` with various input combinations
- Test parameter name normalization and matching
- Test LLM response parsing

## Deployment Notes

- No database migrations required
- No frontend changes required (uses existing comparison UI)
- Backwards compatible with existing comparison endpoints
- Can be deployed alongside current comparison methods

## Support

For questions or issues:
1. Check logs in `backend/logs/app.log`
2. Verify DSCR_GUIDELINES template is up to date
3. Confirm API keys are configured correctly

---

**Implementation Date**: 2026-02-02
**Version**: 1.0  
**Author**: Antigravity AI
