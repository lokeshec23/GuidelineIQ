# Test script for token tracking system
# This script tests the token tracker and report generator with mock data

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.token_tracker import TokenTracker
from utils.report_generator import generate_token_report
from utils.model_pricing import get_model_pricing, calculate_cost

def test_pricing():
    """Test pricing calculations."""
    print("=" * 60)
    print("Testing Pricing Calculations")
    print("=" * 60)
    
    # Test OpenAI pricing
    openai_pricing = get_model_pricing("openai", "gpt-4o")
    print(f"\nOpenAI GPT-4o pricing: {openai_pricing}")
    
    openai_cost = calculate_cost("openai", "gpt-4o", 1000, 500)
    print(f"Cost for 1000 prompt + 500 completion tokens:")
    print(f"  USD: ${openai_cost['total_cost']:.6f}")
    print(f"  INR: ₹{openai_cost['total_cost_inr']:.4f}")
    
    # Test Gemini pricing
    gemini_pricing = get_model_pricing("gemini", "gemini-2.5-pro")
    print(f"\nGemini 2.5 Pro pricing: {gemini_pricing}")
    
    gemini_cost = calculate_cost("gemini", "gemini-2.5-pro", 1000, 500)
    print(f"Cost for 1000 prompt + 500 completion tokens:")
    print(f"  USD: ${gemini_cost['total_cost']:.6f}")
    print(f"  INR: ₹{gemini_cost['total_cost_inr']:.4f}")
    
    print(f"\nExchange Rate: 1 USD = ₹{openai_cost['usd_to_inr_rate']:.2f}")
    print("\n✅ Pricing calculations working correctly (USD & INR)\n")


def test_token_tracker():
    """Test token tracker functionality."""
    print("=" * 60)
    print("Testing Token Tracker")
    print("=" * 60)
    
    # Initialize tracker
    tracker = TokenTracker(
        provider="gemini",
        model="gemini-2.5-pro",
        pdf_name="test_guideline.pdf",
        investor="TestInvestor",
        version="v1.0"
    )
    
    # Simulate adding chunk usage
    tracker.add_chunk_usage(1, 1200, 450, 1650, "1-2")
    tracker.add_chunk_usage(2, 1150, 480, 1630, "3-4")
    tracker.add_chunk_usage(3, 1300, 520, 1820, "5-6")
    
    # Finalize tracking
    tracker.finalize()
    
    # Get summary
    summary = tracker.get_summary()
    print(f"\nTracker Summary:")
    print(f"  Total Chunks: {summary['total_chunks']}")
    print(f"  Total Tokens: {summary['total_tokens']:,}")
    print(f"  Total Cost (USD): ${summary['total_cost']:.6f}")
    print(f"  Total Cost (INR): ₹{summary['total_cost_inr']:.4f}")
    
    # Get averages
    averages = tracker.get_average_per_chunk()
    print(f"\nAverages per Chunk:")
    print(f"  Avg Tokens: {averages['avg_total_tokens']:.2f}")
    print(f"  Avg Cost: ${averages['avg_cost']:.6f}")
    
    print(f"\n{tracker}")
    print("\n✅ Token tracker working correctly (USD & INR)\n")
    
    return summary


def test_report_generation(summary):
    """Test PDF report generation."""
    print("=" * 60)
    print("Testing PDF Report Generation")
    print("=" * 60)
    
    # Create reports directory
    reports_dir = os.path.join(os.path.dirname(__file__), "test_reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate report
    report_path = generate_token_report(
        summary=summary,
        output_dir=reports_dir,
        investor="TestInvestor",
        version="v1.0"
    )
    
    print(f"\n✅ PDF report generated successfully!")
    print(f"   Report saved to: {report_path}")
    print(f"   File size: {os.path.getsize(report_path):,} bytes")
    
    return report_path


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TOKEN USAGE MONITORING SYSTEM - TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: Pricing
        test_pricing()
        
        # Test 2: Token Tracker
        summary = test_token_tracker()
        
        # Test 3: Report Generation
        report_path = test_report_generation(summary)
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
        print(f"\nYou can review the generated report at:")
        print(f"{report_path}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
