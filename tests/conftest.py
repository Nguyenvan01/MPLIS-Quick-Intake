from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
CONFIG = Path(__file__).parents[1] / "config"


@pytest.fixture
def mau() -> Path:
    """File phiếu chuyển ĐÃ ẨN DANH, giữ nguyên lỗi cấu trúc của file thật (ô gộp AA5:AC6, dòng 9 lạc)."""
    return DATA / "phieu_mau_an_danh.xlsx"
