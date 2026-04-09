
import pandas as pd
import os

EXCEL_FILE_PATH = os.path.join(os.getcwd(), 'backend', 'guideline_type_parameters.xlsx')

def check_overlaps():
    df = pd.read_excel(EXCEL_FILE_PATH)
    fa = df[df['Guideline Type'] == 'Full & Alt']
    params = sorted(fa['Parameters'].astype(str).tolist())
    
    print(f"Total Full & Alt data rows in Excel: {len(fa)}")
    print("Checking for potential overlaps/near-duplicates in Full & Alt:")
    
    found = False
    for i in range(len(params)-1):
        p1 = params[i].lower().strip()
        p2 = params[i+1].lower().strip()
        if p1 == p2 or (p1 in p2 and len(p2) - len(p1) < 3) or (p2 in p1 and len(p1) - len(p2) < 3):
            print(f"  - {repr(params[i])} vs {repr(params[i+1])}")
            found = True
            
    if not found:
        print("  No near-duplicates found in Full & Alt.")

    dscr = df[df['Guideline Type'] == 'DSCR']
    params_dscr = sorted(dscr['Parameters'].astype(str).tolist())
    print(f"\nTotal DSCR data rows in Excel: {len(dscr)}")
    print("Checking for potential overlaps/near-duplicates in DSCR:")
    for i in range(len(params_dscr)-1):
        p1 = params_dscr[i].lower().strip()
        p2 = params_dscr[i+1].lower().strip()
        if p1 == p2 or (p1 in p2 and len(p2) - len(p1) < 3) or (p2 in p1 and len(p1) - len(p2) < 3):
            print(f"  - {repr(params_dscr[i])} vs {repr(params_dscr[i+1])}")

if __name__ == "__main__":
    check_overlaps()
