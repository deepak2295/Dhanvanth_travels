import os
from dotenv import dotenv_values

# Load .env manually
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
env_vars = dotenv_values(env_path)

print("📂 Loading from:", env_path)
print("📦 All env vars:", env_vars)

# Check if key exists
if "GOOGLE_MAPS_API_KEY" in env_vars:
    print("✅ Found Key:", env_vars["GOOGLE_MAPS_API_KEY"])
else:
    print("❌ GOOGLE_MAPS_API_KEY not found")
