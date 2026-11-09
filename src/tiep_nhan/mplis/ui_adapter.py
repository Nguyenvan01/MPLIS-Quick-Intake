"""MplisPort bằng Playwright + Chromium."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import expect, sync_playwright

from ..domain.danh_muc import DanhMuc
from ..domain.models import HoSo
from ..infra.config import BROWSER_PROFILE, SHOT_DIR, TRACE_DIR, Settings
from .locators import Locators
from .pages.chuyen_quyen import ChuyenQuyenPage
from .pages.tiep_nhan import TiepNhanPage
from .pages.tra_cuu import TraCuuPage


def da_dang_nhap(url: str, base_url: str) -> bool:
    u = urlparse(url)
    return u.hostname == urlparse(base_url).hostname and u.path.startswith("/dc")


def _safe(s: str) -> str:
    return re.sub(r"[^\w.-]", "_", s)


class PlaywrightMplis:
    """Dùng: with PlaywrightMplis(settings, L, dm) as mplis: Runner(..., port=mplis).run()"""

    def __init__(self, settings: Settings, L: Locators, dm: DanhMuc):
        self.settings, self.L, self.dm = settings, L, dm
        self.hoi_so_moi = None  # giao diện gán vào để hỏi số mới khi MPLIS báo trùng

    def __enter__(self) -> "PlaywrightMplis":
        if getattr(sys, "frozen", False):  # bản đóng gói mang Chromium theo trong thư mục cài
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=self.settings.headless, slow_mo=self.settings.slow_mo_ms,
            no_viewport=True, args=["--start-maximized"],
        )
        self.ctx.set_default_timeout(self.settings.timeout_ms)
        expect.set_options(timeout=self.settings.timeout_ms)  # mặc định 5s, ngắn hơn overlay của MPLIS
        self.ctx.tracing.start(screenshots=True, snapshots=True)
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.tra_cuu = TraCuuPage(self.page, self.L, self.settings.mplis_url)
        self.form = TiepNhanPage(self.page, self.L, self.settings.mplis_url)
        self.wizard = ChuyenQuyenPage(self.page, self.L, self.settings.mplis_url, self.dm, self.settings.nguoi_ky)
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.ctx.tracing.stop()
            self.ctx.close()
        finally:
            self._pw.stop()

    # ----- MplisPort -----
    def cho_dang_nhap(self) -> None:
        self.page.goto(urljoin(self.settings.mplis_url, "/dc/"))
        logger.info("Đăng nhập trong cửa sổ trình duyệt, tool sẽ tự chạy tiếp khi vào được MPLIS")
        self.page.wait_for_url(lambda u: da_dang_nhap(u, self.settings.mplis_url), timeout=600_000)

    def dia_chi_ho_so(self) -> str:
        return self.form.url_ho_so or ""

    def mo_ho_so(self, duong_dan: str) -> None:
        self.form.url_ho_so = duong_dan

    def tim_trung(self, hs: HoSo) -> str | None:
        return self.tra_cuu.tim(hs)

    def mo_form(self) -> None:
        self.form.mo()

    def dien(self, hs: HoSo) -> None:
        self.form.dien(hs)

    def chup(self, key: str) -> str:
        path = SHOT_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe(key)}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    def huy(self) -> None:
        self.form.huy()

    def luu(self) -> str:
        return self.form.luu()

    def chon_gcn(self, hs: HoSo, ma_ho_so: str) -> None:
        self.form.chon_gcn()

    def chuyen_xu_ly(self, hs: HoSo, ma_ho_so: str) -> str:
        return self.form.chuyen_xu_ly(hs)

    def dien_chuyen_quyen(self, hs: HoSo, ma_ho_so: str) -> None:
        self.wizard.url_ho_so = self.form.url_ho_so
        self.wizard.hoi_so_moi = self.hoi_so_moi
        self.wizard.dien(hs)

    def hoan_tat(self, hs: HoSo, ma_ho_so: str) -> None:
        self.wizard.hoan_tat()

    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]:
        return self.tra_cuu.doc(hs, ma_ho_so)

    def ve_trang_dau(self) -> None:
        self.page.goto(self.settings.mplis_url)

    def trace_start(self, key: str) -> None:
        self.ctx.tracing.start_chunk(title=key)

    def trace_stop(self, key: str, keep: bool) -> str | None:
        if not keep:
            self.ctx.tracing.stop_chunk()
            return None
        path = TRACE_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe(key)}.zip"
        self.ctx.tracing.stop_chunk(path=str(path))
        logger.info(f"Đã lưu trace: {path}")
        return str(path)

    # ----- tiện ích cho lệnh kiem-locator -----
    def kiem_section(self, section: str) -> list[tuple[str, str]]:
        """Kiểm từng locator trong section trên TRANG HIỆN TẠI: (đường dẫn, kết quả)."""
        out = []
        for key in self.L.section(section):
            path = f"{section}.{key}"
            try:
                n = self.L.get(self.page, path).count()
                out.append((path, "OK" if n == 1 else f"thấy {n} phần tử"))
            except Exception as e:  # noqa: BLE001
                out.append((path, str(e)))
        return out
