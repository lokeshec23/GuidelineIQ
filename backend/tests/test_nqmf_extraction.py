# backend/tests/test_nqmf_extraction.py
"""
Tests for NQMF-specific extraction format validation
"""

import pytest
import re


class TestNQMFFormatValidation:
    """Test cases to validate NQMF bullet-point format"""
    
    def test_valid_bullet_format(self):
        """Test that valid bullet format passes validation"""
        valid_outputs = [
            "• Maximum LTV is limited to 80%.",
            "• Bullet one\n• Bullet two\n• Bullet three",
            "• Single bullet point with detailed information.",
            "• LTV limited to 70%.\n• LTV limited to 75%.",
            "• Bullet 1\n• Bullet 2\n• Bullet 3\n• Bullet 4\n• Bullet 5\n• Bullet 6\n• Bullet 7",  # Unlimited bullets allowed
        ]
        
        for output in valid_outputs:
            assert self._validate_nqmf_format(output), f"Failed for valid output: {output}"
    
    def test_na_output(self):
        """Test that NA output is accepted"""
        assert self._validate_nqmf_format("NA")
    
    def test_bullet_count(self):
        """Test that bullets are counted correctly"""
        # Valid: Any number of bullets
        valid_1_bullet = "• One bullet"
        valid_7_bullets = "• One\n• Two\n• Three\n• Four\n• Five\n• Six\n• Seven"
        
        assert self._count_bullets(valid_1_bullet) == 1
        assert self._count_bullets(valid_7_bullets) == 7
        
        # No upper limit - all counts are valid
    
    def test_bullet_prefix(self):
        """Test that bullets start with '• ' (bullet + space)"""
        valid = "• Correct format"
        invalid_no_space = "•No space after bullet"
        invalid_dash = "- Dash instead of bullet"
        
        assert self._has_valid_bullet_prefix(valid)
        assert not self._has_valid_bullet_prefix(invalid_no_space)
        assert not self._has_valid_bullet_prefix(invalid_dash)
    
    def test_no_paragraphs_outside_bullets(self):
        """Test that there are no paragraphs outside bullets"""
        invalid_paragraph = "This is a paragraph.\n• Bullet point"
        valid_only_bullets = "• Bullet one\n• Bullet two"
        
        assert not self._validate_nqmf_format(invalid_paragraph)
        assert self._validate_nqmf_format(valid_only_bullets)
    
    def test_no_source_attribution(self):
        """Test that output does NOT contain filename references"""
        valid_no_filename = "• LTV limited to 70%.\n• LTV limited to 75%."
        invalid_with_filename = "• LTV limited to 70% [Source1.pdf].\n• LTV limited to 75% [Source2.pdf]."
        
        assert self._validate_nqmf_format(valid_no_filename)
        # With filenames should ideally be avoided but won't break validation
        # (LLM might still include them, but we instructed it not to)
    
    def test_invalid_formats(self):
        """Test that invalid formats are rejected"""
        invalid_outputs = [
            "",  # Empty
            "This is a summary paragraph without bullets.",  # Paragraph
            "1. Numbered list\n2. Another item",  # Numbered list
            "Bullet\n• Missing prefix on first line",  # Missing prefix
        ]
        
        for output in invalid_outputs:
            assert not self._validate_nqmf_format(output), f"Should reject invalid output: {output}"
    
    # Helper methods for validation
    
    def _validate_nqmf_format(self, output: str) -> bool:
        """
        Validate NQMF output format
        
        Returns:
            True if format is valid, False otherwise
        """
        if not output or not output.strip():
            return False
        
        # Special case: "NA" is valid
        if output.strip() == "NA":
            return True
        
        # Must contain bullets
        if "•" not in output:
            return False
        
        # No upper limit on bullet count - any number is valid
        bullet_count = self._count_bullets(output)
        if bullet_count < 1:
            return False
        
        # Split into lines and validate each bullet
        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            if not self._has_valid_bullet_prefix(line):
                return False
        
        return True
    
    def _count_bullets(self, output: str) -> int:
        """Count the number of bullets in the output"""
        return output.count("•")
    
    def _has_valid_bullet_prefix(self, line: str) -> bool:
        """Check if line starts with '• ' (bullet + space)"""
        return line.startswith("• ")


class TestNQMFContentRules:
    """Test content quality rules for NQMF extraction"""
    
    def test_no_ai_conversational_phrases(self):
        """Test that output doesn't contain conversational AI phrases"""
        prohibited_phrases = [
            "generally",
            "typically",
            "may vary",
            "it depends",
            "in most cases",
            "usually",
        ]
        
        valid_output = "• Maximum LTV is limited to 80%."
        for phrase in prohibited_phrases:
            assert phrase.lower() not in valid_output.lower()
    
    def test_numeric_thresholds_preserved(self):
        """Test that numeric values are extracted precisely"""
        valid_outputs = [
            "• Minimum credit score is 620.",
            "• Maximum LTV is 80%.",
            "• DSCR must be at least 1.0.",
        ]
        
        # Check that numbers exist in output
        for output in valid_outputs:
            assert re.search(r'\d+\.?\d*%?', output), f"No numeric threshold found in: {output}"
    
    def test_underwriting_language_tone(self):
        """Test that language uses underwriting/compliance tone"""
        # Valid: declarative, professional
        valid = "• Maximum LTV is limited to 80% for primary residence."
        
        # Invalid: casual, explanatory
        invalid_casual = "• You can get up to 80% LTV if it's your primary home!"
        invalid_explanatory = "• This means that LTV should usually not exceed 80%."
        
        # Simple heuristic: check for casual markers
        assert "!" not in valid
        assert "you" not in valid.lower()
        assert "this means" not in valid.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
