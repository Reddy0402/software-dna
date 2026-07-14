from typing import Any, Dict, Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Software DNA"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "software_dna"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        
        # Access properties from the validation values dictionary
        data = info.data
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg2",
                username=data.get("POSTGRES_USER"),
                password=data.get("POSTGRES_PASSWORD"),
                host=data.get("POSTGRES_SERVER"),
                path=data.get("POSTGRES_DB") or "",
            )
        )

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # Workspace & Git Settings
    WORKSPACE_BASE_DIR: str = "workspace/repos"
    GIT_CLONE_TIMEOUT: int = 300
    GIT_EXECUTABLE: Optional[str] = None

    # Language Detection Configuration (extension -> language)
    LANGUAGE_MAP: dict[str, str] = {
        "py": "Python",
        "js": "JavaScript",
        "mjs": "JavaScript",
        "cjs": "JavaScript",
        "ts": "TypeScript",
        "tsx": "TypeScript",
        "java": "Java",
        "cpp": "C++",
        "cc": "C++",
        "cxx": "C++",
        "hpp": "C++",
        "c": "C",
        "h": "C",
        "go": "Go",
        "rs": "Rust",
        "cs": "C#"
    }

    # Directories to ignore recursively during traversal
    IGNORED_DIRECTORIES: list[str] = [
        ".git", ".github", "node_modules", "venv", ".venv", "dist", "build",
        "target", "bin", "obj", "coverage", ".idea", ".vscode", "__pycache__",
        ".pytest_cache", ".mypy_cache", ".next", ".nuxt", ".terraform"
    ]

    # File extensions to ignore (binaries, compiled artifacts, media, lockfiles)
    IGNORED_EXTENSIONS: list[str] = [
        "zip", "tar", "gz", "rar", "7z", "bz2", "xz",
        "exe", "dll", "so", "dylib", "bin", "o", "a", "lib", "pyc", "class", "jar", "war",
        "png", "jpg", "jpeg", "gif", "svg", "ico", "webp", "bmp", "tiff",
        "mp4", "mkv", "avi", "mov", "flv", "wmv", "lock"
    ]

    # Specific file names to ignore
    IGNORED_FILENAMES: list[str] = [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock",
        "poetry.lock", "composer.lock", "mix.lock", "paket.lock"
    ]

    # Settings configurations
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
