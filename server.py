# Root ASGI entrypoint bridge for Render & local runners
import os
import uvicorn
from backend.server import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=False)
