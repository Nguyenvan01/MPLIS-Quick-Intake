"""MplisPort bằng Playwright + Microsoft Edge có sẵn (channel="msedge")."""
from __future__ import annotations

import re
from datetime import datetime

from loguru import logger
from playwright.sync_api import sync_playwright

from ..domain.danh_muc import DanhMuc
from ..domain.models import HoSo
from ..infra.config import BROWSER_PROFILE, SHOT_DIR, TRACE_DIR, Settings
from .locators import Locators
from .pages.login import LoginPage
from .pages.them_moi_nhanh import ThemMoiNhanhPage
from .pages.tra_cuu import TraCuuPage


def _safe(s: str) -> str:
    return re.sub(r"[^\w.-]", "_", s)


class PlaywrightMplis:
    """Dùng: with PlaywrightMplis(settings, L, dm) as mplis: Runner(..., port=mplis).run()"""

    def __init__(self, settings: Settings, L: Locators, dm: DanhMuc):
        self.settings, self.L, self.dm = settings, L, dm

    def __enter__(self) -> "PlaywrightMplis":
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE), channel="msedge",
            headless=self.settings.headless, slow_mo=self.settings.slow_mo_ms,
            no_viewport=True, args=["--start-maximized"],
        )
        self.ctx.set_default_timeout(self.settings.timeout_ms)
        self.ctx.tracing.start(screenshots=True, snapshots=True)
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.login = LoginPage(self.page, self.L)
        self.tra_cuu = TraCuuPage(self.page, self.L)
        self.form = ThemMoiNhanhPage(self.page, self.L, self.dm)
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.ctx.tracing.stop()
            self.ctx.close()
        finally:
            self._pw.stop()

    # ----- MplisPort -----
    def dang_nhap(self, username: str, password: str) -> None:
        self.login.dang_nhap(self.settings.mplis_url, username, password)

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

    def doc(self, ma_ho_so: str) -> dict[str, str]:
        return self.tra_cuu.doc(ma_ho_so)

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
