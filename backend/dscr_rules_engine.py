import csv
import sys
from dataclasses import dataclass
from typing import List, Optional

# ==========================================
# 1. Authoritative Constants (Variance Categories)
# ==========================================

class VarianceCategory:
    ELIGIBLE_TRANSACTIONS = "Eligible Transactions"
    CREDIT_HOUSING = "Credit / Housing"
    BORROWER_ELIGIBILITY = "Borrower Eligibility"
    BORROWERS_INELIGIBLE = "Borrowers – Ineligible"
    ENTITY_VESTING = "Entity Vesting"
    COLLATERAL = "Collateral"
    CONDOS_PROPERTY_TYPE = "Condos / Property Type"
    ASSETS = "Assets"
    INCOME = "Income"
    DOCUMENTATION = "Documentation"
    APPRAISAL = "Appraisal"
    ESCROWS_INSURANCE = "Escrows / Insurance"
    TITLE_LEGAL = "Title / Legal"
    LOAN_STRUCTURE = "Loan Structure"
    OTHER_PROGRAM_RESTRICTIONS = "Other Program Restrictions"

    @classmethod
    def all(cls):
        return [
            cls.ELIGIBLE_TRANSACTIONS, cls.CREDIT_HOUSING, cls.BORROWER_ELIGIBILITY,
            cls.BORROWERS_INELIGIBLE, cls.ENTITY_VESTING, cls.COLLATERAL,
            cls.CONDOS_PROPERTY_TYPE, cls.ASSETS, cls.INCOME,
            cls.DOCUMENTATION, cls.APPRAISAL, cls.ESCROWS_INSURANCE,
            cls.TITLE_LEGAL, cls.LOAN_STRUCTURE, cls.OTHER_PROGRAM_RESTRICTIONS
        ]

# ==========================================
# 2. Authoritative Constants (Sub-Categories)
# ==========================================

class SubCategory:
    # Eligible Transactions
    PURCHASE = "Purchase"
    RATE_TERM_REFINANCE = "Rate & Term Refinance"
    CASH_OUT_REFINANCE = "Cash-Out Refinance"
    DELAYED_FINANCING = "Delayed Financing"
    BUSINESS_PURPOSE_LOANS = "Business Purpose Loans"

    # Credit / Housing
    CREDIT_SCORE_REQUIREMENTS = "Credit Score Requirements"
    CREDIT_RESCORE = "Credit Rescore"
    CREDIT_REPORT = "Credit Report"
    CREDIT_HOUSING_EVENT_SEASONING = "Credit/Housing Event Seasoning"
    COLLECTIONS_CHARGE_OFFS_JUDGMENTS = "Collections / Charge-Offs / Judgments"

    # Borrower Eligibility
    BORROWER_ELIGIBILITY = "Borrower Eligibility"
    BORROWER_EXPERIENCED = "Borrower – Experienced"
    BORROWER_DACA_ITIN = "Borrower – DACA / ITIN"

    # Borrowers – Ineligible
    INELIGIBLE_BORROWER_TYPES = "Ineligible Borrower Types"
    RESTRICTED_OWNERSHIP_STRUCTURES = "Restricted Ownership Structures"

    # Entity Vesting
    ENTITY_VESTING_SIGNATURE_REQUIREMENTS = "Entity Vesting – Signature Requirements"
    CONTINUITY_OF_OBLIGATION_OWNERSHIP_SEASONING = "Continuity of Obligation / Ownership Seasoning"

    # Collateral
    PROPERTY_ACREAGE_LAND_VALUE = "Property – Acreage and Land Value"
    DECLINING_MARKETS = "Declining Markets"
    AGE_OF_LOAN_DOCUMENTATION = "Age of Loan Documentation"

    # Condos / Property Type
    CONDO_WARRANTABLE_ESTABLISHED = "Condo – Warrantable / Established"
    CONDO_LIMITED_REVIEW = "Condo – Limited Review"
    CONDO_NON_WARRANTABLE = "Condo – Non-Warrantable"
    CONDO_IN_NEED_OF_CRITICAL_REPAIR = "Condo in Need of Critical Repair"
    CONDOTELS = "Condotels"
    NON_OWNER_OCCUPIED_PROPERTIES = "Non-Owner Occupied Properties"
    ACCESSORY_DWELLING_UNITS_ADU = "Accessory Dwelling Units (ADU)"

    # Assets
    ASSETS_ELIGIBILITY_SOURCING_VERIFICATION = "Assets – Eligibility, Sourcing & Verification"
    ASSETS_BUSINESS_ASSETS = "Assets – Business Assets"
    ASSETS_FOREIGN_ASSETS = "Assets – Foreign Assets"
    ASSETS_INELIGIBLE_SOURCES = "Assets – Ineligible Sources"

    # Income
    DSCR_RATIO_REQUIREMENTS = "DSCR Ratio Requirements"
    RENTAL_INCOME_ANALYSIS = "Rental Income Analysis"

    # Documentation
    DOCUMENTATION_REQUIREMENTS = "Documentation Requirements"
    TITLE_REQUIREMENTS = "Title Requirements"

    # Appraisal
    APPRAISAL_REQUIREMENTS = "Appraisal Requirements"
    # Note: Escrow Holdbacks is listed in Authoritative Sub-Categories under Appraisal AND Loan Structure in prompt.
    # Will map contextually.

    # Escrows / Insurance
    ESCROW_IMPOUNDS = "Escrow Impounds"
    HPML = "HPML"
    FLOOD_INSURANCE = "Flood Insurance"
    AUTOMATIC_PAYMENT_AUTHORIZATION_ACH = "Automatic Payment Authorization (ACH)"

    # Loan Structure
    TWO_ONE_BUYDOWN = "2-1 Buydown"
    CASH_OUT_LIMITS = "Cash-Out Limits"
    ESCROW_HOLDBACKS = "Escrow Holdbacks"

    # Other Program Restrictions
    FOREIGN_NATIONAL_RESTRICTIONS = "Foreign National Restrictions"
    PROGRAM_OVERLAYS = "Program Overlays"


# ==========================================
# 3. Data Models
# ==========================================

@dataclass
class DSCRRule:
    dscr_parameter: str
    variance_category: str
    sub_categories: List[str]
    policy_type: str  # "Hard" or "Soft"
    notes: Optional[str] = None

    def to_dict(self):
        # Flatten for CSV if single sub-category, or handle multiple?
        # Prompt says: "Output Structure... equivalent to DSCR 1-4 Sheet".
        # Prompt says "sub_category_or_overlay" is a field.
        # If multiple sub-categories exist for a parameter, we might need to join them or create multiple rows.
        # Prompt says: "Each DSCR Parameter must map to exactly one Variance Category and one or more Sub-Categories".
        # Usually spread sheets imply comma separated or distinct rows.
        # I will join with "; " for safety in this strict format unless otherwise specified.
        return {
            "dscr_parameter": self.dscr_parameter,
            "variance_category": self.variance_category,
            "sub_category_or_overlay": "; ".join(self.sub_categories),
            "policy_type": self.policy_type,
            "notes": self.notes
        }

# ==========================================
# 4. Rules & Mappings
# ==========================================

def get_dscr_rules() -> List[DSCRRule]:
    """
    Constructs the authoritative list of DSCR rules.
    Mappings are hardcoded based on the prompt's requirements.
    """
    rules = [
        # --- Loan Structure ---
        DSCRRule(
            dscr_parameter="2-1 Buydown",
            variance_category=VarianceCategory.LOAN_STRUCTURE,
            sub_categories=[SubCategory.TWO_ONE_BUYDOWN],
            policy_type="Soft",
            notes="Temporary interest rate buydown allowed per guidelines."
        ),
        
        # --- Condos / Property Type ---
        DSCRRule(
            dscr_parameter="Accessory Dwelling Units",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.ACCESSORY_DWELLING_UNITS_ADU],
            policy_type="Soft",
            notes="ADU properties must meet specific appraisal requirements."
        ),

        # --- Collateral ---
        DSCRRule(
            dscr_parameter="Property – Acreage and Land Value",
            variance_category=VarianceCategory.COLLATERAL,
            sub_categories=[SubCategory.PROPERTY_ACREAGE_LAND_VALUE],
            policy_type="Hard",
            notes="Max acreage limits apply."
        ),
        DSCRRule(
            dscr_parameter="Age of Loan Documentation",
            variance_category=VarianceCategory.COLLATERAL,
            sub_categories=[SubCategory.AGE_OF_LOAN_DOCUMENTATION],
            policy_type="Hard",
            notes="Documents must be within valid window (e.g. 90-120 days)."
        ),

        # --- Appraisal ---
        DSCRRule(
            dscr_parameter="Appraisal Requirements",
            variance_category=VarianceCategory.APPRAISAL,
            sub_categories=[SubCategory.APPRAISAL_REQUIREMENTS],
            policy_type="Hard",
            notes="Full appraisal required. CDA or Field Review may apply."
        ),

        # --- Assets ---
        DSCRRule(
            dscr_parameter="Assets – Business Assets",
            variance_category=VarianceCategory.ASSETS,
            sub_categories=[SubCategory.ASSETS_BUSINESS_ASSETS],
            policy_type="Soft",
            notes="Verification of business liquidity required."
        ),
        DSCRRule(
            dscr_parameter="Assets – Eligibility, Sourcing & Verification",
            variance_category=VarianceCategory.ASSETS,
            sub_categories=[SubCategory.ASSETS_ELIGIBILITY_SOURCING_VERIFICATION],
            policy_type="Hard",
            notes="Large deposits must be sourced."
        ),
        DSCRRule(
            dscr_parameter="Assets – Foreign Assets",
            variance_category=VarianceCategory.ASSETS,
            sub_categories=[SubCategory.ASSETS_FOREIGN_ASSETS],
            policy_type="Hard",
            notes="Must be moved to US institution prior to closing."
        ),
        DSCRRule(
            dscr_parameter="Assets – Ineligible Sources",
            variance_category=VarianceCategory.ASSETS,
            sub_categories=[SubCategory.ASSETS_INELIGIBLE_SOURCES],
            policy_type="Hard",
            notes="Crypto, cash on hand, unsupported gifts are ineligible."
        ),

        # --- Escrows / Insurance ---
        DSCRRule(
            dscr_parameter="Automatic Payment Authorization (ACH)",
            variance_category=VarianceCategory.ESCROWS_INSURANCE,
            sub_categories=[SubCategory.AUTOMATIC_PAYMENT_AUTHORIZATION_ACH],
            policy_type="Soft",
            notes="Required for specific program benefits."
        ),

        # --- Borrower Eligibility ---
        DSCRRule(
            dscr_parameter="Borrower Eligibility",
            variance_category=VarianceCategory.BORROWER_ELIGIBILITY,
            sub_categories=[SubCategory.BORROWER_ELIGIBILITY],
            policy_type="Hard",
            notes="US Citizen, Permanent Resident, Non-Permanent Resident."
        ),
        DSCRRule(
            dscr_parameter="Borrowers – Ineligible",
            variance_category=VarianceCategory.BORROWERS_INELIGIBLE,
            sub_categories=[SubCategory.INELIGIBLE_BORROWER_TYPES],
            policy_type="Hard",
            notes="Diplomatic immunity, inter-vivos revocable trusts without specific attributes."
        ),

        # --- Eligible Transactions ---
        DSCRRule(
            dscr_parameter="Business Purpose Loans",
            variance_category=VarianceCategory.ELIGIBLE_TRANSACTIONS,
            sub_categories=[SubCategory.BUSINESS_PURPOSE_LOANS],
            policy_type="Hard",
            notes="Loan must be for business purpose."
        ),
        DSCRRule(
            dscr_parameter="Cash-Out",
            variance_category=VarianceCategory.ELIGIBLE_TRANSACTIONS,
            sub_categories=[SubCategory.CASH_OUT_REFINANCE],
            policy_type="Hard",
            notes="Cash-out max LTV limits apply."
        ),
        DSCRRule(
            dscr_parameter="Cash-Out Refinance Seasoning & Requirements",
            variance_category=VarianceCategory.ELIGIBLE_TRANSACTIONS,
            sub_categories=[SubCategory.CASH_OUT_REFINANCE], # Mapping to Cash-Out Refinance sub-cat
            policy_type="Hard",
            notes="12 months seasoning typically required."
        ),

        # --- Credit / Housing ---
        DSCRRule(
            dscr_parameter="Collections, Charge-Offs and Judgments",
            variance_category=VarianceCategory.CREDIT_HOUSING,
            sub_categories=[SubCategory.COLLECTIONS_CHARGE_OFFS_JUDGMENTS],
            policy_type="Hard",
            notes="Must be paid in full or meet repayment plan criteria."
        ),

        # --- Condos / Property Type ---
        DSCRRule(
            dscr_parameter="Condo – Warrantable / Established Condos",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.CONDO_WARRANTABLE_ESTABLISHED],
            policy_type="Hard",
            notes="Standard agency warrantable criteria."
        ),
        DSCRRule(
            dscr_parameter="Condo – Limited Review",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.CONDO_LIMITED_REVIEW],
            policy_type="Hard",
            notes="LTV and occupancy restrictions apply for limited review."
        ),
        DSCRRule(
            dscr_parameter="Condo – Non-Warrantable",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.CONDO_NON_WARRANTABLE],
            policy_type="Hard",
            notes="Projects with specific non-warrantable features."
        ),
        DSCRRule(
            dscr_parameter="Condo in Need of Critical Repair / Deferred Maintenance",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.CONDO_IN_NEED_OF_CRITICAL_REPAIR],
            policy_type="Hard",
            notes="Ineligible if structural integrity is compromised."
        ),
        
        # Note: 'Condo Insurance Requirements' wasn't an explicit sub-category in the prompt, 
        # but is a parameter. Mapping to relevant category.
        DSCRRule(
            dscr_parameter="Condo Insurance Requirements",
            variance_category=VarianceCategory.ESCROWS_INSURANCE, # Logical mapping
            sub_categories=[SubCategory.ESCROW_IMPOUNDS], # Closest fit or new overlay implies Association HO6 etc.
            # However, strict adherence effectively means mapping to existing sub-cats.
            # Let's map to "Escrow Impounds" or "Appraisal Requirements"?
            # Prompt Sub-Categories under Escrows/Insurance: Escrow Impounds, HPML, Flood Insurance, ACH.
            # Best fit: Escrow Impounds or implicitly covered. Let's use Escrow Impounds as grouping for Insurance.
            policy_type="Hard",
            notes="HO6 walls-in coverage required."
        ),

        DSCRRule(
            dscr_parameter="Condotels",
            variance_category=VarianceCategory.CONDOS_PROPERTY_TYPE,
            sub_categories=[SubCategory.CONDOTELS],
            policy_type="Hard",
            notes="Condo-hotels eligible under specific LTV caps."
        ),

        # --- Entity Vesting ---
        DSCRRule(
            dscr_parameter="Continuity of Obligation / Ownership Seasoning",
            variance_category=VarianceCategory.ENTITY_VESTING,
            sub_categories=[SubCategory.CONTINUITY_OF_OBLIGATION_OWNERSHIP_SEASONING],
            policy_type="Hard",
            notes="Must establish ownership history."
        ),

        # --- Credit / Housing ---
        DSCRRule(
            dscr_parameter="Credit Report",
            variance_category=VarianceCategory.CREDIT_HOUSING,
            sub_categories=[SubCategory.CREDIT_REPORT],
            policy_type="Hard",
            notes="Tri-merge report required."
        ),
        DSCRRule(
            dscr_parameter="Credit Rescore",
            variance_category=VarianceCategory.CREDIT_HOUSING,
            sub_categories=[SubCategory.CREDIT_RESCORE],
            policy_type="Soft",
            notes="Rapid rescore permitted."
        ),
        DSCRRule(
            dscr_parameter="Credit Score Requirements",
            variance_category=VarianceCategory.CREDIT_HOUSING,
            sub_categories=[SubCategory.CREDIT_SCORE_REQUIREMENTS],
            policy_type="Hard",
            notes="Min FICO 620 typically."
        ),
        DSCRRule(
            dscr_parameter="Credit/Housing Event Seasoning",
            variance_category=VarianceCategory.CREDIT_HOUSING,
            sub_categories=[SubCategory.CREDIT_HOUSING_EVENT_SEASONING],
            policy_type="Hard",
            notes="BK/Foreclosure seasoning periods."
        ),

        # --- Borrower Eligibility ---
        DSCRRule(
            dscr_parameter="Borrower – DACA / ITIN",
            variance_category=VarianceCategory.BORROWER_ELIGIBILITY,
            sub_categories=[SubCategory.BORROWER_DACA_ITIN],
            policy_type="Hard",
            notes="Specific LTV cuts for ITIN borrowers."
        ),
        
        # --- Collateral ---
        DSCRRule(
            dscr_parameter="Declining Markets",
            variance_category=VarianceCategory.COLLATERAL,
            sub_categories=[SubCategory.DECLINING_MARKETS],
            policy_type="Hard",
            notes="LTV reduction required for declining markets."
        ),

        # --- Eligible Transactions ---
        DSCRRule(
            dscr_parameter="Delayed Financing",
            variance_category=VarianceCategory.ELIGIBLE_TRANSACTIONS,
            sub_categories=[SubCategory.DELAYED_FINANCING],
            policy_type="Hard",
            notes="Exception to cash-out seasoning for cash buyers."
        ),

        # --- Income ---
        DSCRRule(
            dscr_parameter="DSCR Ratio Requirements",
            variance_category=VarianceCategory.INCOME,
            sub_categories=[SubCategory.DSCR_RATIO_REQUIREMENTS],
            policy_type="Hard",
            notes="Ratio >= 1.00 usually required, <1.00 exceptions exist."
        ),

        # --- Entity Vesting ---
        DSCRRule(
            dscr_parameter="Entity Vesting – Signature Requirements",
            variance_category=VarianceCategory.ENTITY_VESTING,
            sub_categories=[SubCategory.ENTITY_VESTING_SIGNATURE_REQUIREMENTS],
            policy_type="Hard",
            notes="Personal Guarantee required for entity borrowers."
        ),

        # --- Loan Structure OR Appraisal? ---
        # Prompt lists "Escrow Holdbacks" under both Appraisal and Loan Structure.
        # Parameter is "Escrow Holdbacks". Let's map to Loan Structure as it affects structure.
        DSCRRule(
            dscr_parameter="Escrow Holdbacks",
            variance_category=VarianceCategory.LOAN_STRUCTURE,
            sub_categories=[SubCategory.ESCROW_HOLDBACKS],
            policy_type="Soft",
            notes="Allowed for weather-related repairs."
        ),

        # --- Escrows / Insurance ---
        DSCRRule(
            dscr_parameter="Escrow Impounds / HPML / Flood Insurance",
            variance_category=VarianceCategory.ESCROWS_INSURANCE,
            sub_categories=[SubCategory.ESCROW_IMPOUNDS, SubCategory.HPML, SubCategory.FLOOD_INSURANCE],
            policy_type="Hard",
            notes="Impounds required for HPML and Flood zones."
        ),

        # --- Borrower Eligibility ---
        DSCRRule(
            dscr_parameter="Borrower – Experienced",
            variance_category=VarianceCategory.BORROWER_ELIGIBILITY,
            sub_categories=[SubCategory.BORROWER_EXPERIENCED],
            policy_type="Soft",
            notes="First time investor restrictions may apply."
        )
    ]
    return rules

# ==========================================
# 5. Output Logic
# ==========================================

def generate_csv_output(rules: List[DSCRRule], output_file: str = r"C:\Users\LDNA40022\Lokesh\GuidelineIQ\dscr_1_4_output.csv"):
    fieldnames = ["dscr_parameter", "variance_category", "sub_category_or_overlay", "policy_type", "notes"]
    
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rule in rules:
                writer.writerow(rule.to_dict())
        print(f"Successfully generated {output_file} with {len(rules)} rules.")
    except Exception as e:
        print(f"Error generating CSV: {e}", file=sys.stderr)

if __name__ == "__main__":
    rules = get_dscr_rules()
    # verify_integrity(rules) # Could add integrity check here
    generate_csv_output(rules)
    
    # Print logic for immediate verification
    print("-" * 80)
    print(f"{'PARAMETER':<40} | {'VARIANCE CATEGORY':<30} | {'SUB CATEGORY'}")
    print("-" * 80)
    for r in rules[:5]: # Print first 5 for preview
        subs = "; ".join(r.sub_categories)
        print(f"{r.dscr_parameter:<40} | {r.variance_category:<30} | {subs}")
    print("...")
