"""Vòng lặp xử lý hồ sơ. Chỉ biết MplisPort, không biết Playwright → test được bằng FakeMplis."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from loguru import logger

from ..domain.models import HoSo
from ..mplis.port import MplisPort, SoPhatHanhTrung, so_sanh
from .state import StateStore, TrangThai

# on_event(key, trang_thai, ghi_chu, ma_ho_so)
EventFn = Callable[[str, str, str, str], None]


@dataclass
class RunOptions:
    dry_run: bool = True
    chay_lai_loi: bool = True
    tim_trung_truoc: bool = True
    tai_khoan: str = ""  # tài khoản đang đăng nhập; chuyển cho người khác thì không làm wizard


MOC_SAU_LUU = (TrangThai.DA_LUU, TrangThai.DA_CHON_GCN, TrangThai.DA_CHUYEN_XU_LY, TrangThai.DANG_HOAN_TAT)


class _DoGio:
    """Bọc port để cộng dồn thời gian các bước gọi lên MPLIS (task 3.5)."""
    BUOC = ("tim_trung", "mo_form", "dien", "luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "doc")

    def __init__(self, port: MplisPort):
        self._port = port
        self.giay: dict[str, float] = {}

    def __getattr__(self, ten: str):
        ham = getattr(self._port, ten)
        if ten not in self.BUOC:
            return ham

        def do(*a, **k):
            dau = perf_counter()
            try:
                return ham(*a, **k)
            finally:
                self.giay[ten] = self.giay.get(ten, 0) + perf_counter() - dau
        return do


class Runner:
    def __init__(self, ho_so: list[HoSo], port: MplisPort, store: StateStore, opts: RunOptions,
                 on_event: EventFn | None = None, should_stop: Callable[[], bool] = lambda: False):
        self.ho_so, self.store, self.opts = ho_so, store, opts
        self.port = _DoGio(port)
        self.emit = on_event or (lambda *a: None)
        self.should_stop = should_stop

    def run(self) -> None:
        for hs in self.ho_so:
            if self.should_stop():
                logger.warning("Dừng theo yêu cầu người dùng")
                break
            self.port.giay.clear()
            self.mot_ho_so(hs)
            if self.port.giay:
                logger.info(f"Thời gian {hs.key}: " + ", ".join(f"{k} {v:.1f}s" for k, v in self.port.giay.items()))

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

        dang_do = bg.trang_thai in MOC_SAU_LUU
        if dang_do and self.opts.dry_run:
            self.emit(hs.key, "Bỏ qua", "Hồ sơ đã lưu dở trên MPLIS, chạy thử không đụng tới", bg.ma_ho_so)
            return

        self.emit(hs.key, "Đang chạy", "", "")
        self.port.trace_start(hs.key)
        try:
            if dang_do:  # đã có mã hồ sơ: đi tiếp từ mốc còn dở, tuyệt đối không tạo mới
                if bg.duong_dan:
                    self.port.mo_ho_so(bg.duong_dan)
                self._sau_luu(hs, bg.ma_ho_so, "Hoàn tất phần còn dở")
                self.port.trace_stop(hs.key, keep=False)
                return

            # 1. Tìm trùng — bắt buộc khi lần trước bị ngắt sau khi bấm Lưu (DANG_TAO)
            if self.opts.tim_trung_truoc or bg.trang_thai is TrangThai.DANG_TAO:
                ma = self.port.tim_trung(hs)
                if ma:
                    if bg.trang_thai is TrangThai.DANG_TAO:  # chính lần trước đã tạo xong
                        self.store.mark(hs.key, TrangThai.DA_LUU, "Tìm lại được sau lần chạy bị ngắt", ma)
                        self._sau_luu(hs, ma, "Xác nhận sau lần chạy bị ngắt")
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
            self.store.mark(hs.key, TrangThai.DA_LUU, "Đã lưu, chưa chọn GCN", ma, duong_dan=self.port.dia_chi_ho_so())
            self._sau_luu(hs, ma, "Đã tạo và tra cứu lại khớp")
            self.port.trace_stop(hs.key, keep=False)
        except Exception as e:  # noqa: BLE001 — một hồ sơ lỗi không làm dừng cả lô
            trace = self.port.trace_stop(hs.key, keep=True)
            msg = f"{type(e).__name__}: {str(e).splitlines()[0][:200] if str(e) else ''}"
            if self.store.get(hs.key).trang_thai not in (TrangThai.DANG_TAO, TrangThai.CAN_KIEM_TRA, *MOC_SAU_LUU):
                self.store.mark(hs.key, TrangThai.LOI, msg)
            logger.exception(f"{hs.mo_ta}: lỗi (trace: {trace})")
            self.emit(hs.key, "Lỗi", f"{msg}" + (f" · trace: {trace}" if trace else ""), "")
            try:
                self.port.ve_trang_dau()
            except Exception:  # noqa: BLE001
                pass

    def _sau_luu(self, hs: HoSo, ma: str, note_ok: str) -> None:
        if self.store.get(hs.key).trang_thai is TrangThai.DA_LUU:
            self.port.chon_gcn(hs, ma)
            self.store.mark(hs.key, TrangThai.DA_CHON_GCN, "Đã chọn GCN, chưa chuyển xử lý", ma)
        if self.store.get(hs.key).trang_thai is TrangThai.DA_CHON_GCN:
            nhan = self.port.chuyen_xu_ly(hs, ma)
            if not self.opts.tai_khoan or nhan != self.opts.tai_khoan:
                note = f"Đã chuyển cho {nhan}"
                self.store.mark(hs.key, TrangThai.DA_CHUYEN_NGUOI_KHAC, note, ma)
                self.emit(hs.key, "Đã chuyển", note, ma)
                return
            self.store.mark(hs.key, TrangThai.DA_CHUYEN_XU_LY, "Đã chuyển Thụ lý, chưa làm wizard", ma)
        if self.store.get(hs.key).trang_thai is TrangThai.DANG_HOAN_TAT:
            note = "Bị ngắt lúc Hoàn tất: kiểm tra tay trên MPLIS, không tự bấm lại"
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note, ma)
            self.emit(hs.key, "Cần kiểm tra", note, ma)
            return
        try:
            self.port.dien_chuyen_quyen(hs, ma)
            self.store.mark(hs.key, TrangThai.DANG_HOAN_TAT, "Đã điền wizard, sắp Hoàn tất", ma)
            self.port.hoan_tat(hs, ma)
        except SoPhatHanhTrung as e:
            note = f'Cần kiểm tra lại số phát hành "{e}"'
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note, ma)
            self.emit(hs.key, "Cần kiểm tra", note, ma)
            return
        except Exception as e:
            # wizard ghi dần lên máy chủ nên chạy lại có thể ghi lặp: để người kiểm tra
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, f"Wizard dở: {str(e).splitlines()[0][:150]}", ma)
            raise
        self._xac_nhan(hs, ma, note_ok)

    def _xac_nhan(self, hs: HoSo, ma: str, note_ok: str) -> None:
        lech = so_sanh(hs, self.port.doc(hs, ma))
        if lech:
            note = "; ".join(f"{k}: web='{w}' excel='{x}'" for k, (w, x) in lech.items())
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note, ma)
            self.emit(hs.key, "Cần kiểm tra", note, ma)
        else:
            self.store.mark(hs.key, TrangThai.THANH_CONG, note_ok, ma)
            self.emit(hs.key, "Thành công", note_ok, ma)
