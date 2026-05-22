# API Module
"""
FastAPI 기반 REST API 서버 모듈
"""

# Lazy import to avoid circular dependencies
def get_app():
    from .server import app
    return app

__all__ = ["get_app"]

