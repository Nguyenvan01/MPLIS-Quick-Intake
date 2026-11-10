"""Chạy Runner trong QThread, để giao diện không bị treo."""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import ContextManager

from loguru import logger
from PySide6.QtCore import QThread, Signal

from ..core.runner import Runner, RunOptions
from ..core.state import StateStore
from ..domain.models import HoSo
from ..mplis.port import MplisPort


class Worker(QThread):
    event = Signal(str, str, str, str)  # key, trạng thái, ghi chú, mã hồ sơ
    hoi_so = Signal(str, str)           # mô tả thửa, số phát hành bị trùng
    danh_ba = Signal(dict)              # tài khoản -> họ tên người xử lý lấy từ MPLIS

    def __init__(self, ho_so: list[HoSo], store: StateStore, tao_port: Callable[[], ContextManager[MplisPort]],
                 opts: RunOptions):
        super().__init__()
        self._stop = False
        self._co_tra_loi = threading.Event()
        self._so_moi = ""
        self.ho_so, self.store, self.tao_port, self.opts = ho_so, store, tao_port, opts

    def stop(self) -> None:
        self._stop = True

    def tra_loi(self, so: str) -> None:
        self._so_moi = so
        self._co_tra_loi.set()

    def _hoi_so(self, mo_ta: str, so: str) -> str | None:
        """Chạy trong luồng này; chờ người dùng trả lời trên giao diện."""
        self._co_tra_loi.clear()
        self.hoi_so.emit(mo_ta, so)
        self._co_tra_loi.wait()
        return self._so_moi or None

    def _lay_danh_ba(self, m: MplisPort) -> None:
        """Làm mới danh sách người xử lý cho ô chọn ở màn Lô mới; lỗi thì bỏ qua, không ảnh hưởng lượt chạy."""
        try:
            ds = m.ds_nguoi_xu_ly()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Không lấy được danh sách người xử lý: {type(e).__name__}: {str(e)[:150]}")
            return
        if ds:
            self.danh_ba.emit(ds)

    def run(self) -> None:
        try:
            with self.tao_port() as m:
                m.hoi_so_moi = self._hoi_so
                m.cho_dang_nhap()
                self._lay_danh_ba(m)
                Runner(self.ho_so, m, self.store, self.opts, on_event=self.event.emit,
                       should_stop=lambda: self._stop).run()
        except Exception as e:  # noqa: BLE001
            logger.exception("Dừng do lỗi chung")
            self.event.emit("", "Lỗi", f"Dừng do lỗi chung: {e}", "")
