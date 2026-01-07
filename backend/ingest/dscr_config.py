# backend/ingest/dscr_config.py
# DSCR Parameters (Investor / Business Purpose Loans)
# Category = Variance Categories
# Subcategory = Feature Eligibility (constant)
# DSCR_GUIDELINES
DSCR_GUIDELINES = [
    # ---------------- Eligible Transactions ----------------
    {"parameter": "2-1 Buydown", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Purchase", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Rate & Term Refinance", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Cash-Out Refinance", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Delayed Financing", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Business Purpose Loans", "category": "Eligible Transactions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Credit / Housing ----------------   
    {"parameter": "Credit Score Requirements", "category": "Credit / Housing", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Credit Rescore", "category": "Credit / Housing", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Credit Report", "category": "Credit / Housing", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Credit/Housing Event Seasoning", "category": "Credit / Housing", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Collections / Charge-Offs / Judgments", "category": "Credit / Housing", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},

    # ---------------- Borrower Eligibility ----------------
    {"parameter": "Borrower Eligibility", "category": "Borrower Eligibility", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Borrower – Experienced", "category": "Borrower Eligibility", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Borrower – DACA / ITIN", "category": "Borrower Eligibility", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},

    # ---------------- Borrowers – Ineligible ----------------
    {"parameter": "Ineligible Borrower Types", "category": "Borrowers – Ineligible", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Restricted Ownership Structures", "category": "Borrowers – Ineligible", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Entity Vesting ----------------
    {"parameter": "Entity Vesting - Signature Requirements", "category": "Entity Vesting", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Vesting & Ownership", "category": "Entity Vesting", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Collateral ----------------
    {"parameter": "Accessory Dwelling Units", "category": "Collateral", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Property - Acreage and Land Value", "category": "Collateral", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Declining Markets", "category": "Collateral", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Condos / Property Type ----------------
    {"parameter": "Condo - Warrantable / Established Condos", "category": "Condos / Property Type", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Condo - Limited Review", "category": "Condos / Property Type", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Condos Non-Warrantable", "category": "Condos / Property Type", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Condotels", "category": "Condos / Property Type", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Assets ----------------
    {"parameter": "Assets - Business Assets", "category": "Assets", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Assets - Eligibility, Sourcing & Verification", "category": "Assets", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Assets - Foreign Assets", "category": "Assets", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Assets - Ineligible Sources", "category": "Assets", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Reserves", "category": "Assets", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Income ----------------
    {"parameter": "DSCR Ratio Requirements", "category": "Income", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Gross Rent Requirements", "category": "Income", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Interest-Only", "category": "Income", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Underwriting Method", "category": "Income", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},

    # ---------------- Documentation ----------------
    {"parameter": "Age of Loan Documentation", "category": "Documentation", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Appraisal Requirements", "category": "Documentation", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Escrows / Insurance ----------------
    {"parameter": "Escrow Holdbacks", "category": "Escrows / Insurance", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Escrow Impounds / Flood Insurance", "category": "Escrows / Insurance", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},

    # ---------------- Title / Legal ----------------
    {"parameter": "Title Insurance Requirements", "category": "Title / Legal", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Power of Attorney", "category": "Title / Legal", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},

    # ---------------- Loan Structure ----------------
    {"parameter": "Loan Amounts", "category": "Loan Structure", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "LTV", "category": "Loan Structure", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Prepayment Penalties", "category": "Loan Structure", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},
    {"parameter": "Interest Credit", "category": "Loan Structure", "subcategory": "Feature Eligibility", "ppe_field": "Soft"},

    # ---------------- Other Program Restrictions ----------------
    {"parameter": "State Restrictions", "category": "Other Program Restrictions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
    {"parameter": "Multiple Financed Properties", "category": "Other Program Restrictions", "subcategory": "Feature Eligibility", "ppe_field": "Hard"},
]