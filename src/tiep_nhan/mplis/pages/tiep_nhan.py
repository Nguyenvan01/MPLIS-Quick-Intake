"""Luồng thật /dc/TiepNhanHoSo: tiếp nhận, chọn GCN cũ, chuyển người xử lý."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from playwright.sync_api import Locator, TimeoutError as PwTimeout, expect

from ...domain.chuan_hoa import ten_xa
from ...domain.models import DongPhieu, HoSo, Nguoi
from ..port import so
from .base import BasePage

def _chuan(s: str) -> str:
    return " ".join(s.split()).upper()


def khop_can_bo(o: list[str], ten: str) -> bool:
    """Dòng bảng người xử lý: khớp đúng tài khoản (cột 2) hoặc đuôi họ tên (cột 3)."""
    return len(o) >= 3 and (o[1].strip() == ten or _chuan(o[2]).endswith(_chuan(ten)))


def chon_ca_nhan(dong: list[list[str]], n: Nguoi) -> int | None:
    """Vị trí bản ghi khớp họ tên và năm sinh (cột 3 và 5). Nhiều bản ghi khớp mà giống hệt nhau trừ mã (một người bị nhập
    trùng trong danh bạ MPLIS) thì lấy bản đầu như người dùng; khác nhau thì None."""
    khop = [i for i, c in enumerate(dong) if _chuan(c[2]) == _chuan(n.ho_ten) and c[4].strip().endswith(str(n.nam_sinh))]
    if len({tuple(_chuan(x) for x in dong[i][2:]) for i in khop}) == 1:
        return khop[0]
    return None


def khop_dien_tich(tren_mplis: str, excel: float) -> bool:
    """Bảng thửa của MPLIS ghi số thập phân bằng dấu chấm, Excel đã đọc thành số."""
    return so(float(tren_mplis.replace(",", "."))) == so(excel)


def chu_khop_quy_trinh(cfg: dict, quy_trinh: str) -> str:
    """Chữ để chọn đúng một quy trình 1.012787: "1" đơn lẻ dưới 30 hồ sơ, "2" chủ đầu tư từ 30 hồ sơ trở lên."""
    if quy_trinh not in ("1", "2"):
        raise ValueError(f"Quy trình không hợp lệ: {quy_trinh!r}")
    return cfg["quy_trinh_khop_don_le"] if quy_trinh == "1" else cfg["quy_trinh_khop"]


class TiepNhanPage(BasePage):
    P = "tiep_nhan"
    quy_trinh = "2"  # PlaywrightMplis gán theo Cài đặt trước khi mở form

    def __init__(self, page, L, base_url: str):
        super().__init__(page, L)
        self.base_url = base_url
        self.url_ho_so: str | None = None

    def _el(self, ten: str, scope=None) -> Locator:
        return self.el(f"{self.P}.{ten}", scope)

    def _hien(self, ten: str, scope=None) -> Locator:
        return self._el(ten, scope).filter(visible=True)

    def _cho(self) -> None:
        expect(self._hien("overlay")).to_have_count(0)

    def _khong_co_hop(self, buoc: str) -> None:
        hop = self._hien("hop")
        if hop.count():
            raise RuntimeError(f"MPLIS thông báo ở bước {buoc}: {' '.join(hop.first.inner_text().split())[:200]}")

    def _select2(self, o: str, tim: str, khop: str) -> None:
        self._el(o).click()
        self._el("select2_tim").fill(tim)
        lua_chon = self._el("select2_lua_chon").filter(has_text=khop)
        expect(lua_chon).to_have_count(1)  # khớp nhiều hơn một thì dừng, không chọn đại
        lua_chon.click()
        self._cho()

    @staticmethod
    def _dat(o: Locator, value: str) -> None:
        # Gõ phím vào các ô số của MPLIS có lúc mất chữ số (1133 thành 113) nên đặt thẳng giá trị.
        o.evaluate("(e, v) => { e.value = v; e.dispatchEvent(new Event('change', { bubbles: true })); }", value)
        expect(o).to_have_value(value)

    def _dong_du_lieu(self, dong: Locator) -> Locator:
        return dong.filter(has=self._el("o_cot_2", self.page))  # bảng rỗng chỉ có một ô "Không tìm thấy"

    def _ve_ho_so(self) -> None:
        if not self.url_ho_so:
            raise RuntimeError("Không có địa chỉ hồ sơ trong phiên này, cần mở hồ sơ tay trên MPLIS")
        self.page.goto(self.url_ho_so)
        self._cho()

    # ----- phần A -----
    def mo(self) -> None:
        self.page.goto(urljoin(self.base_url, self.L.data[self.P]["duong_dan"]))
        expect(self._el("nut_luu")).to_be_visible()
        self._cho()
        expect(self._el("nut_luu")).to_have_text(re.compile(r"Lưu hồ sơ"))

    def dien(self, hs: HoSo) -> None:
        if len(hs.dong) != 1:
            raise NotImplementedError("Chưa xác minh luồng gộp nhiều dòng vào một hồ sơ")
        d = hs.dau
        xa = ten_xa(d.thua.dia_chi)
        if not xa:
            raise ValueError(f"Không tách được tên xã từ địa chỉ: {d.thua.dia_chi!r}")
        cfg = self.L.data[self.P]
        self._select2("select2_xa", xa, xa)
        self._select2("select2_quy_trinh", cfg["quy_trinh_tim"], chu_khop_quy_trinh(cfg, self.quy_trinh))
        self._khong_co_hop("chọn quy trình")
        self._chon_thua(d)
        self._dat_dia_chi(d)
        self._chon_nguoi_nop(d.nguoi_nop, tra_cuu=not d.nguoi_nop_excel)
        self._el("nhan_mot_cua").click()
        expect(self._el("o_mot_cua")).to_be_checked()
        self._khong_co_hop("điền người nộp")  # vd "Giấy tờ tùy thân đã tồn tại"

    def _chon_thua(self, d: DongPhieu) -> None:
        self._el("nut_tim_thua").click()
        m = self._el("modal_tim_thua")
        expect(m).to_be_visible()
        self._cho()
        self._dat(self._el("o_so_thua", m), str(d.thua.so_thua))
        self._dat(self._el("o_so_to", m), str(d.thua.so_to))
        with self.page.expect_response(lambda r: "AdvancedSearchThuaDat" in r.url):
            self._el("nut_tra_thua", m).click()
        self._cho()
        dong = self._dong_du_lieu(self._el("dong_thua", m))
        expect(dong).to_have_count(1)
        o = self._el("o_bang", dong)
        if o.nth(1).inner_text().strip() != str(d.thua.so_thua) or o.nth(2).inner_text().strip() != str(d.thua.so_to):
            raise RuntimeError("Dòng tìm được không đúng số thửa/tờ")
        dt = o.nth(3).inner_text().split()[0]
        if d.thua.dien_tich is not None and not khop_dien_tich(dt, d.thua.dien_tich):
            raise RuntimeError(f"Diện tích trên MPLIS ({dt}) khác Excel ({so(d.thua.dien_tich)})")
        dong.click()
        self._el("nut_chon_thua", m).click()
        expect(m).to_be_hidden()
        self._cho()

    def _dat_dia_chi(self, d: DongPhieu) -> None:
        hop = self._hien("hop").filter(has_text="cập nhật lại địa chỉ tài sản")
        try:  # chỉ hiện khi địa chỉ thửa khác địa chỉ đang có
            hop.wait_for(timeout=5000)
            self._el("hop_khong", hop).click()
            expect(hop).to_have_count(0)
        except PwTimeout:
            pass
        self._khong_co_hop("chọn thửa")
        o = self._el("o_dia_chi_ts")
        o.fill(d.dia_chi_tai_san)
        expect(o).to_have_value(d.dia_chi_tai_san)

    def _chon_nguoi_nop(self, n: Nguoi, tra_cuu: bool = True) -> None:
        if not (n.cccd and tra_cuu and self._tim_nguoi_nop(n)):
            o = self._el("o_ten_nop")
            o.fill(n.ho_ten)
            expect(o).to_have_value(n.ho_ten)
            if n.cccd:
                self._el("o_giay_nop").fill(n.cccd)
            if n.dia_chi:
                self._el("o_dia_chi_nop").fill(n.dia_chi)

    def _tim_nguoi_nop(self, n: Nguoi) -> bool:
        self._el("nut_tim_nguoi").click()
        m = self._el("modal_tim_nguoi")
        expect(m).to_be_visible()
        self._cho()
        self._dat(self._el("o_so_giay_to", m), n.cccd or "")
        with self.page.expect_response(lambda r: "AdvancedSearchCaNhan" in r.url):
            self._el("nut_tra_nguoi", m).click()
        self._cho()
        dong = self._dong_du_lieu(self._el("dong_nguoi", m))
        so_dong = dong.count()
        if so_dong == 0:
            self._el("nut_dong", m).last.click()
            expect(m).to_be_hidden()
            return False
        o = dong.evaluate_all("rs => rs.map(r => [...r.cells].map(c => c.innerText))")
        i = chon_ca_nhan(o, n)
        if i is None:
            raise RuntimeError(f"{so_dong} cá nhân cùng số giấy tờ, không xác định được bản ghi khớp họ tên và năm sinh")
        dong.nth(i).click()
        self._el("nut_chon_nguoi", m).click()
        expect(m).to_be_hidden()
        self._cho()
        self._khong_co_hop("chọn người nộp")
        expect(self._el("o_ten_nop")).not_to_have_value("")
        return True

    def luu(self) -> str:
        self._khong_co_hop("trước khi lưu")
        nut = self._el("nut_luu")
        expect(nut).to_have_text(re.compile(r"Lưu hồ sơ"))  # sau khi lưu, nút này thành "Cập nhật hồ sơ"
        nut.click()
        hop = self._hien("hop").filter(has_text="thêm mới hồ sơ")
        expect(hop).to_be_visible()
        with self.page.expect_response(lambda r: r.url.split("?")[0].endswith("/DangKyAjax/TiepNhanHoSo"), timeout=90_000) as ri:
            self._el("hop_dong_y", hop).click()
        kq = ri.value.json()
        if not kq.get("success"):
            raise RuntimeError(f"MPLIS không lưu được: {kq.get('message')}")
        self._cho()
        self.url_ho_so = self.page.url
        return str(kq["value"]["soBienNhan"])

    def huy(self) -> None:
        self.mo()  # form chưa lưu chỉ nằm trên trình duyệt, tải lại là mất

    # ----- đầu phần B -----
    def chon_gcn(self) -> None:
        m = self._el("popup_gcn")
        expect(m).to_be_visible()
        dong = self._el("dong_gcn", m)
        if dong.count() != 1:
            raise RuntimeError(f"Thửa có {dong.count()} GCN, cần người chọn")
        if "selected" not in (dong.get_attribute("class") or ""):  # bấm lần hai sẽ bỏ chọn
            self._el("o_chon_gcn", dong).click()
        expect(dong).to_have_class(re.compile(r"selected"))
        self._el("nut_chon_gcn", m).click()
        hop = self._hien("hop").filter(has_text="Cập nhật thành phần hồ sơ thành công")
        expect(hop).to_be_visible(timeout=60_000)
        self._el("hop_dong_y", hop).click()
        expect(hop).to_have_count(0)
        expect(m).to_be_hidden()  # popup tự đóng sau khi gắn GCN

    def _dong_can_bo(self, m: Locator, ten: str) -> list[Locator]:
        dong = self._el("dong_can_bo", m).filter(visible=True)
        expect(dong.first).to_be_visible()
        return [x for x in dong.all() if khop_can_bo(self._el("o_bang", x).all_inner_texts(), ten)]

    def _chon_dong(self, dong: Locator) -> None:
        """Bảng có thể vẽ lại ngay sau khi lọc làm mất lựa chọn; chỉ bấm khi chưa chọn vì bấm lại là bỏ chọn."""
        lop = self.L.data[self.P]["lop_da_chon"]
        da_chon = re.compile(rf"\b{lop}\b")
        for _ in range(5):
            if not da_chon.search(dong.get_attribute("class") or ""):
                dong.click()
            try:
                expect(dong).to_have_class(da_chon, timeout=1500)
                return
            except AssertionError:
                continue
        raise RuntimeError("Không chọn được dòng người xử lý")

    def chuyen_xu_ly(self, hs: HoSo) -> str:
        ten = hs.dau.can_bo
        if not ten:
            raise ValueError("Excel thiếu Cán bộ XL")
        self._ve_ho_so()
        self._el("nut_xu_ly").click()
        q = self._el("modal_quy_trinh")
        expect(q).to_be_visible()
        self._cho()
        o = self._el("o_da_xu_ly", q).filter(visible=True)
        expect(o).to_have_count(1)
        if not o.is_checked():
            o.click()
            expect(o).to_be_checked()
            self._khong_co_hop("đánh dấu đã xử lý")
        self._el("nut_chuyen", q).click()
        self._cho()
        m = self._hien("modal_chon_nguoi")
        expect(m).to_be_visible()
        buoc = self._el("cbb_buoc", m).evaluate("s => s.selectedOptions[0].text")
        if not buoc.strip().startswith(self.L.data[self.P]["buoc_chuyen"]):
            raise RuntimeError(f"Bước kế tiếp không như dự kiến: {buoc}")
        khop = self._dong_can_bo(m, ten)
        if not khop:  # MPLIS có thể trả danh sách cũ rút gọn (forceReload: false)
            with self.page.expect_response(lambda r: "GetUserInOuHasPermissionOnActivity" in r.url):
                self._el("tai_lai_can_bo", m).first.click()
            self._cho()
            khop = self._dong_can_bo(m, ten)
        if khop and ten.isascii() and " " not in ten:  # là tài khoản; ô lọc của MPLIS không tìm được họ tên có dấu
            self._el("o_loc_can_bo", m).press_sequentially(ten)
            expect(self._el("dong_can_bo", m).filter(visible=True)).to_have_count(1)
            khop = self._dong_can_bo(m, ten)
        if len(khop) != 1:
            raise RuntimeError(f"Tìm thấy {len(khop)} cán bộ khớp '{ten}'")
        nhan = self._el("o_bang", khop[0]).all_inner_texts()[1].strip()
        self._chon_dong(khop[0])
        nut = self._el("nut_thuc_thi", m)
        expect(nut).to_be_visible()
        with self.page.expect_response(lambda r: r.url.split("?")[0].endswith("/WorkflowAjax/executeCommand"), timeout=90_000) as ri:
            nut.click()
        if not ri.value.json().get("success"):
            raise RuntimeError("MPLIS không chuyển được hồ sơ")
        self._cho()
        return nhan
