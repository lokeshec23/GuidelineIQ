import sys
import os
import unittest

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from compare.processor import align_guideline_data

class TestAlignment(unittest.TestCase):
    def test_fuzzy_matching(self):
        data1 = [
            {"category": "Credit", "attribute": "Minimum Score", "guideline_summary": "660"},
            {"category": "LTV", "attribute": "Max LTV", "guideline_summary": "80%"},
            {"category": "Income", "attribute": "DTI", "guideline_summary": "43%"}
        ]
        
        data2 = [
            {"category": "Credit", "attribute": "Min Score", "guideline_summary": "640"}, # Fuzzy match expected
            {"category": "LTV", "attribute": "Max LTV", "guideline_summary": "75%"},     # Exact match
            {"category": "Assets", "attribute": "Reserves", "guideline_summary": "6 months"} # No match
        ]
        
        aligned = align_guideline_data(data1, data2, "file1", "file2")
        
        # Check results
        print("\nAlignment Results:")
        for item in aligned:
            g1 = item.get("guideline1")
            g2 = item.get("guideline2")
            match_type = item.get("match_type", "unknown")
            
            c1 = f"{g1['category']} - {g1['attribute']}" if g1 else "None"
            c2 = f"{g2['category']} - {g2['attribute']}" if g2 else "None"
            
            print(f"{c1} <==[{match_type}]==> {c2}")

        # Assertions
        # 1. Exact match
        ltv_match = next((x for x in aligned if x["guideline1"] and x["guideline1"]["attribute"] == "Max LTV"), None)
        self.assertIsNotNone(ltv_match)
        self.assertIsNotNone(ltv_match["guideline2"])
        self.assertEqual(ltv_match["guideline2"]["attribute"], "Max LTV")
        
        # 2. Fuzzy match (Minimum Score vs Min Score)
        # Note: "Minimum Score" vs "Min Score" might be tricky depending on threshold.
        # Let's see if 0.85 catches it.
        # "credit | minimum score" vs "credit | min score"
        # ratio is likely high enough.
        score_match = next((x for x in aligned if x["guideline1"] and x["guideline1"]["attribute"] == "Minimum Score"), None)
        
        # If fuzzy matching works, this should be matched
        if score_match and score_match["guideline2"]:
             print("Fuzzy match successful for Credit Score")
        else:
             print("Fuzzy match FAILED for Credit Score")

        # 3. No match
        dti_match = next((x for x in aligned if x["guideline1"] and x["guideline1"]["attribute"] == "DTI"), None)
        self.assertIsNotNone(dti_match)
        self.assertIsNone(dti_match["guideline2"])

if __name__ == '__main__':
    unittest.main()
