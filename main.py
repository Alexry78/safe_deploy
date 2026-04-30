import os
from dotenv import load_dotenv

load_dotenv()

secret = os.getenv("APP_SECRET")

if not secret:
    print("ERROR: APP_SECRET environment variable not set. Create a .env file.")
    exit(1)

print(f"System started. Secret hash: {secret[:3]}*")

