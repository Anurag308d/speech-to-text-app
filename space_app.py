"""Entry point for Hugging Face Spaces (Gradio SDK, free tier).

The Space runs this file with Python. It serves the FastAPI app on port 7860 with uvicorn,
so no Gradio UI is used. Locally, run `uvicorn app.main:app` instead.
"""
import os

import uvicorn

from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
