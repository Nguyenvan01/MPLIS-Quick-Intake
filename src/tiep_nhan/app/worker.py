"""Chạy Runner + PlaywrightMplis trong QThread để giao diện không bị đơ.

Playwright sync API phải được tạo và dùng trong CÙNG một luồng → mọi thứ nằm trong run().
"""
from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QThread, Signal

from ..core.runner import Runner, RunOptions
from ..core.state import StateStore
from ..domain.danh_muc import DanhMuc
from ..domain.models import HoSo
from ..infra.config import Settings
from ..mplis.locators import Locators
from ..mplis.ui_adapter import PlaywrightMplis


class Worker(QThread):
    event = Signal(str, str, str, str)  # key, trạng thái, ghi chú, mã hồ sơ

    def __init__(self, ho_so: list[HoSo], store: StateStore, settings: Settings, L: Locators,
                 dm: DanhMuc, password: str, opts: RunOptions):
        super().__init__()
        self._stop = False
        self.ho_so, self.store, self.settings, self.L, self.dm = ho_so, store, settings, L, dm
        self.password, self.opts = password, opts

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            with PlaywrightMplis(self.settings, self.L, self.dm) as m:
                m.dang_nhap(self.settings.username, self.password)
                Runner(self.ho_so, m, self.store, self.opts, on_event=self.event.emit,
                       should_stop=lambda: self._stop).run()
        except Exception as e:  # noqa: BLE001
            logger.exception("Dừng do lỗi chung")
            self.event.emit("", "Lỗi", f"Dừng do lỗi chung: {e}", "")
