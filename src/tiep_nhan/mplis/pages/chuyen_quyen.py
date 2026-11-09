"""Wizard "Chuyển quyền trọn giấy": thêm chủ mới, Lâu dài, thêm nhà, GCN mới, Hoàn tất."""
from __future__ import annotations

import re

from playwright.sync_api import Locator, TimeoutError as PwTimeout, expect

from ...domain.chuan_hoa import chuan_ma_phat_hanh
from ...domain.danh_muc import DanhMuc
from ...domain.models import DongPhieu, HoSo, Nguoi
from ..port import SoPhatHanhTrung
from .tiep_nhan import TiepNhanPage, _chuan


class ChuyenQuyenPage(TiepNhanPage):
    P = "chuyen_quyen"
    hoi_so_moi = None  # (mô tả thửa, số bị trùng) -> số mới

    def __init__(self, page, L, base_url: str, dm: DanhMuc, nguoi_ky: str):
        super().__init__(page, L, base_url)
        self.dm, self.nguoi_ky = dm, nguoi_ky

    def _wiz(self) -> Locator:
        return self._hien("wizard")

    def _muc(self, ten: str) -> None:
        muc = self._hien("menu_muc").filter(has_text=re.compile(rf"^\s*{ten}\s*$"))
        expect(muc).to_have_count(1)
        muc.click()
        self._cho()

    def _da_map(self, bang: str, gia_tri: str | None) -> str:
        v = self.dm.anh_xa(bang, gia_tri)
        if not v:
            raise ValueError(f"[BR-05] {bang} '{gia_tri}' chưa ánh xạ")
        return v

    def _chon_dung(self, ten: str, scope: Locator, gia_tri: str) -> None:
        self._el(ten, scope).filter(visible=True).first.click()
        self._el("select2_tim").fill(gia_tri)
        o = self._el("select2_lua_chon")
        expect(o.filter(has_text=gia_tri).first).to_be_visible()
        vi_tri = [i for i, t in enumerate(o.all_inner_texts()) if _chuan(t) == _chuan(gia_tri)]
        if not vi_tri:
            raise RuntimeError(f"Không có lựa chọn '{gia_tri}'")
        o.nth(vi_tri[0]).click()  # danh mục MPLIS có mục trùng chữ (vd "Cấp 3"), các mục này như nhau

    def _o(self, ten: str, scope: Locator) -> Locator:
        return self._el(ten, scope).filter(visible=True).first

    # ----- Bước 1 -----
    def _mo(self) -> None:
        self._ve_ho_so()
        self._el("nut_xu_ly").click()
        q = self._el("modal_quy_trinh")
        expect(q).to_be_visible()
        self._cho()
        tac_vu = self._el("dong_tac_vu", q).filter(has_text="Chuyển quyền trọn giấy")
        expect(tac_vu).to_have_count(1)
        self._el("lk_xu_ly", tac_vu).click()
        expect(self._wiz()).to_be_visible()
        self._cho()

    def _sau(self, den_buoc: int) -> None:
        self._el("nut_buoc_sau", self._wiz()).click()
        expect(self._el("buoc_hien", self._wiz()).filter(has_text=f"Bước {den_buoc}")).to_be_visible(timeout=90_000)
        self._cho()

    def _dien_nguoi(self, n: Nguoi) -> None:
        f = self._hien("modal_ca_nhan")
        expect(f).to_be_visible()
        self._cho()
        ten = self._o("o_ho_ten", f)
        ten.fill(n.ho_ten)
        self._dat(self._o("o_nam_sinh", f), str(n.nam_sinh or ""))  # fill() chỉ giữ chữ số cuối
        self._o("o_so_giay_to", f).fill(n.cccd or "")
        self._o("o_dia_chi", f).fill(n.dia_chi or "")
        nam = self._o("o_gioi_tinh", f)
        if nam.is_checked() != (n.gioi_tinh == "Nam"):
            nam.click()
        self._o("nut_luu", f).click()
        self._dong_y_neu_trung_giay_to()
        expect(self._hien("modal_ca_nhan")).to_have_count(0)
        self._khong_co_hop("lưu người nhận")

    def _dong_y_neu_trung_giay_to(self) -> None:
        hop = self._hien("hop").filter(has_text="Giấy tờ tùy thân đã tồn tại")
        try:
            hop.wait_for(timeout=4000)
        except PwTimeout:
            return
        self._el("hop_dong_y", hop).click()
        self._cho()

    def _them_chu(self, d: DongPhieu) -> None:
        self._o("nut_them_chu", self._wiz()).click()
        if not d.la_vo_chong:
            self._muc("Cá nhân")
            self._dien_nguoi(d.nguoi[0])
            return
        self._muc("Vợ chồng")
        m = self._hien("modal_vo_chong")
        expect(m).to_be_visible()
        for i, n in enumerate(d.chong_vo):
            self._el("nut_cong_nguoi", m).filter(visible=True).nth(i).click()
            self._dien_nguoi(n)
        self._el("nut_luu_vo_chong", m).click()
        expect(self._hien("modal_vo_chong")).to_have_count(0)
        self._khong_co_hop("lưu vợ chồng")

    # ----- Bước 3 -----
    def _chon_thua(self) -> None:
        self._el("neo_cay", self._wiz()).filter(visible=True).filter(has_text="Thửa đất").first.click()

    def _sua_thoi_han(self, d: DongPhieu) -> None:
        self._chon_thua()
        self._o("nut_sua_ts", self._wiz()).click()
        m = self._hien("modal_tai_san").last
        expect(m).to_be_visible()
        self._cho()
        self._el("dong_mdsd", m).first.click()
        v = self._da_map("thoi_han", d.thua.thoi_han)
        o = self._o("o_thoi_han", m)
        o.fill(v)
        expect(o).to_have_value(v)
        self._el("nut_luu_thua", m).click()
        expect(self._hien("modal_tai_san")).to_have_count(0)
        self._khong_co_hop("lưu thời hạn")

    def _them_nha(self, d: DongPhieu) -> None:
        self._chon_thua()
        self._o("nut_them_ts", self._wiz()).click()
        self._muc("Nhà riêng lẻ")
        m = self._hien("modal_tai_san").last
        expect(m).to_be_visible()
        self._cho()
        self._chon_dung("sel_loai_nha", m, self._da_map("loai_nha", d.nha.loai_nha))
        self._chon_dung("sel_cap_nha", m, self._da_map("cap_nha", d.nha.cap_nha))
        self._chon_dung("sel_ket_cau", m, self._da_map("ket_cau", d.nha.ket_cau))
        self._o("o_so_nha", m).fill(d.so_nha)
        self._o("o_dt_xay_dung", m).fill(f"{d.nha.dt_xay_dung:g}")
        o = self._o("o_dt_su_dung", m)
        o.click()
        o.press_sequentially(f"{d.nha.dt_san:g}", delay=120)  # fill() làm ô này trống
        self._o("o_so_nha", m).click()
        expect(o).to_have_value(re.compile(rf"^{re.escape(f'{d.nha.dt_san:g}')}"))
        self._el("mo_dia_chi", m).first.click()
        chinh = self._o("o_dia_chi_chinh", m)
        expect(chinh).to_be_visible()
        if not chinh.is_checked():
            chinh.click()
        self._el("nut_luu_nha", m).click()
        expect(self._hien("modal_tai_san")).to_have_count(0)
        self._khong_co_hop("lưu nhà")

    def _luu_dang_ky(self) -> None:
        w = self._wiz()
        for ten in ("o_quyen_su_dung", "o_quyen_so_huu"):
            o = self._o(ten, w)
            if not o.is_checked():
                o.click()
        with self.page.expect_response(lambda r: "ValidateThongTinDangKyJson" in r.url) as ri:
            self._o("nut_luu_dang_ky", w).click()
        if not ri.value.json().get("success"):
            raise RuntimeError("MPLIS không chấp nhận thông tin đăng ký")
        self._cho()
        self._khong_co_hop("lưu đăng ký")

    def _dat_so_phat_hanh(self, m: Locator, so: str) -> None:
        sp = self._o("o_so_phat_hanh", m)
        sp.fill(so)
        sp.press("Tab")
        self._cho()
        if _chuan(sp.input_value()) != _chuan(so):  # video từng lệch số ở ô gợi ý
            raise RuntimeError(f"Ô số phát hành bị đổi thành {sp.input_value()}")

    def _them_gcn(self, d: DongPhieu) -> None:
        if not d.thua.ma_phat_hanh:
            raise ValueError("Thiếu số phát hành GCN mới")
        w = self._wiz()
        self._el("tab_gcn", w).filter(visible=True).click()
        self._cho()
        self._o("nut_them_gcn", w).click()
        m = self._hien("modal_gcn")
        expect(m).to_be_visible()
        self._cho()
        self._el("o_vpdk", m).check(force=True)
        expect(self._el("o_so_vao_so", m).first).to_have_value("VP")
        so = d.thua.ma_phat_hanh
        self._dat_so_phat_hanh(m, so)
        self._o("o_nguoi_ky", m).fill(self.nguoi_ky)
        neo = self._el("neo_cay", m).filter(visible=True)
        for i in range(neo.count()):
            if "jstree-checked" not in (neo.nth(i).get_attribute("class") or ""):  # tick cha tự tick con
                self._el("o_tick_cay", neo.nth(i)).click()
        expect(self._el("neo_chua_tick", m).filter(visible=True)).to_have_count(0)
        while True:
            self._el("nut_luu_gcn", m).click()
            self._cho()
            trung = self._hien("hop").filter(has_text=self.L.data[self.P]["so_ph_trung"])
            if not trung.count():
                break
            moi = self.hoi_so_moi(f"tờ {d.thua.so_to}, thửa {d.thua.so_thua}", so) if self.hoi_so_moi else None
            if not moi:
                raise SoPhatHanhTrung(so)
            self._el("hop_dong_y", trung).click()
            expect(trung).to_have_count(0)
            so = chuan_ma_phat_hanh(moi)
            self._dat_so_phat_hanh(m, so)  # hộp GCN vẫn mở, các ô khác giữ nguyên nên không phải đi lại wizard
        self._khong_co_hop("lưu GCN")
        expect(self._hien("modal_gcn")).to_have_count(0)

    # ----- Port -----
    def dien(self, hs: HoSo) -> None:
        d = hs.dau
        self._mo()
        self._them_chu(d)
        self._sau(2)
        self._sau(3)
        self._sua_thoi_han(d)
        self._them_nha(d)
        self._luu_dang_ky()
        self._them_gcn(d)
        self._sau(4)

    def hoan_tat(self) -> None:
        self._khong_co_hop("trước Hoàn tất")
        with self.page.expect_response(lambda r: r.url.split("?")[0].endswith("/DangKyAjax/UpdateTacVuDaXuLy"), timeout=120_000) as ri:
            self._el("nut_hoan_tat", self._wiz()).filter(visible=True).click()
        if not ri.value.json().get("success"):
            raise RuntimeError("MPLIS không hoàn tất được hồ sơ")
        self._cho()
