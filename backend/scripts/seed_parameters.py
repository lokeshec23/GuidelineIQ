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
import pandas as pd

EXCEL_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guideline_type_parameters.xlsx")

def build_unified_parameters():
    """
    Build a unified list of unique parameters with their guideline_type tags
    by reading from the Excel file and appending the new general parameters.
    """
    result = []
    
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        for _, row in df.iterrows():
            param = str(row["Parameters"]).strip() if pd.notna(row["Parameters"]) else ""
            cat = str(row["Category"]).strip() if pd.notna(row["Category"]) else "General"
            subcat = str(row["Sub-Categories"]).strip() if pd.notna(row["Sub-Categories"]) else "Feature Eligibility"
            if param:
                # Assign all parameters to all program types to ensure visibility
                result.append({
                    "parameter": param,
                    "category": cat,
                    "subcategory": subcat,
                    "ppe_field": None,
                    "guideline_type": ["Full Doc", "Alt Doc", "DSCR"]
                })
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise e
    
    return result


async def add_column_if_not_exists():
    """Add guideline_type and investor_id columns if they don't exist yet."""
    async with engine.begin() as conn:
        try:
            await conn.execute(text(
                "ALTER TABLE dscr_parameters ADD guideline_type NVARCHAR(MAX) NULL"
            ))
            print("✅ Added guideline_type column to dscr_parameters table")
        except Exception as e:
            pass

        try:
            await conn.execute(text(
                "ALTER TABLE dscr_parameters ADD investor_id NVARCHAR(36) NULL"
            ))
            print("✅ Added investor_id column to dscr_parameters table")
        except Exception as e:
            pass


async def seed_parameters(force: bool = False):
    """
    Seed parameters with the unified list.
    If force is False, it will skip if parameters already exist.
    """
    
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
        # Check if already seeded
        if not force:
            from sqlalchemy import select, func
            result = await db.execute(select(func.count()).select_from(DSCRParameter))
            if result.scalar() > 0:
                print("📋 DSCR Parameters already exist in database. Skipping seed.")
                return

        # Clear existing if forced or if we reached here
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
