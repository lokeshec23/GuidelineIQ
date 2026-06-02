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

from sqlalchemy import text, inspect, select, func, delete
from sql_database import engine, AsyncSessionLocal
from models.sql_models import DSCRParameter, Investor, GuidelineType, Base

async def seed_guideline_types(db):
    """Seed default guideline types if they don't exist."""
    defaults = [
        {"name": "DSCR", "description": "Debt Service Coverage Ratio", "color": "blue"},
        {"name": "Full Doc", "description": "Full Documentation", "color": "green"},
        {"name": "Alt Doc", "description": "Alternative Documentation", "color": "purple"}
    ]
    
    for item in defaults:
        result = await db.execute(select(GuidelineType).where(GuidelineType.name == item["name"]))
        if not result.scalar_one_or_none():
            print(f"🏷️ Seeding Guideline Type: {item['name']}")
            db.add(GuidelineType(**item))
    
    await db.commit()


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
        for i, row in df.iterrows():
            param = str(row["Parameters"]).strip() if "Parameters" in row and pd.notna(row["Parameters"]) else ""
            cat = str(row["Category"]).strip() if "Category" in row and pd.notna(row["Category"]) else "General"
            subcat = str(row["Sub-Categories"]).strip() if "Sub-Categories" in row and pd.notna(row["Sub-Categories"]) else "Feature Eligibility"
            g_type_val = str(row["Guideline Type"]).strip() if "Guideline Type" in row and pd.notna(row["Guideline Type"]) else ""
            ppe_val = str(row["PPE Field"]).strip() if "PPE Field" in row and pd.notna(row["PPE Field"]) else None
            
            if param:
                g_types = []
                g_type_lower = g_type_val.lower()
                if "full" in g_type_lower or "alt" in g_type_lower:
                    g_types.extend(["Full Doc", "Alt Doc"])
                if "dscr" in g_type_lower:
                    g_types.append("DSCR")
                if not g_types:
                    # Fallback if Guideline Type is empty
                    g_types = ["Full Doc", "Alt Doc", "DSCR"]
                    
                result.append({
                    "parameter": param,
                    "category": cat,
                    "subcategory": subcat,
                    "ppe_field": ppe_val,
                    "guideline_type": g_types
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
    Uses upsert logic with indexes for speed.
    """
    
    # First, ensure column exists
    await add_column_if_not_exists()
    
    unified = build_unified_parameters()
    print(f"\n📋 Unified parameter count from Excel: {len(unified)}")
    
    async with AsyncSessionLocal() as db:
        # Seed Guideline Types first
        await seed_guideline_types(db)

        if not force:
            count_res = await db.execute(select(func.count()).select_from(DSCRParameter).where(DSCRParameter.investor_id == None))
            if count_res.scalar() > 0:
                print("📋 General DSCR Parameters already exist. Skipping seed. (Use --force to wipe and re-seed)")
                return

        print("🗑️ Option A (Clean Slate): Wiping all existing parameters from DB...")
        await db.execute(delete(DSCRParameter))
        await db.commit()

        new_count = 0
        
        print(f"🔄 Syncing General parameters...")
        
        new_params = []
        for p_data in unified:
            new_param = DSCRParameter(
                parameter=p_data["parameter"],
                category=p_data["category"],
                subcategory=p_data["subcategory"],
                ppe_field=p_data["ppe_field"],
                guideline_type=p_data["guideline_type"],
                investor_id=None,
                is_active=True
            )
            new_params.append(new_param)
            new_count += 1
            
        db.add_all(new_params)
        await db.commit()

        print(f"\n✅ Sync complete:")
        print(f"   - Newly Created (General): {new_count}")
        
        # Verify total
        count_res = await db.execute(select(func.count()).select_from(DSCRParameter))
        total = count_res.scalar()
        print(f"📊 Total parameters in DB: {total}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Parameter Seed Script")
    print("  Seeds Full Doc, Alt Doc, and DSCR parameters")
    print("=" * 60)
    
    force_seed = "--force" in sys.argv
    asyncio.run(seed_parameters(force=force_seed))
    print("\n✅ Done!")
