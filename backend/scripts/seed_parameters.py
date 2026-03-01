"""
Seed script to populate the dscr_parameters table with the three parameter lists:
- Full Doc parameters
- Alt Doc parameters
- DSCR parameters

Also adds the guideline_type column if it doesn't exist.

Usage: python scripts/seed_parameters.py
"""
import asyncio
import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from sql_database import engine, AsyncSessionLocal
from models.sql_models import DSCRParameter, Base


# ===================== PARAMETER LISTS =====================

FULL_DOC_PARAMS = [
    "1099", "2-1 Buydown", "4506-C IRS Tax Transcripts",
    "Accessory Dwelling Units - Rental Income", "Age of Loan Documentation",
    "Alimony, Child Support, Obligations (Debt)", "Appraisal Requirements",
    "Asset Depletion/Asset Utilization", "Assets - Foreign Assets",
    "Assets - Ineligible", "Assets Source & Verification", "AUS Underwriting Method",
    "Bank Statements - NSFs", "Bonus Income", "Borrowers - Eligible",
    "Borrowers - Ineligible", "Business Assets",
    "Business Bank Statements & Co-mingled Bank Statements",
    "Business Debt / Debt Paid by Others", "Business Purpose Loans",
    "Cash-Out Limits", "Cash-Out Refinance Seasoning & Requirements",
    "Chain of Title", "Collections, Charge-Offs and Judgments", "Commission",
    "Condo Insurance Requirements", "Condos - Non-Warrantable",
    "Condos - Warrantable", "Condotels", "Continuity of Obligation",
    "Credit / Housing Event Seasoning", "Credit Reports", "Credit Rescore",
    "Credit Score Requirements", "Debt Consolidation", "Declining Income",
    "Declining Markets", "Deferred Maintenance", "Delayed Financing",
    "Departing Residence / Current Residence Pending Sale", "Disaster Policy",
    "Disputed Accounts", "DTI", "Employment by a Relative",
    "Employment Offers or Contracts / Projected Income",
    "Entity Vesting - Grantor Documentation Requirements",
    "Entity Vesting - Signature Requirements", "Escrow Holdbacks",
    "Escrow Impounds / HPML / Flood Insurance", "First Time Homebuyers",
    "Flip Transactions", "Forbearance / Mortgage Modification / Deferment",
    "Foreign Nationals", "Gap Credit Report / Undisclosed Debt",
    "Gaps in Employment", "Gift Funds / Gift of Equity", "HELOC",
    "Housing History - Incomplete and Rent-Free",
    "Housing Payment Verification (VOM/ VOR/ PVOR - Cancelled Checks/ Bank Statements)",
    "Housing/Rental History", "Income - Foreign Income",
    "Income - Ineligible Sources", "Income - Other Sources of Income",
    "Inherited Properties", "Installment debt", "Interest Credit",
    "Interest-Only", "IPCs", "Judgments and Tax Liens",
    "Land Contract / Contract for Deed", "Large Deposits",
    "Lease with Purchase Option", "Leaseholds - Leasehold Condos",
    "Limited Tradeline Requirements", "Loan Amounts", "Loan Purpose",
    "LTV Determination", "LTV/CLTV", "Maximum Exposure",
    "Minimum Square Footage Requirements", "Mixed Use Properties",
    "Multiple Dwellings on one lot", "Multiple Financed Properties",
    "Multiple Parcels", "Non-Arm's Length Transactions",
    "Non-Occupant Co-Borrowers", "Non-Permanent Resident Aliens",
    "Non-Taxable Income", "Non-Traditional Tradeline Requirements (Standard)",
    "Occupancy", "Open 30-Day Charge Accounts",
    "P&L and 2 months Bank Statements",
    "P&L and 2 months Bank Statements - Overlays", "P&L Only",
    "Pension / Retirement Income", "Permanent Resident Aliens",
    "Personal Bank Statements", "Power of Attorney",
    "Prepayment Penalties & Fees", "Principal Curtailment", "Products",
    "Properties Listed for Sale", "Property - Acreage and Land Value",
    "Property - Minimum Square Footage", "Property Insurance",
    "Property Types - Eligible", "Property Types - Ineligible",
    "Qualified Asset from Retirement / Annuity Income",
    "Qualifying Foreign Credit (FN)", "Rate/Term Refinance",
    "Rate/Term Refinance - Others", "Rental Income", "Reserves",
    "Residual Income", "Retirement Assets", "Revolving Debt", "RSU Income",
    "Rural Properties", "Second Home", "Self-Employment History",
    "Self-Employment Income", "Self-Employment Less than 2 years History",
    "Short Term Rentals", "Social Security Income", "State Restrictions",
    "Stocks, Bonds and Mutual Funds / Stock options", "Student Loans",
    "Subordinate / Secondary Financing",
    "Texas Section 50 (a)(6) Equity Cash Out Loans",
    "Title Insurance Requirements", "Tradeline Requirements (Standard)",
    "Trust Assets", "Trust Income", "Vesting and Ownership", "VVOE",
    "Wage Earners / Paystubs", "WVOE Alt Doc",
]

# Alt Doc is identical to Full Doc
ALT_DOC_PARAMS = list(FULL_DOC_PARAMS)

DSCR_PARAMS = [
    "2-1 Buydown", "Accessory Dwelling Units - Rental Income",
    "Age of Loan Documentation", "Appraisal Requirements", "Business Assets",
    "Assets Source & Verification", "Assets - Foreign Assets",
    "Assets - Ineligible", "Automatic Payment Authorization (ACH)",
    "Borrower - Experienced Investor", "Borrower - First-Time Home Buyers",
    "Non-Permanent Resident Aliens", "Borrower Eligibility",
    "Borrower First Time Investors", "Borrower - Ineligible",
    "Business Purpose Loans", "Cash-Out",
    "Cash-Out Refinance Seasoning & Requirements",
    "Collections, Charge-Offs and Judgments", "Condos - Warrantable",
    "Condo - Warrantable / Limited Review",
    "Condo in Need of Critical Repair / Deferred Maintenance",
    "Condo Insurance Requirements", "Condos - Non-Warrantable", "Condotels",
    "Continuity of Obligation / Ownership Seasoning", "Credit Reports",
    "Credit Rescore", "Credit Score Requirements",
    "Credit / Housing Event Seasoning", "Declining Markets",
    "Delayed Financing", "DSCR Ratio Requirements",
    "Entity Vesting - Signature Requirements", "Escrow Holdbacks",
    "Escrow Impounds / HPML / Flood Insurance", "Flip Transactions",
    "Forbearance / Mortgage Modification / Deferment", "Gift Funds",
    "Entity Vesting - Grantor Documentation Requirements",
    "Gross Rent Requirements", "Housing / Rental History",
    "Housing History - Incomplete and Rent Free",
    "Housing History Verification",
    "Housing Payment Verification (VOM/ VOR/ PVOR - Cancelled Checks/ Bank Statements)",
    "Inherited Properties", "Interest Credit", "Interest-Only", "IPCs",
    "Lease and Occupancy Requirements", "Loan Amounts", "Loan Purpose",
    "Long Term Rentals", "LTV",
    "Maximum Concentration Exposure (Condo Projects)", "Maximum Exposure",
    "Multiple Financed Properties", "Permanent Resident Aliens",
    "Personal Guaranty", "Power of Attorney", "Prepayment Penalties",
    "Products", "Properties Listed for Sale",
    "Property - Acreage and Land Value", "Property Types - Eligible",
    "Property Types - Ineligible", "Rate/Term Refinance",
    "Rents Loss Insurance", "Reserves", "Rural Properties",
    "Short-Term Rentals", "State Restrictions",
    "Subordinate Financing - HELOC / Closed End Second Lien",
    "Title Insurance Requirements", "Tradelines Requirements",
    "Underwriting Method", "Vacant / Unleased Properties",
    "Vesting and Ownership",
]


def build_unified_parameters():
    """
    Build a unified list of unique parameters with their guideline_type tags.
    """
    full_doc_set = set(FULL_DOC_PARAMS)
    alt_doc_set = set(ALT_DOC_PARAMS)
    dscr_set = set(DSCR_PARAMS)
    
    all_params = full_doc_set | alt_doc_set | dscr_set
    
    result = []
    for param in sorted(all_params):
        types = []
        if param in full_doc_set:
            types.append("Full Doc")
        if param in alt_doc_set:
            types.append("Alt Doc")
        if param in dscr_set:
            types.append("DSCR")
        

        result.append({
            "parameter": param,
            "category": "General",
            "subcategory": "Feature Eligibility",
            "ppe_field": None,
            "guideline_type": types
        })
    
    return result


async def add_column_if_not_exists():
    """Add guideline_type column if it doesn't exist yet."""
    async with engine.begin() as conn:
        try:
            await conn.execute(text(
                "ALTER TABLE dscr_parameters ADD guideline_type NVARCHAR(MAX) NULL"
            ))
            print("✅ Added guideline_type column to dscr_parameters table")
        except Exception as e:
            if "already" in str(e).lower() or "duplicate" in str(e).lower() or "column names" in str(e).lower():
                print("ℹ️  guideline_type column already exists")
            else:
                print(f"⚠️  Column add attempt: {e}")


async def seed_parameters():
    """Clear existing parameters and seed with the unified list."""
    
    # First, ensure column exists
    await add_column_if_not_exists()
    
    unified = build_unified_parameters()
    print(f"\n📋 Unified parameter list: {len(unified)} unique parameters")
    
    # Count by type
    type_counts = {"Full Doc": 0, "Alt Doc": 0, "DSCR": 0}
    for p in unified:
        for t in p["guideline_type"]:
            type_counts[t] = type_counts.get(t, 0) + 1
    
    for t, c in type_counts.items():
        print(f"  - {t}: {c} parameters")
    
    async with AsyncSessionLocal() as db:
        # Clear existing
        from sqlalchemy import delete
        await db.execute(delete(DSCRParameter))
        await db.commit()
        print("\n🗑️  Cleared existing parameters")
        
        # Insert new
        import json
        for p in unified:
            param = DSCRParameter(
                parameter=p["parameter"],
                category=p["category"],
                subcategory=p["subcategory"],
                ppe_field=p["ppe_field"],
                guideline_type=p["guideline_type"]
            )
            db.add(param)
        
        await db.commit()
        print(f"✅ Seeded {len(unified)} parameters successfully!")
        
        # Verify
        from sqlalchemy import select, func
        count = await db.execute(select(func.count()).select_from(DSCRParameter))
        total = count.scalar()
        print(f"📊 Total parameters in DB: {total}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Parameter Seed Script")
    print("  Seeds Full Doc, Alt Doc, and DSCR parameters")
    print("=" * 60)
    asyncio.run(seed_parameters())
    print("\n✅ Done!")
