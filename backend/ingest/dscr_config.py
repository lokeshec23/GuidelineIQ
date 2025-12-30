
# backend/ingest/dscr_config.py

# Consolidated Configuration with Hardcoded Categories
DSCR_GUIDELINES = [
    # --- Eligibility ---
    {"parameter": "2-1 Buydown", "category": "Eligibility", "subcategory": "Buydown", "ppe_field": "Text"},
    {"parameter": "Accessory Dwelling Units", "category": "Property Eligibility", "subcategory": "ADU", "ppe_field": "Boolean"},
    {"parameter": "Property - Acreage and Land Value", "category": "Property Eligibility", "subcategory": "Acreage", "ppe_field": "Number"},
    {"parameter": "Age of Loan Documentation", "category": "Documentation", "subcategory": "Age of Docs", "ppe_field": "Number", "aliases": ["AGE OF DOCUMENT REQUIREMENTS"]},
    
    # --- Assets ---
    {"parameter": "Assets - Business Assets", "category": "Assets", "subcategory": "Business Assets", "ppe_field": "Boolean"},
    {"parameter": "Assets - Eligibility, Sourcing & Verification", "category": "Assets", "subcategory": "Sourcing", "ppe_field": "Text"},
    {"parameter": "Assets - Foreign Assets", "category": "Assets", "subcategory": "Foreign Assets", "ppe_field": "Boolean"},
    {"parameter": "Assets - Ineligible Sources", "category": "Assets", "subcategory": "Ineligible", "ppe_field": "Text"},
    {"parameter": "Reserves", "category": "Assets", "subcategory": "Reserves", "ppe_field": "Number"},
    {"parameter": "Gift Funds", "category": "Assets", "subcategory": "Gift Funds", "ppe_field": "Boolean"},
    
    # --- Borrower ---
    {"parameter": "Borrower Eligibility", "category": "Borrower Eligibility", "subcategory": "General", "ppe_field": "Text"},
    {"parameter": "Borrowers - Ineligible", "category": "Borrower Eligibility", "subcategory": "Ineligible", "ppe_field": "Text"},
    {"parameter": "Borrower - DACA / ITIN", "category": "Borrower Eligibility", "subcategory": "Residency", "ppe_field": "Boolean"},
    {"parameter": "Borrower - Non-Permanent Resident Alien", "category": "Borrower Eligibility", "subcategory": "Residency", "ppe_field": "Boolean"},
    {"parameter": "Permanent Resident Aliens", "category": "Borrower Eligibility", "subcategory": "Residency", "ppe_field": "Boolean"},
    {"parameter": "Borrower - Experienced Investor", "category": "Borrower Eligibility", "subcategory": "Experience", "ppe_field": "Boolean"},
    {"parameter": "Borrower First Time Investors", "category": "Borrower Eligibility", "subcategory": "Experience", "ppe_field": "Boolean"},
    {"parameter": "Borrower - First-Time Home Buyers", "category": "Borrower Eligibility", "subcategory": "FTHB", "ppe_field": "Boolean"},
    {"parameter": "Entity Vesting - Signature Requirements", "category": "Borrower Eligibility", "subcategory": "Vesting", "ppe_field": "Text"},
    {"parameter": "Grantor Documentation for Entity Vesting", "category": "Borrower Eligibility", "subcategory": "Vesting", "ppe_field": "Text"},
    {"parameter": "Vesting & Ownership", "category": "Borrower Eligibility", "subcategory": "Vesting", "ppe_field": "Text"},
    {"parameter": "Power of Attorney", "category": "Borrower Eligibility", "subcategory": "POA", "ppe_field": "Boolean"},
    {"parameter": "Personal Guaranty", "category": "Borrower Eligibility", "subcategory": "Guaranty", "ppe_field": "Boolean"},
    {"parameter": "Continuity of Obligation / Ownership Seasoning", "category": "Borrower Eligibility", "subcategory": "Seasoning", "ppe_field": "Text"},

    # --- Credit ---
    {"parameter": "Credit Report", "category": "Credit", "subcategory": "Report", "ppe_field": "Text"},
    {"parameter": "Credit Rescore", "category": "Credit", "subcategory": "Score", "ppe_field": "Boolean"},
    {"parameter": "Credit Score Requirements", "category": "Credit", "subcategory": "Score", "ppe_field": "Number"},
    {"parameter": "Credit/Housing Event Seasoning", "category": "Credit", "subcategory": "Derogatory", "ppe_field": "Number"},
    {"parameter": "Collections, Charge-Offs and Judgments", "category": "Credit", "subcategory": "Derogatory", "ppe_field": "Text"},
    {"parameter": "Forbearance / Mortgage Modification / Deferment", "category": "Credit", "subcategory": "Derogatory", "ppe_field": "Text"},
    {"parameter": "Tradelines Requirements", "category": "Credit", "subcategory": "Tradelines", "ppe_field": "Number"},

    # --- Property ---
    {"parameter": "Appraisal Requirements", "category": "Property Eligibility", "subcategory": "Appraisal", "ppe_field": "Text"},
    {"parameter": "Condo - Warrantable / Established Condos", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Boolean"},
    {"parameter": "Condo - Warrantable / Limited Review", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Boolean"},
    {"parameter": "Condo in Need of Critical Repair / Deferred Maintenance", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Boolean"},
    {"parameter": "Condo Insurance Requirements", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Text"},
    {"parameter": "Condos Non-Warrantable", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Boolean"},
    {"parameter": "Condotels", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Boolean"},
    {"parameter": "Maximum Concentration Exposure (Condo Projects)", "category": "Property Eligibility", "subcategory": "Condo", "ppe_field": "Number"},
    {"parameter": "Declining Markets", "category": "Property Eligibility", "subcategory": "Market", "ppe_field": "Boolean"},
    {"parameter": "Flip Transactions", "category": "Property Eligibility", "subcategory": "Flip", "ppe_field": "Boolean"},
    {"parameter": "Properties Listed for Sale", "category": "Property Eligibility", "subcategory": "Listing", "ppe_field": "Boolean"},
    {"parameter": "Property Types - Eligible", "category": "Property Eligibility", "subcategory": "Types", "ppe_field": "Text"},
    {"parameter": "Property Types - Ineligible", "category": "Property Eligibility", "subcategory": "Types", "ppe_field": "Text"},
    {"parameter": "Rural Properties", "category": "Property Eligibility", "subcategory": "Rural", "ppe_field": "Boolean"},
    {"parameter": "Short-Term Rentals", "category": "Property Eligibility", "subcategory": "Rental", "ppe_field": "Boolean"},
    {"parameter": "Vacant / Unleased Properties", "category": "Property Eligibility", "subcategory": "Vacancy", "ppe_field": "Boolean"},
    {"parameter": "Inherited Properties", "category": "Property Eligibility", "subcategory": "Inherited", "ppe_field": "Boolean"},

    # --- Transaction ---
    {"parameter": "Business Purpose Loans", "category": "Transaction", "subcategory": "Purpose", "ppe_field": "Boolean"},
    {"parameter": "Cash-Out", "category": "Transaction", "subcategory": "Refinance", "ppe_field": "Boolean"},
    {"parameter": "Cash-Out Refinance Seasoning & Requirements", "category": "Transaction", "subcategory": "Refinance", "ppe_field": "Text"},
    {"parameter": "Rate/Term Refinance", "category": "Transaction", "subcategory": "Refinance", "ppe_field": "Text"},
    {"parameter": "Rate/Term Refinance - Other", "category": "Transaction", "subcategory": "Refinance", "ppe_field": "Text"},
    {"parameter": "Delayed Financing", "category": "Transaction", "subcategory": "Financing", "ppe_field": "Boolean"},
    {"parameter": "Loan Purpose", "category": "Transaction", "subcategory": "Purpose", "ppe_field": "Text"},
    {"parameter": "Multiple Financed Properties", "category": "Transaction", "subcategory": "Exposure", "ppe_field": "Number"},
    {"parameter": "Maximum Exposure", "category": "Transaction", "subcategory": "Exposure", "ppe_field": "Number"},

    # --- Income/DSCR ---
    {"parameter": "DSCR Ratio Requirements", "category": "Income", "subcategory": "DSCR", "ppe_field": "Number"},
    {"parameter": "Gross Rent Requirements", "category": "Income", "subcategory": "Rents", "ppe_field": "Number"},
    {"parameter": "Rents Loss Insurance", "category": "Income", "subcategory": "Insurance", "ppe_field": "Number"},
    {"parameter": "Interest-Only", "category": "Income", "subcategory": "IO", "ppe_field": "Boolean"},
    {"parameter": "Underwriting Method", "category": "Income", "subcategory": "UW", "ppe_field": "Text"},
    
    # --- Housing ---
    {"parameter": "Housing / Rental History", "category": "History", "subcategory": "Housing", "ppe_field": "Text"},
    {"parameter": "Housing History - Incomplete and Rent Free", "category": "History", "subcategory": "Housing", "ppe_field": "Text"},
    {"parameter": "Housing History Verification", "category": "History", "subcategory": "Housing", "ppe_field": "Text"},
    {"parameter": "Housing Payment History Documentation Requirements", "category": "History", "subcategory": "Housing", "ppe_field": "Text"},

    # --- Other ---
    {"parameter": "Automatic Payment Authorization (ACH)", "category": "Other", "subcategory": "Payment", "ppe_field": "Boolean"},
    {"parameter": "Escrow Holdbacks", "category": "Other", "subcategory": "Escrow", "ppe_field": "Boolean"},
    {"parameter": "Escrow Impounds / HPML / Flood Insurance", "category": "Other", "subcategory": "Escrow", "ppe_field": "Text"},
    {"parameter": "Interest Credit", "category": "Other", "subcategory": "Interest", "ppe_field": "Boolean"},
    {"parameter": "IPCs", "category": "Other", "subcategory": "Contributions", "ppe_field": "Number"},
    {"parameter": "Loan Amounts", "category": "Other", "subcategory": "Limits", "ppe_field": "Number"},
    {"parameter": "LTV", "category": "Other", "subcategory": "Limits", "ppe_field": "Number"},
    {"parameter": "Prepayment Penalties", "category": "Other", "subcategory": "Penalty", "ppe_field": "Text"},
    {"parameter": "Products", "category": "Other", "subcategory": "Product", "ppe_field": "Text"},
    {"parameter": "State Restrictions", "category": "Other", "subcategory": "States", "ppe_field": "Text"},
    {"parameter": "Subordinate Financing - HELOC / Closed End Second Lien", "category": "Other", "subcategory": "Subordinate", "ppe_field": "Boolean"},
    {"parameter": "Title Insurance Requirements", "category": "Other", "subcategory": "Title", "ppe_field": "Text"},
]
