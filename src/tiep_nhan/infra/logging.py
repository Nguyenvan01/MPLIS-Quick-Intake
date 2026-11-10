"""Log theo ngày bằng loguru. KHÔNG ghi CCCD đầy đủ ra log — dùng che_cccd()."""
from __future__ import annotations

import re
import sys

from loguru import logger

from .config import LOG_DIR


def _che_so(s: str) -> str:
    return re.sub(r"(?<!\d)(\d{4})\d{5}(\d{3})(?!\d)", r"\1•••\2", s)


def _che_ban_ghi(record) -> None:
    """Lỗi của Playwright kèm nội dung các ô trên trang, có thể có CCCD."""
    record["message"] = _che_so(record["message"])
    ex = record["exception"]
    if ex and ex.value is not None:
        record["exception"] = ex._replace(value=type(ex.type.__name__, (Exception,), {"__str__": lambda _: _che_so(str(ex.value))})())


def setup() -> None:
    logger.remove()
    logger.configure(patcher=_che_ban_ghi)
    if sys.stderr:  # bản đóng gói không có console
        logger.add(sys.stderr, diagnose=False)  # diagnose in giá trị biến trong traceback, tức CCCD đầy đủ
    logger.add(LOG_DIR / "tiep_nhan_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days",
               encoding="utf-8", level="DEBUG", enqueue=True, diagnose=False)


def che_cccd(cccd: str | None) -> str:
    return f"{cccd[:4]}•••{cccd[-3:]}" if cccd and len(cccd) >= 8 else "—"


def che_so_trong_chu(chu: str) -> str:
    """Che mọi dãy 12 chữ số (CCCD) trong một đoạn chữ, ví dụ ghi chú hay nội dung lỗi trước khi lưu, hiện, xuất."""
    return re.sub(r"(?<!\d)\d{12}(?!\d)", lambda m: che_cccd(m[0]), chu or "")
