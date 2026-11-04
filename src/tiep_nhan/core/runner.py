"""Vòng lặp xử lý hồ sơ. Chỉ biết MplisPort, không biết Playwright → test được bằng FakeMplis."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

from ..domain.models import HoSo
from ..mplis.port import MplisPort, so_sanh
from .state import StateStore, TrangThai

# on_event(key, trang_thai, ghi_chu, ma_ho_so)
EventFn = Callable[[str, str, str, str], None]


@dataclass
class RunOptions:
    dry_run: bool = True
    chay_lai_loi: bool = True
    tim_trung_truoc: bool = True


class Runner:
    def __init__(self, ho_so: list[HoSo], port: MplisPort, store: StateStore, opts: RunOptions,
                 on_event: EventFn | None = None, should_stop: Callable[[], bool] = lambda: False):
        self.ho_so, self.port, self.store, self.opts = ho_so, port, store, opts
        self.emit = on_event or (lambda *a: None)
        self.should_stop = should_stop

    def run(self) -> None:
        for hs in self.ho_so:
            if self.should_stop():
                logger.warning("Dừng theo yêu cầu người dùng")
                break
            self.mot_ho_so(hs)

    def mot_ho_so(self, hs: HoSo) -> None:
        bg = self.store.get(hs.key)
        if bg.trang_thai.ket_thuc:
            self.emit(hs.key, "Bỏ qua", "Đã xong ở lần chạy trước", bg.ma_ho_so)
            return
        if bg.trang_thai is TrangThai.CAN_KIEM_TRA:
            self.emit(hs.key, "Bỏ qua", "Cần người kiểm tra (bấm Chạy lại để làm lại)", bg.ma_ho_so)
            return
        if bg.trang_thai is TrangThai.LOI and not self.opts.chay_lai_loi:
            self.emit(hs.key, "Bỏ qua", "Lỗi lần trước", "")
            return

        self.emit(hs.key, "Đang chạy", "", "")
        self.port.trace_start(hs.key)
        try:
            # 1. Tìm trùng — bắt buộc khi lần trước bị ngắt sau khi bấm Lưu (DANG_TAO)
            if self.opts.tim_trung_truoc or bg.trang_thai is TrangThai.DANG_TAO:
                ma = self.port.tim_trung(hs)
                if ma:
                    if bg.trang_thai is TrangThai.DANG_TAO:  # chính lần trước đã tạo xong
                        self._xac_nhan(hs, ma, "Xác nhận sau lần chạy bị ngắt")
                    else:
                        self.store.mark(hs.key, TrangThai.DA_CO_SAN, "Đã có trên MPLIS, không tạo mới", ma)
                        self.emit(hs.key, "Đã có sẵn", "Tìm thấy hồ sơ trùng", ma)
                    self.port.trace_stop(hs.key, keep=False)
                    return

            # 2. Điền form
            self.port.mo_form()
            self.port.dien(hs)

            if self.opts.dry_run:
                anh = self.port.chup(hs.key)
                self.port.huy()
                self.emit(hs.key, "Chạy thử", f"Điền xong, không lưu. Ảnh: {anh}", "")
                self.port.trace_stop(hs.key, keep=False)
                return

            # 3. Lưu → xác nhận
            self.store.mark(hs.key, TrangThai.DANG_TAO, "Đã bấm Lưu, chưa xác nhận")
            ma = self.port.luu()
            self.store.mark(hs.key, TrangThai.DANG_TAO, "Đã lưu, chưa xác nhận", ma)
            self._xac_nhan(hs, ma, "Đã tạo và tra cứu lại khớp")
            self.port.trace_stop(hs.key, keep=False)
        except Exception as e:  # noqa: BLE001 — một hồ sơ lỗi không làm dừng cả lô
            trace = self.port.trace_stop(hs.key, keep=True)
            msg = f"{type(e).__name__}: {str(e).splitlines()[0][:200] if str(e) else ''}"
            if self.store.get(hs.key).trang_thai is not TrangThai.DANG_TAO:
                self.store.mark(hs.key, TrangThai.LOI, msg)
            logger.exception(f"{hs.mo_ta}: lỗi (trace: {trace})")
            self.emit(hs.key, "Lỗi", f"{msg}" + (f" · trace: {trace}" if trace else ""), "")
            try:
                self.port.ve_trang_dau()
            except Exception:  # noqa: BLE001
                pass

    def _xac_nhan(self, hs: HoSo, ma: str, note_ok: str) -> None:
        lech = so_sanh(hs, self.port.doc(ma))
        if lech:
            note = "; ".join(f"{k}: web='{w}' excel='{x}'" for k, (w, x) in lech.items())
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note, ma)
            self.emit(hs.key, "Cần kiểm tra", note, ma)
        else:
            self.store.mark(hs.key, TrangThai.THANH_CONG, note_ok, ma)
            self.emit(hs.key, "Thành công", note_ok, ma)
