# backend/scripts/check_token_usage.py

"""
Script to check token usage data from the most recent ingestion.
This shows you the real-time token counts and costs that were tracked.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_latest_report():
    """Find the most recent token usage report."""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    
    if not os.path.exists(reports_dir):
        print(f"❌ Reports directory not found: {reports_dir}")
        return None
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ No reports found in {reports_dir}")
        return None
    
    # Sort by modification time (most recent first)
    pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(reports_dir, x)), reverse=True)
    
    latest_report = os.path.join(reports_dir, pdf_files[0])
    return latest_report


def display_token_usage_from_progress():
    """
    Display token usage from the progress store (in-memory data).
    This shows the actual real-time data that was tracked.
    """
    print("\n" + "=" * 70)
    print("REAL-TIME TOKEN USAGE DATA")
    print("=" * 70)
    
    try:
        from utils.progress import progress_store, progress_lock
        
        with progress_lock:
            if not progress_store:
                print("\n⚠️  No active or recent ingestion sessions found in memory.")
                print("   Run an ingestion to see real-time token tracking.\n")
                return
            
            # Get the most recent session
            sessions = list(progress_store.items())
            if not sessions:
                print("\n⚠️  No session data available.\n")
                return
            
            # Show all sessions
            for session_id, data in sessions:
                print(f"\n📊 Session: {session_id[:16]}...")
                print(f"   Status: {data.get('status', 'unknown')}")
                
                token_usage = data.get('token_usage')
                if token_usage:
                    print(f"\n   🔹 Model: {token_usage.get('provider', 'N/A')}/{token_usage.get('model', 'N/A')}")
                    print(f"   🔹 PDF: {token_usage.get('pdf_name', 'N/A')}")
                    print(f"   🔹 Total Chunks: {token_usage.get('total_chunks', 0)}")
                    print(f"\n   📈 Token Consumption (Real-Time from LLM API):")
                    print(f"      • Prompt Tokens:     {token_usage.get('total_prompt_tokens', 0):,}")
                    print(f"      • Completion Tokens: {token_usage.get('total_completion_tokens', 0):,}")
                    print(f"      • Total Tokens:      {token_usage.get('total_tokens', 0):,}")
                    print(f"\n   💰 Cost (Calculated from Real Tokens):")
                    print(f"      • USD: ${token_usage.get('total_cost', 0):.6f}")
                    print(f"      • INR: ₹{token_usage.get('total_cost_inr', 0):.4f}")
                    print(f"\n   📄 Report: {data.get('token_report_path', 'Not generated')}")
                    
                    # Show per-chunk breakdown
                    chunk_details = token_usage.get('chunk_details', [])
                    if chunk_details:
                        print(f"\n   📋 Per-Chunk Breakdown:")
                        print(f"      {'Chunk':<8} {'Pages':<10} {'Prompt':<10} {'Completion':<12} {'Total':<10} {'USD':<12} {'INR'}")
                        print(f"      {'-'*80}")
                        for chunk in chunk_details[:10]:  # Show first 10 chunks
                            print(f"      {chunk['chunk_num']:<8} "
                                  f"{chunk['page_numbers']:<10} "
                                  f"{chunk['prompt_tokens']:<10,} "
                                  f"{chunk['completion_tokens']:<12,} "
                                  f"{chunk['total_tokens']:<10,} "
                                  f"${chunk['total_cost']:<11.6f} "
                                  f"₹{chunk['total_cost_inr']:.4f}")
                        
                        if len(chunk_details) > 10:
                            print(f"      ... and {len(chunk_details) - 10} more chunks")
                else:
                    print("   ⚠️  No token usage data available for this session.")
                
                print("\n" + "-" * 70)
    
    except Exception as e:
        print(f"\n❌ Error reading progress data: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "=" * 70)
    print("TOKEN USAGE CHECKER")
    print("=" * 70)
    
    # Check for latest report
    latest_report = find_latest_report()
    if latest_report:
        file_time = datetime.fromtimestamp(os.path.getmtime(latest_report))
        print(f"\n📄 Latest Report Found:")
        print(f"   Path: {latest_report}")
        print(f"   Generated: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Size: {os.path.getsize(latest_report):,} bytes")
    else:
        print("\n⚠️  No reports found yet. Run an ingestion to generate a report.")
    
    # Display real-time data from progress store
    display_token_usage_from_progress()
    
    print("\n" + "=" * 70)
    print("HOW TO VERIFY REAL-TIME DATA:")
    print("=" * 70)
    print("""
1. Run an ingestion process through your API
2. The system will automatically track tokens in real-time from the LLM API
3. Check the console output - you'll see token counts logged per chunk
4. After completion, check backend/reports/ for the PDF report
5. Run this script again to see the tracked data

The token counts come directly from:
- OpenAI: response.usage.prompt_tokens, response.usage.completion_tokens
- Gemini: usageMetadata.promptTokenCount, usageMetadata.candidatesTokenCount

These are the ACTUAL token counts reported by the LLM providers!
""")


if __name__ == "__main__":
    main()
