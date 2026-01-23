import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test Azure OpenAI connection
def test_azure_connection():
    try:
        print("🔍 Testing Azure OpenAI Connection...")
        print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
        print(f"API Version: {os.getenv('AZURE_OPENAI_API_VERSION')}")
        print(f"Embedding Deployment: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')}")
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Test embedding generation
        print("\n📤 Generating test embedding...")
        response = client.embeddings.create(
            input=["test connection"],
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-model")
        )
        
        print(f"✅ SUCCESS! Generated embedding with {len(response.data[0].embedding)} dimensions")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"\nError Type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    test_azure_connection()
