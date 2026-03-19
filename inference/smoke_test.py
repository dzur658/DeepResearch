"""Minimal smoke test: sends one prompt to the Brev Nemotron deployment and prints the response."""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(script_dir, "..", ".env")

from dotenv import load_dotenv
load_dotenv(env_file)

from openai import OpenAI

api_key = os.environ.get("BREV_API_KEY")
base_url = os.environ.get("BREV_MAIN_BASE_URL")
model_name = os.environ.get("BREV_MAIN_MODEL_NAME")

if not api_key or api_key == "your_brev_api_key":
    print("ERROR: BREV_API_KEY not set in .env"); sys.exit(1)
if not base_url or "your_main_deployment_id" in base_url:
    print("ERROR: BREV_MAIN_BASE_URL not configured in .env"); sys.exit(1)
if not model_name:
    print("ERROR: BREV_MAIN_MODEL_NAME not set in .env"); sys.exit(1)

print(f"Endpoint: {base_url}")
print(f"Model:    {model_name}")
print("Sending test prompt...")

client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

try:
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Say hello and confirm you are Nemotron. Reply in one sentence."}],
        max_tokens=256,
        temperature=1.0,
        top_p=0.95,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}}
    )
    content = response.choices[0].message.content
    print(f"\n=== Response ===\n{content}\n")
    print(f"Model returned: {response.model}")
    print(f"Usage: {response.usage}")
    print("\nSmoke test PASSED.")
except Exception as e:
    print(f"\nSmoke test FAILED: {e}")
    sys.exit(1)
