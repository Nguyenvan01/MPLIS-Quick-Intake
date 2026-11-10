"""MplisPort bằng Playwright + Chromium."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from loguru import logger
from playwright.sync_api import expect, sync_playwright

from ..domain.danh_muc import DanhMuc
from ..domain.models import HoSo
from ..infra.config import BROWSER_PROFILE, SHOT_DIR, TRACE_DIR, Settings
from . import api_ghi as G
from .locators import Locators
from .pages.chuyen_quyen import ChuyenQuyenPage
from .pages.tiep_nhan import TiepNhanPage
from ..domain.chuan_hoa import ten_xa
from .pages.tra_cuu import (API_TIM_THUA, API_TRA_HO_SO, TraCuuPage, chon_trung, doc_het_trang, doi_chieu_thua, gia_tri_doc,
                            tham_so_tim_ca_nhan, tham_so_tim_thua, tham_so_tra_ho_so)


def da_dang_nhap(url: str, base_url: str) -> bool:
    u = urlparse(url)
    return u.hostname == urlparse(base_url).hostname and u.path.startswith("/dc")


# Lệnh kiểm tra số phát hành mà chính wizard MPLIS gọi trước khi Lưu GCN. Chỉ đọc; kiểm tra trên toàn hệ thống, không phụ thuộc
# tỉnh/xã, chạy được khi chưa có hồ sơ; bắt buộc có loại GCN; phân biệt khoảng trắng (đã thử trên MPLIS ngày 10/11/2026).
API_KIEM_SO = "/dc/DangKyAjax/CheckExistThongTinGiayChungNhan"
THAN_KIEM_SO = {"tinhId": 0, "huyenId": 0, "xaId": 0, "soVaoSo": "VP", "maGiayChungNhan": "", "giayChungNhanId": 0, "tinhHinhDangKyId": 0,
                "hoSoTiepNhanId": "00000000-0000-0000-0000-000000000000", "loaiGiayChungNhanId": "97", "donViCap": "3"}
JS_KIEM_SO = """async ([url, ds]) => {
    const o = document.querySelector('input[name="__RequestVerificationToken"]');
    const ra = [];
    for (const b of ds) {
        const r = await fetch(url, {method: 'POST', credentials: 'include', body: JSON.stringify(b), headers: {
            'Content-Type': 'application/json; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest', '__RequestVerificationToken': o ? o.value : ''}});
        ra.push(r.ok ? await r.json() : {success: false, status: r.status});
    }
    return ra;
}"""


# Danh sách người nhận bước Thụ lý mà hộp "Chọn người xử lý" của MPLIS tải (lấy từ trace). forceReload=true vì có lúc
# trả thiếu (33 thay vì 125 tài khoản). Quy trình QD_1_012787_2 là quy trình mặc định đã chốt trong plan.md.
API_NGUOI_XU_LY = "/dc/DangKyAjax/GetUserInOuHasPermissionOnActivity"
def than_nguoi_xu_ly(quy_trinh: str) -> dict:
    """Quy trình _1 và _2 có người nhận bước Thụ lý khác nhau (vd. ltmung.nnmt không nhận được ở _1)."""
    return {"schemaCode": f"QD_1_012787_{quy_trinh}", "state": "ThuLyHoSo", "tinhId": 33, "xaId": 12031, "forceReload": True}


JS_GOI_FORM = """async ([url, ts]) => {
    const o = document.querySelector('input[name="__RequestVerificationToken"]');
    const r = await fetch(url, {method: 'POST', credentials: 'include', body: new URLSearchParams(ts), headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest',
        '__RequestVerificationToken': o ? o.value : ''}});
    return r.ok ? await r.json() : {success: false, status: r.status};
}"""


class KhongDungApi(RuntimeError):
    """Người dùng bật "Chạy hoàn toàn trên giao diện": các bước chỉ làm được bằng API (quét trước, danh sách người xử lý) bỏ qua."""


def _safe(s: str) -> str:
    return re.sub(r"[^\w.-]", "_", s)


class PlaywrightMplis:
    """Dùng: with PlaywrightMplis(settings, L, dm) as mplis: Runner(..., port=mplis).run()"""

    def __init__(self, settings: Settings, L: Locators, dm: DanhMuc):
        self.settings, self.L, self.dm = settings, L, dm
        self.hoi_so_moi = None  # giao diện gán vào để hỏi số mới khi MPLIS báo trùng
        self.ghi_api = False    # Worker bật khi chạy thật: Lưu, gắn GCN, chuyển Thụ lý gọi thẳng API (Đợt 1)
        self._cho_luu: dict | None = None
        self._da_luu: G.KetQuaLuu | None = None

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

    def _can_api(self) -> None:
        if self.settings.chay_giao_dien:
            raise KhongDungApi("Đang bật Chạy hoàn toàn trên giao diện nên không gọi API")

    def _goi_form(self, duong_dan: str, tham_so: list[tuple[str, str]]) -> dict:
        if not da_dang_nhap(self.page.url, self.settings.mplis_url):
            self.cho_dang_nhap()
        kq = self.page.evaluate(JS_GOI_FORM, [urljoin(self.settings.mplis_url, duong_dan), tham_so])
        if kq.get("success") is False or "data" not in kq:
            raise RuntimeError(f"MPLIS không trả lời {duong_dan.rsplit('/', 1)[-1]}: {kq.get('status', '')}")
        return kq

    def _goi_json(self, duong_dan: str, than: dict) -> dict:
        if not da_dang_nhap(self.page.url, self.settings.mplis_url):
            self.cho_dang_nhap()
        return self.page.evaluate(JS_KIEM_SO, [urljoin(self.settings.mplis_url, duong_dan), [than]])[0]

    def _dung_api_ghi(self) -> bool:
        return self.ghi_api and not self.settings.chay_giao_dien

    def _cua_ho_so(self, ma_ho_so: str) -> G.KetQuaLuu | None:
        """Kết quả Lưu bằng API của đúng hồ sơ này trong phiên; chạy lại hồ sơ dở từ phiên trước thì không có, dùng giao diện."""
        r = self._da_luu
        return r if self._dung_api_ghi() and r and r.so_bien_nhan == ma_ho_so else None

    def _chuan_bi_luu(self, hs: HoSo) -> dict:
        """Mọi tra cứu và kiểm tra giao diện làm trước khi Lưu, bằng API chỉ đọc. Lỗi ở đây thì chưa ghi gì lên MPLIS."""
        if len(hs.dong) != 1:
            raise NotImplementedError("Chưa xác minh luồng gộp nhiều dòng vào một hồ sơ")
        d, xa = hs.dau, self._xa_id(hs)
        ds = doc_het_trang(lambda s, n: self._goi_form(API_TIM_THUA, tham_so_tim_thua(xa, str(d.thua.so_thua), str(d.thua.so_to), s, n)))
        lech = doi_chieu_thua(ds, hs)
        if lech:
            raise RuntimeError(lech)
        thua = [r for r in ds if (str(r.get("soThuTuThua")), str(r.get("soHieuToBanDo"))) == (str(d.thua.so_thua), str(d.thua.so_to))]
        if len(thua) != 1:
            raise RuntimeError(f"MPLIS có {len(thua)} thửa {d.thua.so_to}/{d.thua.so_thua}")
        G.kiem_ngan_chan(self._goi_json(G.API_NGAN_CHAN_THUA, G.than_ngan_chan_thua(thua[0], xa)), "chọn thửa")
        n = d.nguoi_nop
        nguoi = {"hoTen": n.ho_ten, "giayChungMinh": n.cccd or "", "diachi": n.dia_chi or ""}
        if n.cccd and not d.nguoi_nop_excel:  # có cột Người nộp thì gõ thẳng như giao diện (BR-09)
            r = G.chon_ban_ghi_ca_nhan(doc_het_trang(lambda s, k: self._goi_form(G.API_TIM_CA_NHAN, tham_so_tim_ca_nhan(n.cccd or "", s, k))), n)
            if r:  # ponytail: nhánh này chưa có lượt thật để đối chiếu (13 trace đều gõ tay); lần đầu chạy API cần xem lại hồ sơ
                nguoi.update(hoTen=str(r.get("hoTen") or n.ho_ten), diachi=str(r.get("diaChi") or n.dia_chi or ""), caNhanId=str(r["caNhanId"]))
        ma = f"QD_1_012787_{self.settings.quy_trinh}"
        bay_gio = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:00.000Z")
        return G.than_luu(hs, xa_id=xa, thua=thua[0], nguoi_nop=nguoi,
                          quy_trinh=(ma, G.ten_quy_trinh(self._goi_json(G.API_QUY_TRINH, {}), ma)), ngay_tiep_nhan=bay_gio,
                          ngay_hen_tra=G.doc_ngay_hen_tra(self._goi_json(G.API_NGAY_HEN_TRA, {"ngayTiepNhan": bay_gio, "schemaCode": [ma]})))

    def _xa_id(self, hs: HoSo) -> int:
        v = self.dm.anh_xa("xa", ten_xa(hs.dau.thua.dia_chi))
        if not (v and v.isdigit()):
            raise ValueError(f"Chưa có mã xã cho địa chỉ {hs.dau.thua.dia_chi!r}")
        return int(v)

    def _tra_ho_so(self, hs: HoSo, **loc: str) -> list[dict]:
        xa = self._xa_id(hs)
        return doc_het_trang(lambda s, n: self._goi_form(API_TRA_HO_SO, tham_so_tra_ho_so(xa, start=s, length=n, **loc)))

    def tim_trung(self, hs: HoSo) -> str | None:
        """Tra trùng bằng API, đọc đủ mọi trang; API lỗi hoặc người dùng chọn chạy trên giao diện thì tra qua giao diện."""
        if self.settings.chay_giao_dien:
            return self.tra_cuu.tim(hs)
        try:
            ds = self._tra_ho_so(hs, so_thua=str(hs.dau.thua.so_thua), so_to=str(hs.dau.thua.so_to))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Tra trùng bằng API không được, chuyển sang giao diện: {type(e).__name__}: {str(e)[:150]}")
            return self.tra_cuu.tim(hs)
        return chon_trung(ds, hs)

    def kiem_thua(self, hs: HoSo) -> str | None:
        self._can_api()
        xa, t = self._xa_id(hs), hs.dau.thua
        return doi_chieu_thua(doc_het_trang(lambda s, n: self._goi_form(API_TIM_THUA, tham_so_tim_thua(xa, str(t.so_thua), str(t.so_to), s, n))), hs)

    def so_da_cap(self, ds: list[str]) -> set[str]:
        self._can_api()
        if not da_dang_nhap(self.page.url, self.settings.mplis_url):
            self.cho_dang_nhap()
        kq = self.page.evaluate(JS_KIEM_SO, [urljoin(self.settings.mplis_url, API_KIEM_SO), [dict(THAN_KIEM_SO, soPhatHanh=s) for s in ds]])
        if not all(x.get("success") for x in kq):
            raise RuntimeError(f"MPLIS không trả lời lệnh kiểm tra số phát hành: {next(x for x in kq if not x.get('success'))}")
        return {s for s, x in zip(ds, kq) if x.get("isExistSoPhatHanh")}

    def ds_nguoi_xu_ly(self) -> dict[str, str]:
        self._can_api()
        if not da_dang_nhap(self.page.url, self.settings.mplis_url):
            self.cho_dang_nhap()
        kq = self.page.evaluate(JS_KIEM_SO, [urljoin(self.settings.mplis_url, API_NGUOI_XU_LY), [than_nguoi_xu_ly(self.settings.quy_trinh)]])[0]
        if not kq.get("success"):
            raise RuntimeError(f"MPLIS không trả danh sách người xử lý: {kq}")
        return {x["UserName"]: (x.get("FullName") or "").strip() for x in kq.get("value") or [] if x.get("UserName")}

    def mo_form(self) -> None:
        self._cho_luu = None
        if self._dung_api_ghi():
            return
        self.form.quy_trinh = self.settings.quy_trinh
        self.form.mo()

    def dien(self, hs: HoSo) -> None:
        if self._dung_api_ghi():
            self._cho_luu = self._chuan_bi_luu(hs)
            return
        self.form.dien(hs)

    def chup(self, key: str) -> str:
        path = SHOT_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{_safe(key)}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    def huy(self) -> None:
        self.form.huy()

    def luu(self) -> str:
        if not self._dung_api_ghi():
            return self.form.luu()
        than, self._cho_luu, self._da_luu = self._cho_luu, None, None
        if than is None:
            raise RuntimeError("Chưa chuẩn bị dữ liệu Lưu")
        r = G.doc_ket_qua_luu(self._goi_json(G.API_LUU, than))
        self._da_luu = r
        self.form.url_ho_so = urljoin(self.settings.mplis_url, G.DUONG_DAN_HO_SO + r.id)
        return r.so_bien_nhan

    def chon_gcn(self, hs: HoSo, ma_ho_so: str) -> None:
        r = self._cua_ho_so(ma_ho_so)
        if not r:
            return self.form.chon_gcn()
        if len(r.gcn) != 1:
            raise RuntimeError(f"Thửa có {len(r.gcn)} GCN, cần người chọn")
        g = r.gcn[0]
        G.kiem_ngan_chan(self._goi_json(G.API_NGAN_CHAN_GCN, {"giayChungNhanIds": [g["giayChungNhanId"]], "hoSoTiepNhanId": r.id}), "chọn GCN")
        kq = self._goi_json(G.API_THEM_GCN, {"hoSoTiepNhanId": r.id, "guids": [g["Id"]]})
        if not (kq.get("success") and kq.get("value") is True):
            raise RuntimeError(f"MPLIS không gắn được GCN vào hồ sơ: {kq.get('message') or kq.get('status') or ''}")

    def chuyen_xu_ly(self, hs: HoSo, ma_ho_so: str) -> str:
        r = self._cua_ho_so(ma_ho_so)
        if not r:
            return self.form.chuyen_xu_ly(hs)
        if not hs.dau.can_bo:
            raise ValueError("Excel thiếu Cán bộ XL")
        tk = G.chon_tai_khoan(self.ds_nguoi_xu_ly(), hs.dau.can_bo)
        kq = self._goi_json(G.API_DA_XU_LY, {"hoSoTiepNhanId": r.id, "actionCode": "XuLyHoSo", "daXuLy": True})
        if not kq.get("success"):
            raise RuntimeError(f"MPLIS không đánh dấu được đã xử lý: {kq.get('message') or kq.get('status') or ''}")
        kq = self._goi_json(G.API_CHUYEN, G.than_chuyen(self.settings.quy_trinh, r.id, r.process_id, tk))
        if not (kq.get("success") and kq.get("value") is True):
            raise RuntimeError(f"MPLIS không chuyển được cho {tk}: {kq.get('message') or kq.get('status') or ''}")
        return tk

    def dien_chuyen_quyen(self, hs: HoSo, ma_ho_so: str) -> None:
        self.wizard.url_ho_so = self.form.url_ho_so
        self.wizard.hoi_so_moi = self.hoi_so_moi
        self.wizard.dien(hs)

    def hoan_tat(self, hs: HoSo, ma_ho_so: str) -> None:
        self.wizard.hoan_tat()

    def mo_du_thao(self, hs: HoSo, ma_ho_so: str) -> None:
        self.wizard.url_ho_so = self.form.url_ho_so
        self.wizard.mo_du_thao()

    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]:
        if self.settings.chay_giao_dien:
            return self.tra_cuu.doc(hs, ma_ho_so)
        try:
            kq = self._tra_ho_so(hs, so_bien_nhan=ma_ho_so)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Tra cứu lại bằng API không được, chuyển sang giao diện: {type(e).__name__}: {str(e)[:150]}")
            return self.tra_cuu.doc(hs, ma_ho_so)
        return gia_tri_doc(kq[0]) if len(kq) == 1 else {}

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
