"""Runner với MPLIS giả: chống trùng, bị ngắt sau Lưu, lệch khi tra cứu lại, chạy thử."""
import pytest
from loguru import logger

from tiep_nhan.core.runner import Runner, RunOptions
from tiep_nhan.core.state import StateStore, TrangThai
from tiep_nhan.domain.gom_ho_so import gom
from tiep_nhan.domain.rules import kiem_tra_file
from tiep_nhan.infra.excel_in import read_phieu
from tiep_nhan.mplis.fake import FakeMplis


@pytest.fixture
def ho_so(mau):
    rows, _ = kiem_tra_file(read_phieu(mau))
    return gom(rows)


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / "s.sqlite3")


def run(ho_so, port, store, dry=False):
    events = []
    Runner(ho_so, port, store, RunOptions(dry_run=dry, tai_khoan="toi"), on_event=lambda *e: events.append(e)).run()
    return events


def test_chay_that_thanh_cong(ho_so, store):
    port = FakeMplis()
    run(ho_so, port, store)
    assert port.so_lan_luu == 3
    assert all(store.get(h.key).trang_thai is TrangThai.THANH_CONG for h in ho_so)
    assert all(store.get(h.key).ma_ho_so for h in ho_so)


def test_chay_lai_khong_tao_trung(ho_so, store):
    port = FakeMplis()
    run(ho_so, port, store)
    run(ho_so, port, store)
    assert port.so_lan_luu == 3


def test_chay_thu_khong_luu(ho_so, store):
    port = FakeMplis()
    ev = run(ho_so, port, store, dry=True)
    assert port.so_lan_luu == 0
    assert [e[1] for e in ev if e[1] != "Đang chạy"] == ["Chạy thử"] * 3
    assert all(store.get(h.key).trang_thai is TrangThai.CHO for h in ho_so)


def test_da_co_san_tren_mplis(ho_so, store):
    port = FakeMplis()
    run(ho_so[:1], port, store)
    store.reset(ho_so[0].key)              # máy khác / mất file trạng thái
    run(ho_so[:1], port, store)
    assert port.so_lan_luu == 1
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DA_CO_SAN


def test_ngat_sau_khi_luu_roi_chay_lai(ho_so, store):
    port = FakeMplis(ngat_sau_luu={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DANG_TAO
    run(ho_so[:1], port, store)
    assert port.so_lan_luu == 1             # KHÔNG tạo lần hai
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_lech_khi_tra_cuu_lai(ho_so, store):
    port = FakeMplis(lech_khi_doc={ho_so[0].key})
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and "dien_tich" in bg.ghi_chu
    run(ho_so[:1], port, store)
    assert port.so_lan_luu == 1             # Cần kiểm tra thì không tự chạy lại


def test_sau_luu_chon_gcn_roi_chuyen_xu_ly(ho_so, store):
    port = FakeMplis()
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_chay_thu_khong_chon_gcn(ho_so, store):
    port = FakeMplis()
    run(ho_so[:1], port, store, dry=True)
    assert port.goi == []


def test_ngat_sau_luu_van_chon_gcn_mot_lan(ho_so, store):
    port = FakeMplis(ngat_sau_luu={ho_so[0].key})
    run(ho_so[:1], port, store)
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat"]


def test_loi_khi_chon_gcn_chay_lai_khong_tao_ho_so_moi(ho_so, store):
    port = FakeMplis(loi_chon_gcn={ho_so[0].key})
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.DA_LUU and bg.ma_ho_so
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_loi_khi_chuyen_khong_chon_gcn_lan_hai(ho_so, store):
    port = FakeMplis(loi_chuyen={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DA_CHON_GCN
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_chay_thu_bo_qua_ho_so_dang_do(ho_so, store):
    port = FakeMplis(loi_chon_gcn={ho_so[0].key})
    run(ho_so[:1], port, store)
    ev = run(ho_so[:1], port, store, dry=True)
    assert port.goi == ["luu", "chon_gcn"]
    assert ev[-1][1] == "Bỏ qua"


def test_loi_trong_wizard_can_nguoi_kiem_tra_khong_chay_lai(ho_so, store):
    port = FakeMplis(loi_chuyen_quyen={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.CAN_KIEM_TRA
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen"]


def test_loi_khi_hoan_tat_khong_bam_lai(ho_so, store):
    port = FakeMplis(loi_hoan_tat={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.CAN_KIEM_TRA
    run(ho_so[:1], port, store)
    assert port.goi.count("hoan_tat") == 1


def test_ngat_giua_hoan_tat_chuyen_can_kiem_tra(ho_so, store):
    store.mark(ho_so[0].key, TrangThai.DANG_HOAN_TAT, "giả lập tắt máy", "HS-9")
    port = FakeMplis()
    run(ho_so[:1], port, store)
    assert port.goi == []
    assert store.get(ho_so[0].key).trang_thai is TrangThai.CAN_KIEM_TRA


def test_chuyen_xong_chay_lai_chi_lam_wizard(ho_so, store):
    store.mark(ho_so[0].key, TrangThai.DA_CHUYEN_XU_LY, "giả lập", "HS-9")
    port = FakeMplis(da_co={"HS-9": {}})
    port.doc = lambda hs, ma: __import__("tiep_nhan.mplis.port", fromlist=["gia_tri_so_khop"]).gia_tri_so_khop(hs)
    run(ho_so[:1], port, store)
    assert port.goi == ["dien_chuyen_quyen", "hoan_tat"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_luu_ghi_nho_dia_chi_ho_so(ho_so, store):
    port = FakeMplis(loi_chon_gcn={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).duong_dan == "fake://HS-0001"


def test_chay_lai_mo_dung_ho_so_truoc_khi_di_tiep(ho_so, store):
    port = FakeMplis(loi_chon_gcn={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert port.mo_lai == []
    run(ho_so[:1], port, store)
    assert port.mo_lai == ["fake://HS-0001"]


def test_du_lieu_trang_thai_cu_van_doc_duoc(tmp_path):
    import sqlite3
    f = tmp_path / "cu.sqlite3"
    db = sqlite3.connect(f)
    db.execute("CREATE TABLE ho_so (key TEXT PRIMARY KEY, trang_thai TEXT NOT NULL, ma_ho_so TEXT NOT NULL DEFAULT '', ghi_chu TEXT NOT NULL DEFAULT '', so_lan INTEGER NOT NULL DEFAULT 0, cap_nhat TEXT NOT NULL)")
    db.execute("INSERT INTO ho_so VALUES ('k', 'da_luu', 'HS-1', '', 1, 'x')")
    db.commit(); db.close()
    s = StateStore(f)
    assert s.get("k").duong_dan == ""
    s.mark("k", TrangThai.DA_LUU, "", "HS-1", duong_dan="url")
    s.mark("k", TrangThai.DA_CHON_GCN, "", "HS-1")
    assert s.get("k").duong_dan == "url"


def test_chuyen_cho_nguoi_khac_thi_dung_va_khong_lam_lai(ho_so, store):
    port = FakeMplis(tai_khoan_chuyen="ndanh.tnmt")
    ev = run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DA_CHUYEN_NGUOI_KHAC
    assert "dien_chuyen_quyen" not in port.goi
    assert ev[-1][1:3] == ("Đã chuyển", "Đã chuyển cho ndanh.tnmt")
    assert run(ho_so[:1], port, store)[-1][1] == "Bỏ qua"
    assert port.so_lan_luu == 1 and port.goi.count("chuyen_xu_ly") == 1


def test_chua_khai_tai_khoan_thi_khong_tu_lam_wizard(ho_so, store):
    port = FakeMplis()
    Runner(ho_so[:1], port, store, RunOptions(dry_run=False)).run()
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DA_CHUYEN_NGUOI_KHAC
    assert "dien_chuyen_quyen" not in port.goi


def test_lich_su_lo_moi_nhat_truoc(store):
    store.ghi_lo("a.xlsx", "Chạy thử", 3, "3 Chạy thử", ["k1|to3|thua1"])
    store.ghi_lo("b.xlsx", "Chạy thật", 1, "1 Lỗi", ["k2"])
    ds = store.ds_lo()
    assert [x["file"] for x in ds] == ["b.xlsx", "a.xlsx"] and ds[1]["keys"] == ["k1|to3|thua1"]


def test_trung_so_phat_hanh_bao_can_kiem_tra_va_khong_bam_lai(ho_so, store):
    port = FakeMplis(so_phat_hanh_trung={ho_so[0].key})
    ev = run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and bg.ghi_chu == "Cần kiểm tra lại số phát hành \"AA 1\""
    assert ev[-1][1:3] == ("Cần kiểm tra", "Cần kiểm tra lại số phát hành \"AA 1\"")
    assert "hoan_tat" not in port.goi
    run(ho_so[:1], port, store)
    assert port.goi.count("dien_chuyen_quyen") == 1 and port.so_lan_luu == 1


def test_ghi_thoi_gian_tung_buoc(ho_so, store):
    dong: list[str] = []
    h = logger.add(lambda m: dong.append(str(m)), format="{message}")
    run(ho_so[:1], FakeMplis(), store)
    logger.remove(h)
    tg = [x for x in dong if x.startswith("Thời gian")]
    assert len(tg) == 1 and ho_so[0].key in tg[0]
    assert all(b in tg[0] for b in ("mo_form", "dien", "luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "doc"))
