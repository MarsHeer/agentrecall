import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Cloud API configuration from environment variables."""

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://localhost/agentrecall"
        )
    )
    supabase_url: str = field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "")
    )
    supabase_anon_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", "")
    )
    supabase_service_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", "")
    )
    stripe_secret_key: str = field(
        default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret: str = field(
        default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", "")
    )
    jwt_secret: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-change-me")
    )
    cors_origins: list = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "https://agentmemory-landing-swart.vercel.app,http://localhost:3000",
        ).split(",")
    )
    # Free tier limits
    free_tier_memories: int = 10000
    free_tier_api_calls_daily: int = 1000


config = Config()
