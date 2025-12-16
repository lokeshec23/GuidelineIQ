# backend/utils/token_tracker.py

"""
Token usage tracking utility for monitoring LLM consumption during ingestion.
Tracks tokens per chunk and calculates costs based on model pricing.
"""

from typing import List, Dict
from datetime import datetime
from utils.model_pricing import calculate_cost


class TokenTracker:
    """
    Tracks token usage across multiple LLM calls during ingestion process.
    """
    
    def __init__(self, provider: str, model: str, pdf_name: str, investor: str, version: str):
        """
        Initialize token tracker.
        
        Args:
            provider: LLM provider (e.g., "openai", "gemini")
            model: Model name (e.g., "gpt-4o", "gemini-2.5-pro")
            pdf_name: Name of the uploaded PDF file
            investor: Investor name
            version: Version string
        """
        self.provider = provider
        self.model = model
        self.pdf_name = pdf_name
        self.investor = investor
        self.version = version
        self.start_time = datetime.now()
        self.end_time = None
        
        # Track per-chunk usage
        self.chunk_usage: List[Dict] = []
        
        # Aggregate totals
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def add_chunk_usage(self, chunk_num: int, prompt_tokens: int, completion_tokens: int, 
                   total_tokens: int, page_numbers: str = ""):
    
        # Check for unbilled tokens (common in Gemini)
        calculated_total = prompt_tokens + completion_tokens
        hidden_tokens = 0
        
        if total_tokens > calculated_total:
            hidden_tokens = total_tokens - calculated_total
            # Assume hidden tokens (system prompts) are billed as Input
            prompt_tokens += hidden_tokens 

        # Calculate cost for this chunk
        cost_info = calculate_cost(self.provider, self.model, prompt_tokens, completion_tokens)
        
        chunk_data = {
            "chunk_num": chunk_num,
            "page_numbers": page_numbers,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "input_cost": cost_info["input_cost"],
            "output_cost": cost_info["output_cost"],
            "total_cost": cost_info["total_cost"],
            "input_cost_inr": cost_info["input_cost_inr"],
            "output_cost_inr": cost_info["output_cost_inr"],
            "total_cost_inr": cost_info["total_cost_inr"]
        }
        
        self.chunk_usage.append(chunk_data)
        
        # Update totals
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.total_cost += cost_info["total_cost"]
    
    def finalize(self):
        """Mark the tracking as complete and record end time."""
        self.end_time = datetime.now()
    
    def get_summary(self) -> Dict:
        """
        Get a summary of all token usage.
        
        Returns:
            Dictionary with comprehensive usage statistics in USD and INR
        """
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        # Get pricing info for display
        cost_info = calculate_cost(self.provider, self.model, 
                                   self.total_prompt_tokens, 
                                   self.total_completion_tokens)
        
        return {
            "provider": self.provider,
            "model": self.model,
            "model_description": cost_info["model_description"],
            "pdf_name": self.pdf_name,
            "investor": self.investor,
            "version": self.version,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "total_chunks": len(self.chunk_usage),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "total_cost_inr": round(cost_info["total_cost_inr"], 4),
            "input_price_per_1m": cost_info["input_price_per_1m"],
            "output_price_per_1m": cost_info["output_price_per_1m"],
            "usd_to_inr_rate": cost_info["usd_to_inr_rate"],
            "chunk_details": self.chunk_usage
        }
    
    def get_average_per_chunk(self) -> Dict:
        """
        Calculate average token usage per chunk.
        
        Returns:
            Dictionary with average statistics
        """
        if not self.chunk_usage:
            return {
                "avg_prompt_tokens": 0,
                "avg_completion_tokens": 0,
                "avg_total_tokens": 0,
                "avg_cost": 0.0
            }
        
        num_chunks = len(self.chunk_usage)
        
        return {
            "avg_prompt_tokens": round(self.total_prompt_tokens / num_chunks, 2),
            "avg_completion_tokens": round(self.total_completion_tokens / num_chunks, 2),
            "avg_total_tokens": round(self.total_tokens / num_chunks, 2),
            "avg_cost": round(self.total_cost / num_chunks, 6)
        }
    
    def __str__(self) -> str:
        """String representation for logging."""
        return (f"TokenTracker({self.provider}/{self.model}): "
                f"{self.total_tokens:,} tokens, ${self.total_cost:.6f}, "
                f"{len(self.chunk_usage)} chunks")
