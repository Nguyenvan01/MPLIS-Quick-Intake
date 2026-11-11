"""Vòng lặp xử lý hồ sơ. Chỉ biết MplisPort, không biết Playwright → test được bằng FakeMplis."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from loguru import logger

from ..domain.chuan_hoa import chuan_ma_phat_hanh
from ..domain.models import HoSo
from ..infra.logging import che_so_trong_chu
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


def _doi_so_phat_hanh(hs: HoSo, so: str) -> HoSo:
    d = hs.dong[0]
    thua = d.thua.model_copy(update={"ma_phat_hanh": so})
    return hs.model_copy(update={"dong": (d.model_copy(update={"thua": thua}),) + hs.dong[1:]})


class _DoGio:
    """Bọc port để cộng dồn thời gian các bước gọi lên MPLIS (task 3.5)."""
    BUOC = ("tim_trung", "mo_form", "dien", "luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao", "doc")
    NHAN = {"tim_trung": "Đang tra trùng trên MPLIS…", "dien": "Đang kiểm tra trước khi lưu…", "luu": "Đang lưu hồ sơ…",
            "chon_gcn": "Đang gắn GCN…", "chuyen_xu_ly": "Đang chuyển Thụ lý…", "dien_chuyen_quyen": "Đang điền wizard chuyển quyền…",
            "hoan_tat": "Đang hoàn tất…", "mo_du_thao": "Đang mở Dự thảo GCN…", "luu_du_thao": "Đang tạo QR và lưu dự thảo…",
            "doc": "Đang tra cứu lại để đối chiếu…"}

    def __init__(self, port: MplisPort, bao: Callable[[str], None] = lambda _: None):
        self._port = port
        self.bao = bao  # phần API chạy ngầm không hiện gì trên Chromium: báo bước để người dùng biết tool không đứng
        self.giay: dict[str, float] = {}

    def __getattr__(self, ten: str):
        ham = getattr(self._port, ten)
        if ten not in self.BUOC:
            return ham

        def do(*a, **k):
            if ten in self.NHAN:
                self.bao(self.NHAN[ten])
            dau = perf_counter()
            try:
                return ham(*a, **k)
            finally:
                self.giay[ten] = self.giay.get(ten, 0) + perf_counter() - dau
        return do


class Runner:
    def __init__(self, ho_so: list[HoSo], port: MplisPort, store: StateStore, opts: RunOptions,
                 on_event: EventFn | None = None, should_stop: Callable[[], bool] = lambda: False):
        self.ho_so, self.store, self.opts = list(ho_so), store, opts  # bản sao: quét số có thể thay hồ sơ bằng bản đã đổi số
        self.emit = on_event or (lambda *a: None)
        self._dang = ""  # key hồ sơ đang chạy, để báo bước đúng dòng
        self.port = _DoGio(port, lambda nhan: self._dang and self.emit(self._dang, "Đang chạy", nhan, ""))
        self.should_stop = should_stop

    def run(self) -> None:
        if not self.opts.dry_run:
            self._quet_thua()
            self._quet_so_phat_hanh()
        for hs in self.ho_so:
            if self.should_stop():
                logger.warning("Dừng theo yêu cầu người dùng")
                break
            self.port.giay.clear()
            self.mot_ho_so(hs)
            if self.port.giay:
                logger.info(f"Thời gian {hs.key}: " + ", ".join(f"{k} {v:.1f}s" for k, v in self.port.giay.items()))

    def _so_da_cap(self, ds: list[str]) -> set[str]:
        try:
            return self.port.so_da_cap(ds)
        except Exception as e:  # noqa: BLE001 — không quét được thì wizard vẫn tự báo khi trùng số
            logger.warning(f"Không kiểm tra được số phát hành trên MPLIS: {type(e).__name__}: {str(e)[:150]}")
            return set()

    def _quet_thua(self) -> None:
        """Đối chiếu thửa và diện tích trên MPLIS cho cả lô trước khi tạo hồ sơ nào; sai thì báo Lỗi, không tạo."""
        bo_qua: set[str] = set()
        for hs in self.ho_so:
            if self.store.get(hs.key).trang_thai not in (TrangThai.CHO, TrangThai.LOI):
                continue
            try:
                van_de = self.port.kiem_thua(hs)
            except Exception as e:  # noqa: BLE001 — không quét được thì vẫn chạy như cũ, bước điền form tự kiểm diện tích
                logger.warning(f"Không quét được thửa trên MPLIS: {type(e).__name__}: {str(e)[:150]}")
                return
            if van_de:
                self.store.mark(hs.key, TrangThai.LOI, van_de)
                self.emit(hs.key, "Lỗi", van_de, "")
                bo_qua.add(hs.key)
        self.ho_so = [hs for hs in self.ho_so if hs.key not in bo_qua]

    def _quet_so_phat_hanh(self) -> None:
        """Số phát hành đã cấp thì hỏi số mới trước khi tạo hồ sơ, để wizard không kẹt ở bước GCN với hồ sơ đã lưu."""
        chua_tao = [i for i, hs in enumerate(self.ho_so)
                    if hs.dau.thua.ma_phat_hanh and self.store.get(hs.key).trang_thai in (TrangThai.CHO, TrangThai.LOI)]
        if not chua_tao:
            return
        da_cap = self._so_da_cap([self.ho_so[i].dau.thua.ma_phat_hanh for i in chua_tao])
        bo_qua: set[str] = set()
        for i in chua_tao:
            hs = self.ho_so[i]
            so = hs.dau.thua.ma_phat_hanh
            trung = so in da_cap
            while trung:
                moi = self.port.hoi_so_moi(f"tờ {hs.dau.thua.so_to}, thửa {hs.dau.thua.so_thua}", so) if self.port.hoi_so_moi else None
                if not moi:
                    note = f'Cần kiểm tra lại số phát hành "{so}"'
                    self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note)
                    self.emit(hs.key, "Cần kiểm tra", note, "")
                    bo_qua.add(hs.key)
                    break
                so = chuan_ma_phat_hanh(moi)
                trung = so in self._so_da_cap([so])
            if not trung and so != hs.dau.thua.ma_phat_hanh:
                self.ho_so[i] = _doi_so_phat_hanh(hs, so)
        self.ho_so = [hs for hs in self.ho_so if hs.key not in bo_qua]  # đã báo Cần kiểm tra, không báo thêm "Bỏ qua"

    def mot_ho_so(self, hs: HoSo) -> None:
        self._dang = hs.key
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
        if self.opts.dry_run and (dang_do or bg.trang_thai is TrangThai.DANG_TAO):  # DANG_TAO có thể đã có trên MPLIS
            self.emit(hs.key, "Bỏ qua", "Hồ sơ đã lưu dở trên MPLIS, chạy thử không đụng tới", bg.ma_ho_so)
            return
        thieu = [ten for ten, v in (("Số phát hành", hs.dau.thua.ma_phat_hanh), ("Diện tích xây dựng", hs.dau.nha.dt_xay_dung),
                                    ("Diện tích sàn", hs.dau.nha.dt_san)) if not v]
        if thieu and not self.opts.dry_run and bg.trang_thai in (TrangThai.CHO, TrangThai.LOI):
            note = f"Thiếu {', '.join(thieu)}: wizard bắt buộc có nên không tạo hồ sơ"
            self.store.mark(hs.key, TrangThai.LOI, note)
            self.emit(hs.key, "Lỗi", note, "")
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
                        if not self.opts.dry_run:  # chạy thử không ghi trạng thái
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
            dong = str(e).splitlines()[0][:200] if str(e) else ""
            # RuntimeError là lý do tool/MPLIS viết sẵn bằng tiếng Việt: không kèm tên lớp; lỗi khác giữ tên để dễ tra
            msg = che_so_trong_chu(dong if isinstance(e, RuntimeError) and dong else f"{type(e).__name__}: {dong}")
            if not self.opts.dry_run and self.store.get(hs.key).trang_thai not in (TrangThai.DANG_TAO, TrangThai.CAN_KIEM_TRA, *MOC_SAU_LUU):
                self.store.mark(hs.key, TrangThai.LOI, msg)
            logger.exception(f"{hs.key}: lỗi (trace: {trace})")  # không ghi họ tên ra log
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
            if not self.opts.tai_khoan or (nhan or "").strip().casefold() != self.opts.tai_khoan.strip().casefold():
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
            # ghi mốc trước khi vào wizard: bị tắt ngang thì lần sau chuyển người kiểm tra, không làm lại wizard từ đầu
            self.store.mark(hs.key, TrangThai.DANG_HOAN_TAT, "Đang làm wizard, chưa Hoàn tất", ma)
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
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, che_so_trong_chu(f"Wizard dở: {str(e).splitlines()[0][:150]}"), ma)
            raise
        try:
            self.port.mo_du_thao(hs, ma)
        except Exception as e:
            # đã Hoàn tất trên MPLIS rồi: không mở được dự thảo thì chỉ ghi chú, người dùng mở tay
            note_ok = f"{note_ok}; chưa mở được Dự thảo GCN: {che_so_trong_chu(str(e).splitlines()[0][:100])}"
        else:
            try:
                self.port.luu_du_thao(hs, ma)
            except Exception as e:
                note_ok = f"{note_ok}; chưa tạo QR/Lưu dự thảo: {che_so_trong_chu(str(e).splitlines()[0][:100])}"
        self._xac_nhan(hs, ma, note_ok)

    def _xac_nhan(self, hs: HoSo, ma: str, note_ok: str) -> None:
        lech = so_sanh(hs, self.port.doc(hs, ma))
        if lech:
            note = che_so_trong_chu("; ".join(f"{k}: web='{w}' excel='{x}'" for k, (w, x) in lech.items()))
            self.store.mark(hs.key, TrangThai.CAN_KIEM_TRA, note, ma)
            self.emit(hs.key, "Cần kiểm tra", note, ma)
        else:
            self.store.mark(hs.key, TrangThai.THANH_CONG, note_ok, ma)
            self.emit(hs.key, "Thành công", note_ok, ma)
