# Load .env on import so every entrypoint (the web app, ingest, eval, the agent)
# picks up OPENAI_BASE_URL / OPENAI_API_KEY without you exporting them by hand.
from dotenv import load_dotenv

load_dotenv()
