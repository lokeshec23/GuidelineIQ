# Script to add DSCR template comparison route to routes.py

NEW_ROUTE = '''
@router.post("/dscr-template", response_model=CompareResponse)
async def compare_with_dscr_template(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    model_provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: str = Form(""),
    user_prompt: str = Form(""),
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Compare two DSCR guideline Excel files using the DSCR_GUIDELINES template.
    
    This endpoint:
    1. Uses the fixed 46 DSCR parameters from dscr_config.py as the template
    2. Matches values from both uploaded guidelines to each parameter
    3. Generates a structured comparison with all parameters
    4. Creates Excel output with columns:
       - DSCR PARAMETERS
       - VARIANCE CATEGORIES
       - SUB CATEGORY
       - PPE FIELD TYPE
       - [File1 Name] (Guideline 1 values)
       - [File2 Name] (Guideline 2 values)
       - COMPARISON NOTES
    """
    
    logger.info(f"DSCR Template comparison request: File1={file1.filename}, File2={file2.filename}, Provider={model_provider}, Model={model_name}, UserID={user_id}")

    # Validate model
    if model_provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {model_provider}")

    if model_name not in SUPPORTED_MODELS[model_provider]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{model_name}' for provider '{model_provider}'"
        )
    
    # Fetch admin's settings
    from database import db_manager
    admin_user = await db_manager.users.find_one({"role": "admin"})
    if not admin_user:
        raise HTTPException(
            status_code=500, 
            detail="System configuration error. No admin user found."
        )
    
    admin_settings = await get_user_settings(str(admin_user["_id"]))
    if not admin_settings:
        raise HTTPException(
            status_code=403, 
            detail="API keys not configured. Please contact the administrator."
        )
    
    # Validate file types
    for file in [file1, file2]:
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type for DSCR comparison: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Only Excel files (.xlsx, .xls) are supported. Got: {file.filename}"
            )

    # Generate session ID
    session_id = str(uuid.uuid4())
    logger.info(f"DSCR Template comparison session: {session_id}")

    # Save Excel files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp1:
        content1 = await file1.read()
        tmp1.write(content1)
        file1_path = tmp1.name
        logger.info(f"File 1 saved: {len(content1) / 1024:.2f} KB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp2:
        content2 = await file2.read()
        tmp2.write(content2)
        file2_path = tmp2.name
        logger.info(f"File 2 saved: {len(content2) / 1024:.2f} KB")

    # Get current user's info for history tracking
    current_user = await db_manager.users.find_one({"_id": ObjectId(user_id)})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Initialize progress
    from utils.progress import update_progress
    update_progress(session_id, 0, "Starting DSCR template comparison...")
    
    # Start background processing with DSCR template processor
    background_tasks.add_task(
        process_dscr_template_comparison,
        session_id=session_id,
        file1_path=file1_path,
        file2_path=file2_path,
        file1_name=file1.filename,
        file2_name=file2.filename,
        user_settings=admin_settings,
        model_provider=model_provider,
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=user_id,
        username=current_user.get("email", "Unknown"),
    )
    
    return CompareResponse(
        status="processing",
        message="DSCR template comparison started",
        session_id=session_id
    )

'''

# Read the file
routes_file = r'c:\Users\LDNA40022\Lokesh\GuidelineIQ\backend\compare\routes.py'
with open(routes_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with @router.post("/from-db"
insert_index = None
for i, line in enumerate(lines):
    if '@router.post("/from-db"' in line:
        insert_index = i
        break

if insert_index is None:
    print("ERROR: Could not find @router.post('/from-db' line")
    exit(1)

# Insert the new route before the from-db route  
lines.insert(insert_index, NEW_ROUTE + '\n')

# Write back
with open(routes_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"SUCCESS: Successfully inserted DSCR template route at line {insert_index}")
print(f"   Total lines in file: {len(lines)}")

