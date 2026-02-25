import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from compare.dscr_template_processor import detect_parameter_column
from ingest.dscr_config import DSCR_GUIDELINES

def test_detect_parameter_column():
    # Test 1: Exact match with complex header
    data1 = [{"DSCR Parameters\n(Investor / Business Purpose Loans)": "Purchase", "Category": "Test"}]
    col1 = detect_parameter_column(data1, DSCR_GUIDELINES)
    print(f"Test 1 (Complex Header): Detected = {col1}")
    assert col1 == "DSCR Parameters\n(Investor / Business Purpose Loans)"

    # Test 2: Standard name
    data2 = [{"dscr_parameters": "Purchase", "Category": "Test"}]
    col2 = detect_parameter_column(data2, DSCR_GUIDELINES)
    print(f"Test 2 (Standard Name): Detected = {col2}")
    assert col2 == "dscr_parameters"

    # Test 3: Content overlap (no standard header)
    data3 = [{"Some Unknown Header": "Purchase", "Other": "Test"}]
    col3 = detect_parameter_column(data3, DSCR_GUIDELINES)
    print(f"Test 3 (Content Overlap): Detected = {col3}")
    assert col3 == "Some Unknown Header"

    print("All backend column detection tests passed!")

if __name__ == "__main__":
    try:
        test_detect_parameter_column()
    except Exception as e:
        print(f"Tests failed: {e}")
        sys.exit(1)
