from .app import app

__all__ = ["app", "main"]


def main() -> None:
    """Run the development server."""
    import uvicorn

    from .config import get_settings

    settings = get_settings()
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
