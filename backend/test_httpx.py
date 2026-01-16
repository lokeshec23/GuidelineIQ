
import openai
import httpx
print(f"OpenAI Version: {openai.__version__}")
print(f"Httpx Version: {httpx.__version__}")

try:
    # Try to simulate what openai does internally
    client = httpx.Client(proxies="http://foo")
    print("httpx.Client accepts proxies argument!")
except TypeError:
    print("httpx.Client DOES NOT accept proxies argument!")

try:
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_key="dummy",
        api_version="2023-05-15",
        azure_endpoint="https://dummy.openai.azure.com"
    )
    print("AzureOpenAI initialized successfully!")
except Exception as e:
    print(f"AzureOpenAI initialization failed: {e}")
