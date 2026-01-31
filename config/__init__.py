"""配置模块"""

from .settings import (
    Settings,
    settings,
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    VECTOR_DB_DIR,
)

__all__ = [
    "Settings",
    "settings",
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "VECTOR_DB_DIR",
]
