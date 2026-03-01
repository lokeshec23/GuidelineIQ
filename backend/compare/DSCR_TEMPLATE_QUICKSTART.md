# Quick Start Guide: DSCR Template Comparison

## What is DSCR Template Comparison?

This new comparison method ensures that **all 46 DSCR parameters** from your template are always included in the comparison output, even if some parameters are missing from one or both guidelines.

## When to Use This vs Regular Comparison?

### Use **DSCR Template Comparison** when:
- ✅ You want a **complete, standardized** comparison across all DSCR parameters
- ✅ You need to identify **missing parameters** in one guideline
- ✅ You want output that **matches the ingestion Excel format**
- ✅ You're comparing **DSCR/Business Purpose** loan guidelines

### Use **Regular Comparison** when:
- ✅ You're comparing **non-DSCR guidelines** (e.g., conforming, jumbo)
- ✅ The guidelines have **custom/unique parameters** not in the DSCR template
- ✅ You want a **minimal output** with only matching parameters

## How to Use (API)

### Endpoint
```
POST /compare/dscr-template
```

### Request (multipart/form-data)
```javascript
{
  file1: <Excel File>,           // Required: First guideline Excel
  file2: <Excel File>,           // Required: Second guideline Excel
  model_provider: "openai",      // Required: "openai" (Azure OpenAI)
  model_name: "gpt-4",           // Required: Model name
  system_prompt: "",             // Optional: LLM system prompt
  user_prompt: ""                // Optional: LLM user prompt
}
```

### Response
```json
{
  "status": "processing",
  "message": "DSCR template comparison started",
  "session_id": "abc-123-xyz"
}
```

## Expected Input Format

Your Excel files should have a column named one of:
- `DSCR_Parameters`
- `DSCR Parameters`
- `dscr_parameters`
- `Parameter`
- `parameter`

Example Row:
| DSCR_Parameters | Variance_Category | SubCategory | PPE_Field_Type | NQMF Investor DSCR |
|----------------|-------------------|-------------|----------------|-------------------|
| Purchase | Eligible Transactions | Feature Eligibility | Hard | Allowed for primary, secondary, and investment properties... |

## Output Format

The resulting Excel will always have these columns:

1. **DSCR PARAMETERS** - Parameter name from template
2. **VARIANCE CATEGORIES** - Category (e.g., "Eligible Transactions")
3. **SUB CATEGORY** - Always "Feature Eligibility"
4. **PPE FIELD TYPE** - "Hard" or "Soft"
5. **[Guideline 1 Filename]** - Extracted value from first file
6. **[Guideline 2 Filename]** - Extracted value from second file
7. **COMPARISON NOTES** - LLM analysis of differences

### Example Output Row:
| DSCR PARAMETERS | VARIANCE CATEGORIES | SUB CATEGORY | PPE FIELD TYPE | Sharp_DSCR.xlsx | TLS_DSCR.xlsx | COMPARISON NOTES |
|----------------|---------------------|--------------|----------------|-----------------|---------------|------------------|
| Credit Score Requirements | Credit / Housing | Feature Eligibility | Hard | Min 660 for standard DSCR loans | Min 680 for all DSCR products | TLS has stricter credit requirements (+20 points) |

## Workflow

```
1. User uploads two DSCR guideline Excel files
                 ↓
2. System loads DSCR_GUIDELINES template (46 parameters)
                 ↓
3. For each parameter, system searches both files for matches
                 ↓
4. Creates 46 comparison entries (one per parameter)
                 ↓
5. Sends to LLM in chunks for analysis
                 ↓
6. Generates Excel with all 46 parameters
                 ↓
7. User downloads structured comparison
```

## Advantages

### ✅ Comprehensive Coverage
- **46 parameters always included** (never miss a parameter)
- **Highlights missing parameters** with "Not present"

### ✅ Standardized Structure
- **Same columns** every time
- **Matches ingestion format**
- **Easy to compare** across multiple versions

### ✅ Better Insights
- **LLM analyzes** each parameter
- **Explains differences** in natural language
- **Identifies trends** (e.g., "TLS is generally stricter on credit")

## Example Scenarios

### Scenario 1: Both guidelines have the parameter
```
Parameter: "Purchase"
Guideline 1: "Allowed for all property types"
Guideline 2: "Allowed for primary residence only"
→ Output: Both values shown + comparison notes explaining restriction
```

### Scenario 2: Only one guideline has the parameter
```
Parameter: "2-1 Buydown"
Guideline 1: "Not present"
Guideline 2: "Allowed with specific pricing adjustments"
→ Output: Highlights that Guideline 1 doesn't offer this product
```

### Scenario 3: Neither guideline has the parameter
```
Parameter: "Condotels"
Guideline 1: "Not present"
Guideline 2: "Not present"
→ Output: Shows both as "Not present" - parameter not addressed
```

## Troubleshooting

### Issue: "No matching parameters found"
**Solution**: Ensure your Excel has a column named `DSCR_Parameters` or similar

### Issue: "All values showing as 'Not present'"
**Solution**: Check capitalization and spacing in column header

### Issue: "Comparison taking too long"
**Solution**: Check LLM API status and chunk size settings (default: 10 params/chunk)

## Next Steps

1. **Test the endpoint** with sample Excel files
2. **Review output quality** and adjust prompts if needed
3. **Integrate into frontend** UI (optional - works with existing comparison page)
4. **Add to workflows** for regular guideline updates

---

Need help? Check the full documentation in `DSCR_TEMPLATE_COMPARISON_README.md`
