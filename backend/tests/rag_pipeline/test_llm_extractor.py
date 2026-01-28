
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from rag_pipeline.extraction.llm_extractor import LLMExtractor
from rag_pipeline.models import ExtractionResult

@pytest.fixture
def mock_llm_client():
    with patch("rag_pipeline.extraction.llm_extractor.AsyncAzureOpenAI") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client

@pytest.mark.asyncio
async def test_extraction_success(mock_llm_client):
    """Test successful extraction with valid JSON response"""
    
    # Mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"value": "Min 660", "citations": []}'))
    ]
    mock_llm_client.chat.completions.create.return_value = mock_response
    
    extractor = LLMExtractor()
    # Mock the embedding/client check implicitly or it will try to init real client
    # The fixture patches AsyncAzureOpenAI class, so LLMExtractor() init will use mock
    
    context = [{"text": "Context", "metadata": {"page": 1, "filename": "doc.pdf"}}]
    result = await extractor.extract(
        parameter_name="Minimum FICO",
        context_chunks=context,
        query="What is min FICO?"
    )
    
    assert isinstance(result, ExtractionResult)
    assert result.value == "Min 660"

@pytest.mark.asyncio
async def test_extraction_json_correction(mock_llm_client):
    """Test extraction deals with markdown code blocks"""
    
    # Mock response with markdown code block
    mock_response = MagicMock()
    content = '```json\n{"value": "Min 660", "citations": []}\n```'
    mock_response.choices = [
        MagicMock(message=MagicMock(content=content))
    ]
    mock_llm_client.chat.completions.create.return_value = mock_response
    
    extractor = LLMExtractor()
    
    context = [{"text": "Context", "metadata": {"page": 1, "filename": "doc.pdf"}}]
    result = await extractor.extract(
        parameter_name="Minimum FICO",
        context_chunks=context,
        query="What is min FICO?"
    )
    
    assert result.value == "Min 660"
