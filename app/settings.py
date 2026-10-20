import os
import subprocess
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    allowed_origins: list[str]
    max_steps: int
    max_tokens_per_task: int
    max_cost_per_task: float
    max_replans: int
    git_sha: str
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    default_eval_provider: str = "deepseek"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    default_ai_provider: str = "gemini"
    default_ai_model: str = "gemini-3.5-flash-lite"
    live_rate_limit_max_calls: int = 5
    live_rate_limit_window_seconds: int = 600
    database_url: str | None = None


def get_git_sha() -> str:
    # 1. settings.git_sha (CI-injected)
    if os.environ.get("GIT_SHA"):
        return os.environ["GIT_SHA"].strip()

    # 2. git rev-parse HEAD
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if sha:
            return sha
    except (subprocess.SubprocessError, OSError):
        pass

    # 3. "unknown"
    return "unknown"


def _read_env_file(path: str = ".env") -> dict[str, str]:
    env_vars: dict[str, str] = {}
    p = Path(path)
    if p.exists():
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
        except OSError:
            pass
    return env_vars


def load_settings() -> Settings:
    file_vars = _read_env_file()

    def get_val(key: str, default: str = "") -> str:
        return os.environ.get(key) or file_vars.get(key) or default

    origins_raw = get_val("ALLOWED_ORIGINS", "http://localhost:4200,https://tripagent.vector.me")
    origins = [x.strip() for x in origins_raw.split(",") if x.strip()]

    return Settings(
        allowed_origins=origins,
        max_steps=int(get_val("MAX_STEPS", "25")),
        max_tokens_per_task=int(get_val("MAX_TOKENS_PER_TASK", "60000")),
        max_cost_per_task=float(get_val("MAX_COST_PER_TASK", "0.05")),
        max_replans=int(get_val("MAX_REPLANS", "3")),
        git_sha=get_git_sha(),
        openai_api_key=get_val("OPENAI_API_KEY") or None,
        deepseek_api_key=get_val("DEEPSEEK_API_KEY") or None,
        deepseek_base_url=get_val("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        default_eval_provider=get_val("DEFAULT_EVAL_PROVIDER", "deepseek"),
        gemini_api_key=get_val("GEMINI_API_KEY") or None,
        gemini_base_url=get_val("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        default_ai_provider=get_val("DEFAULT_AI_PROVIDER", "gemini"),
        default_ai_model=get_val("DEFAULT_AI_MODEL", "gemini-3.5-flash-lite"),
        live_rate_limit_max_calls=int(get_val("LIVE_RATE_LIMIT_MAX_CALLS", "5")),
        live_rate_limit_window_seconds=int(get_val("LIVE_RATE_LIMIT_WINDOW_SECONDS", "600")),
        database_url=get_val("DATABASE_URL") or None,
    )


settings = load_settings()
