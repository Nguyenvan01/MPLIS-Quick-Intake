"""Tra cứu hồ sơ tiếp nhận: tìm trùng (BR-04) và đọc lại để so khớp (BR-07)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from ...domain.chuan_hoa import ten_xa
from ...domain.models import HoSo
from ..port import so
from .tiep_nhan import TiepNhanPage


def chon_trung(ban_ghi: list[dict[str, Any]], hs: HoSo) -> str | None:
    """Số biên nhận của hồ sơ cùng thửa và cùng người nộp. MPLIS bỏ qua lọc giấy tờ nên phải tự so."""
    d = hs.dau
    thua = (str(d.thua.so_thua), str(d.thua.so_to))
    giay = {n.cccd for n in d.nguoi if n.cccd}
    for x in ban_ghi:
        co_thua = thua in {(str(t.get("soThua")), str(t.get("soTo"))) for t in x.get("thuaDat") or []}
        if co_thua and (x.get("nguoiNopDon") or {}).get("giayChungMinh") in giay:
            return str(x["soBienNhan"])
    return None


def gia_tri_doc(x: dict[str, Any]) -> dict[str, str]:
    t = (x.get("thuaDat") or [{}])[0]
    return {
        "so_to": str(t.get("soTo", "")), "so_thua": str(t.get("soThua", "")),
        "dien_tich": so(t.get("dienTich")), "cccd_nop": str((x.get("nguoiNopDon") or {}).get("giayChungMinh", "")),
    }


class TraCuuPage(TiepNhanPage):
    P = "tra_cuu"

    def _tim(self, xa: str, gia_tri: dict[str, str]) -> list[dict[str, Any]]:
        self.page.goto(urljoin(self.base_url, self.L.data[self.P]["duong_dan"]))
        self._cho()
        self._select2("select2_xa", xa, xa)
        for o, v in gia_tri.items():
            self._dat(self._el(o), v)
        # ponytail: chỉ đọc trang đầu 10 kết quả; thửa có trên 10 hồ sơ thì cần lật trang.
        with self.page.expect_response(lambda r: "AdvancedSearchHoSoTiepNhan" in r.url) as ri:
            self._el("nut_tim").click()
        self._cho()
        return ri.value.json().get("data") or []

    def tim(self, hs: HoSo) -> str | None:
        d = hs.dau
        xa = ten_xa(d.thua.dia_chi)
        if not xa:
            raise ValueError(f"Không tách được tên xã từ địa chỉ: {d.thua.dia_chi!r}")
        return chon_trung(self._tim(xa, {"o_so_thua": str(d.thua.so_thua), "o_so_to": str(d.thua.so_to)}), hs)

    def doc(self, hs: HoSo, ma_ho_so: str) -> dict[str, str]:
        kq = self._tim(ten_xa(hs.dau.thua.dia_chi) or "", {"o_so_bien_nhan": ma_ho_so})
        return gia_tri_doc(kq[0]) if len(kq) == 1 else {}
