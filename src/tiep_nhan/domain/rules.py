"""Quy tắc nghiệp vụ BR-01 … BR-09 (xem docs/nghiep-vu.md)."""
from __future__ import annotations

from pydantic import ValidationError

from ..infra.excel_in import RawRow, ReadResult
from .chuan_hoa import chuan_ten, cccd_khop, to_cccd
from .models import DongPhieu, NhaO, Nguoi, ThuaDat, VanDe

NEN_CO = {  # BR-06: thiếu thì cảnh báo, không chặn
    "ma_phat_hanh": "Mã phát hành",
    "thoi_han": "Thời hạn sử dụng đất",
    "mau_nha": "Mẫu nhà",
    "phan_loai_duong": "Phân loại đường",
    "can_bo": "Cán bộ XL",
}


def _loi_de_doc(err: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'dòng'}: {e['msg']}" for e in err.errors())


def _nguoi(v: dict, prefix: str, vai_tro: str, notes: list[tuple[str, str]]) -> Nguoi | None:
    if not v.get(f"{prefix}_ho_ten"):
        if any(v.get(f"{prefix}_{k}") for k in ("nam_sinh", "cccd", "dia_chi")):
            raise ValueError(f"Cột {vai_tro} có CCCD/năm sinh/địa chỉ nhưng thiếu họ tên")
        return None
    cccd, cccd_notes = to_cccd(v.get(f"{prefix}_cccd"), v.get(f"{prefix}_nam_sinh"))
    notes += [("BR-02", f"{vai_tro}: {n}") for n in cccd_notes]
    n = Nguoi(vai_tro=vai_tro, ho_ten=v[f"{prefix}_ho_ten"], nam_sinh=v.get(f"{prefix}_nam_sinh"),
              cccd=cccd, dia_chi=v.get(f"{prefix}_dia_chi"))
    if n.cccd:
        notes += [("BR-02", f"{vai_tro}: {x}") for x in cccd_khop(n.cccd, n.nam_sinh, vai_tro)]
    return n


def kiem_tra_dong(raw: RawRow) -> tuple[DongPhieu | None, list[VanDe]]:
    v, r = raw.values, raw.excel_row
    notes: list[tuple[str, str]] = []
    try:
        nguoi = tuple(x for x in (_nguoi(v, "ong", "Ông", notes), _nguoi(v, "ba", "Bà", notes)) if x)
        if not nguoi:
            return None, [VanDe(excel_row=r, muc="loi", ma="BR-01", noi_dung="Không có người nhận nào có họ tên")]
        dong = DongPhieu(
            excel_row=r, stt=v.get("stt"), ma_dau_vao=v.get("ma_dau_vao"),
            ben_chuyen=v.get("ben_chuyen"), xac_nhan=v.get("xac_nhan"), nguoi=nguoi,
            thua=ThuaDat(so_to=v.get("so_to"), so_thua=v.get("so_thua"), dien_tich=v.get("dien_tich"),
                         ma_phat_hanh=v.get("ma_phat_hanh"), thoi_han=v.get("thoi_han"),
                         dia_chi=v.get("dia_chi_thua")),
            nha=NhaO(**{k: v.get(k) for k in NhaO.model_fields}),
            mau_nha=v.get("mau_nha"), phan_loai_duong=v.get("phan_loai_duong"), can_bo=v.get("can_bo"),
            nguoi_nop_excel=v.get("nguoi_nop"),
        )
    except ValidationError as e:
        return None, [VanDe(excel_row=r, muc="loi", ma="BR-03", noi_dung=_loi_de_doc(e))]
    except ValueError as e:
        return None, [VanDe(excel_row=r, muc="loi", ma="BR-02", noi_dung=str(e))]

    issues = [VanDe(excel_row=r, muc="canh_bao", ma=ma, noi_dung=t) for ma, t in notes]
    for field, label in NEN_CO.items():
        val = getattr(dong.thua, field, None) if field in ("ma_phat_hanh", "thoi_han") else getattr(dong, field)
        if val in (None, ""):
            issues.append(VanDe(excel_row=r, muc="canh_bao", ma="BR-06", noi_dung=f"Thiếu {label}"))
    if dong.nguoi_nop_excel and chuan_ten(dong.nguoi_nop_excel) not in {chuan_ten(n.ho_ten) for n in dong.nguoi}:
        issues.append(VanDe(excel_row=r, muc="loi", ma="BR-09", noi_dung="Cột Người nộp không khớp người nhận nào của dòng"))
        return None, issues
    if dong.la_vo_chong and dong.nguoi[0].gioi_tinh == dong.nguoi[1].gioi_tinh:
        issues.append(VanDe(excel_row=r, muc="loi", ma="BR-09",
                            noi_dung=f"Hai người nhận đều là {dong.nguoi[0].gioi_tinh}, không xác định được vợ/chồng"))
        return None, issues
    return dong, issues


def kiem_tra_file(result: ReadResult) -> tuple[list[DongPhieu], list[VanDe]]:
    issues = [VanDe(excel_row=0, muc="canh_bao", ma="BR-08", noi_dung=w) for w in result.warnings]
    rows: list[DongPhieu] = []
    seen: dict[tuple[int, int], int] = {}
    seen_ph: dict[str, int] = {}
    for raw in result.rows:
        dong, row_issues = kiem_tra_dong(raw)
        issues += row_issues
        if dong is None:
            continue
        k = (dong.thua.so_to, dong.thua.so_thua)
        if k in seen:  # BR-03: tờ + thửa là duy nhất; giữ dòng đầu, loại dòng sau, báo nhưng không chặn cả lô
            issues.append(VanDe(excel_row=raw.excel_row, muc="canh_bao", ma="BR-03",
                                noi_dung=f"Trùng tờ/thửa {k[0]}/{k[1]} với dòng {seen[k]} — đã loại khỏi lô"))
            continue
        ph = dong.thua.ma_phat_hanh
        if ph and ph in seen_ph:  # BR-03
            issues.append(VanDe(excel_row=raw.excel_row, muc="loi", ma="BR-03",
                                noi_dung=f"Trùng số phát hành {ph} với dòng {seen_ph[ph]} — bỏ qua"))
            continue
        seen[k] = raw.excel_row
        if ph:
            seen_ph[ph] = raw.excel_row
        rows.append(dong)
    return rows, issues
