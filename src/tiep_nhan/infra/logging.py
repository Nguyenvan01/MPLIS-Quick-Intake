"""Log theo ngày bằng loguru. KHÔNG ghi CCCD đầy đủ ra log — dùng che_cccd()."""
from __future__ import annotations

from loguru import logger

from .config import LOG_DIR


def setup() -> None:
    logger.add(LOG_DIR / "tiep_nhan_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days",
               encoding="utf-8", level="DEBUG", enqueue=True)


def che_cccd(cccd: str | None) -> str:
    return f"{cccd[:4]}•••{cccd[-3:]}" if cccd and len(cccd) >= 8 else "—"
