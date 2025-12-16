# backend/utils/model_pricing.py

"""
Centralized pricing configuration for LLM models.
Prices are per 1 million tokens (input and output).
Last updated: December 2025
"""

# Currency conversion rate (USD to INR)
USD_TO_INR = 83.50  # Update this rate as needed

# Pricing in USD per 1M tokens
MODEL_PRICING = {
    # OpenAI Models
    "openai": {
        "gpt-4": {
            "input": 30.00,
            "output": 60.00,
            "description": "GPT-4 (8K context)"
        },
        "gpt-4-32k": {
            "input": 60.00,
            "output": 120.00,
            "description": "GPT-4 (32K context)"
        },
        "gpt-4o": {
            "input": 2.50,
            "output": 10.00,
            "description": "GPT-4o (Optimized)"
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
            "description": "GPT-4o Mini"
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50,
            "description": "GPT-3.5 Turbo"
        },
        "gpt-3.5-turbo-16k": {
            "input": 3.00,
            "output": 4.00,
            "description": "GPT-3.5 Turbo (16K context)"
        }
    },
    
    # Google Gemini Models
    "gemini": {
        "gemini-2.5-pro": {
            "input": 1.25,
            "output": 5.00,
            "description": "Gemini 2.5 Pro"
        },
        "gemini-2.5-flash": {
            "input": 0.075,
            "output": 0.30,
            "description": "Gemini 2.5 Flash"
        },
        "gemini-1.5-pro": {
            "input": 1.25,
            "output": 5.00,
            "description": "Gemini 1.5 Pro"
        },
        "gemini-1.5-flash": {
            "input": 0.075,
            "output": 0.30,
            "description": "Gemini 1.5 Flash"
        },
        "gemini-1.5-flash-8b": {
            "input": 0.0375,
            "output": 0.15,
            "description": "Gemini 1.5 Flash-8B"
        }
    }
}


def get_model_pricing(provider: str, model: str) -> dict:
    """
    Get pricing information for a specific model.
    
    Args:
        provider: LLM provider (e.g., "openai", "gemini")
        model: Model name (e.g., "gpt-4o", "gemini-2.5-pro")
    
    Returns:
        Dictionary with input/output pricing and description
        Returns default pricing if model not found
    """
    provider = provider.lower()
    
    if provider not in MODEL_PRICING:
        # Default pricing for unknown providers
        return {
            "input": 1.00,
            "output": 2.00,
            "description": f"Unknown model: {model}"
        }
    
    if model not in MODEL_PRICING[provider]:
        # Default pricing for unknown models within known provider
        return {
            "input": 1.00,
            "output": 2.00,
            "description": f"Unknown {provider} model: {model}"
        }
    
    return MODEL_PRICING[provider][model]


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> dict:
    """
    Calculate the cost for a given token usage in both USD and INR.
    
    Args:
        provider: LLM provider
        model: Model name
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens
    
    Returns:
        Dictionary with cost breakdown in USD and INR
    """
    pricing = get_model_pricing(provider, model)
    
    # Calculate costs in USD (pricing is per 1M tokens)
    input_cost_usd = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost_usd = (completion_tokens / 1_000_000) * pricing["output"]
    total_cost_usd = input_cost_usd + output_cost_usd
    
    # Convert to INR
    input_cost_inr = input_cost_usd * USD_TO_INR
    output_cost_inr = output_cost_usd * USD_TO_INR
    total_cost_inr = total_cost_usd * USD_TO_INR
    
    return {
        "input_cost": round(input_cost_usd, 6),
        "output_cost": round(output_cost_usd, 6),
        "total_cost": round(total_cost_usd, 6),
        "input_cost_inr": round(input_cost_inr, 4),
        "output_cost_inr": round(output_cost_inr, 4),
        "total_cost_inr": round(total_cost_inr, 4),
        "input_price_per_1m": pricing["input"],
        "output_price_per_1m": pricing["output"],
        "model_description": pricing["description"],
        "usd_to_inr_rate": USD_TO_INR
    }
