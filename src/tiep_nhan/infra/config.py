"""Đường dẫn và cài đặt. Mọi thứ ghi ra đĩa nằm trong %APPDATA%\\NhapPhieuMPLIS."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "NhapPhieuMPLIS"


def app_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def sub_dir(name: str) -> Path:
    p = app_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def resource_dir() -> Path:
    """Thư mục config/ đi kèm bản cài (PyInstaller) hoặc trong repo khi dev."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "config"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3] / "config"


def assets_dir() -> Path:
    """Thư mục assets/ (font...) đi kèm bản cài hoặc trong repo khi dev."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3] / "assets"


def config_file(name: str) -> Path:
    """Ưu tiên bản người dùng đã sửa trong %APPDATA%, không có thì dùng bản mặc định."""
    user = app_dir() / name
    return user if user.exists() else resource_dir() / name


LOG_DIR = sub_dir("logs")
TRACE_DIR = sub_dir("traces")
SHOT_DIR = sub_dir("screenshots")
BROWSER_PROFILE = sub_dir("chromium-profile")
STATE_DB = app_dir() / "trang_thai.sqlite3"
SETTINGS_FILE = app_dir() / "settings.json"


@dataclass
class Settings:
    mplis_url: str = "https://hye.mplis.gov.vn"
    username: str = ""
    headless: bool = False
    slow_mo_ms: int = 0
    timeout_ms: int = 30_000
    che_do_gom: str = "moi_dong"          # xem domain/gom_ho_so.py
    cho_chay_khi_canh_bao: bool = True
    tim_trung_truoc: bool = True
    nguoi_ky: str = "Phạm Ngọc Trường"
    ds_can_bo: list[str] = field(default_factory=lambda: ["ltmung.nnmt", "ndanh.tnmt"])  # combobox người xử lý
    thoi_han_mac_dinh: str = "Lâu dài"    # dùng khi Excel không có cột/ô Thời hạn
    quy_trinh: str = "2"                  # 1.012787: "1" đơn lẻ dưới 30 hồ sơ, "2" chủ đầu tư từ 30 hồ sơ trở lên
    danh_ba_can_bo: dict[str, str] = field(default_factory=dict)  # tài khoản -> họ tên người xử lý, tool tự lấy từ MPLIS

    @classmethod
    def load(cls) -> "Settings":
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self) -> None:
        SETTINGS_FILE.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
