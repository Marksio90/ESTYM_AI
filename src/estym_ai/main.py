"""Application entry point."""

import uvicorn

from estym_ai.api.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "estym_ai.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
