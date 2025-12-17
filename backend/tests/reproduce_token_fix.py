
import sys
import unittest
from unittest.mock import MagicMock, patch

# Adjust path to import backend modules if needed
sys.path.append("c:/Users/lsaravanan/Lokesh_ws/GuidelineIQ")

from backend.utils.llm_provider import LLMProvider

class TestGeminiTokenFix(unittest.TestCase):
    @patch("backend.utils.llm_provider.requests.Session")
    def test_hidden_token_calculation(self, mock_session_cls):
        # Mock the session instance and its post method
        mock_session = mock_session_cls.return_value
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response
        
        # Scenario: 
        # Prompt: 100
        # Completion: 50
        # Total: 160 (Mismatch! 10 hidden tokens)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Test response"}]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 100,
                "candidatesTokenCount": 50,
                "totalTokenCount": 160
            }
        }
        
        provider = LLMProvider(provider="gemini", api_key="fake_key", model="gemini-1.5-pro")
        
        # Inject the mock session
        LLMProvider._gemini_session = mock_session
        
        result = provider.generate("System", "User")
        
        usage = result["usage"]
        print(f"\nDEBUG: Usage Result: {usage}")
        
        # Verification
        # Original Prompt: 100
        # Hidden: 160 - (100 + 50) = 10
        # Expected Prompt in dict: 100 + 10 = 110
        self.assertEqual(usage["prompt_tokens"], 110, "Hidden tokens should be added to prompt_tokens")
        self.assertEqual(usage["completion_tokens"], 50)
        self.assertEqual(usage["total_tokens"], 160)
        
        print("SUCCESS: Input tokens were correctly adjusted for hidden overhead.")

if __name__ == "__main__":
    unittest.main()
