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
            param = str(row["Parameters"]).strip() if pd.notna(row["Parameters"]) else ""
            cat = str(row["Category"]).strip() if pd.notna(row["Category"]) else "General"
            subcat = str(row["Sub-Categories"]).strip() if pd.notna(row["Sub-Categories"]) else "Feature Eligibility"
            if param:
                # Row 2-138 (Index 0-136) -> Full Doc, Alt Doc
                # Row 139-180 (Index 137-178) -> DSCR
                if i <= 136:
                    g_types = ["Full Doc", "Alt Doc"]
                else:
                    g_types = ["DSCR"]
                    
                result.append({
                    "parameter": param,
                    "category": cat,
                    "subcategory": subcat,
                    "ppe_field": None,
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

        # Ensure Investor "AB" exists
        result = await db.execute(select(Investor).where(Investor.name == "AB"))
        ab_investor = result.scalar_one_or_none()
        if not ab_investor:
            print("👤 Creating Investor: AB")
            ab_investor = Investor(name="AB")
            db.add(ab_investor)
            await db.commit()
            await db.refresh(ab_investor)
        
        ab_id = ab_investor.id

        # Check if already seeded (Skip only if not forced AND some records exist)
        if not force:
            count_res = await db.execute(select(func.count()).select_from(DSCRParameter))
            if count_res.scalar() > 0:
                print("📋 DSCR Parameters already exist. Skipping seed. (Use --force to update)")
                return

        if force:
            print("🗑️ Force flag active. Clearing existing parameters for fresh sync...")
            await db.execute(delete(DSCRParameter))
            await db.commit()

        # Load existing parameters into memory for fast lookup (Index: investor_id, category, parameter)
        print("🔍 Loading existing parameters for sync...")
        existing_res = await db.execute(select(DSCRParameter))
        existing_params = existing_res.scalars().all()
        lookup = {(p.investor_id, p.category, p.parameter): p for p in existing_params}

        new_count = 0
        update_count = 0
        
        # We handle two sets: General (None) and AB Investor
        target_investors = [None, ab_id]
        
        for investor_id in target_investors:
            inv_label = "General" if investor_id is None else "AB"
            print(f"🔄 Syncing parameters for {inv_label}...")
            
            for p_data in unified:
                key = (investor_id, p_data["category"], p_data["parameter"])
                
                if key in lookup:
                    # Check for updates
                    existing = lookup[key]
                    changed = False
                    
                    if existing.subcategory != p_data["subcategory"]:
                        existing.subcategory = p_data["subcategory"]
                        changed = True
                    
                    if existing.guideline_type != p_data["guideline_type"]:
                        existing.guideline_type = p_data["guideline_type"]
                        changed = True
                        
                    if changed:
                        update_count += 1
                else:
                    # Insert new
                    new_param = DSCRParameter(
                        parameter=p_data["parameter"],
                        category=p_data["category"],
                        subcategory=p_data["subcategory"],
                        ppe_field=p_data["ppe_field"],
                        guideline_type=p_data["guideline_type"],
                        investor_id=investor_id
                    )
                    db.add(new_param)
                    new_count += 1

        await db.commit()
        print(f"\n✅ Sync complete:")
        print(f"   - Newly Created: {new_count}")
        print(f"   - Updated: {update_count}")
        
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
