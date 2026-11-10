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
    # chạy thật bắt buộc có số phát hành (wizard cần); file mẫu cố ý để trống ở vài dòng
    return [h if h.dau.thua.ma_phat_hanh else _voi_so(h, f"AA {i:08d}") for i, h in enumerate(gom(rows), 1)]


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
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_chay_thu_khong_chon_gcn(ho_so, store):
    port = FakeMplis()
    run(ho_so[:1], port, store, dry=True)
    assert port.goi == []


def test_ngat_sau_luu_van_chon_gcn_mot_lan(ho_so, store):
    port = FakeMplis(ngat_sau_luu={ho_so[0].key})
    run(ho_so[:1], port, store)
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao"]


def test_loi_khi_chon_gcn_chay_lai_khong_tao_ho_so_moi(ho_so, store):
    port = FakeMplis(loi_chon_gcn={ho_so[0].key})
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.DA_LUU and bg.ma_ho_so
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao"]
    assert store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_loi_khi_chuyen_khong_chon_gcn_lan_hai(ho_so, store):
    port = FakeMplis(loi_chuyen={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DA_CHON_GCN
    run(ho_so[:1], port, store)
    assert port.goi == ["luu", "chon_gcn", "chuyen_xu_ly", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao"]
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


def test_loi_khi_mo_du_thao_van_thanh_cong_co_ghi_chu(ho_so, store):
    port = FakeMplis(loi_du_thao={ho_so[0].key})
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.THANH_CONG and "Dự thảo" in bg.ghi_chu


def test_loi_khi_mo_du_thao_thi_khong_luu_du_thao(ho_so, store):
    port = FakeMplis(loi_du_thao={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert "luu_du_thao" not in port.goi


def test_loi_khi_luu_du_thao_van_thanh_cong_co_ghi_chu(ho_so, store):
    port = FakeMplis(loi_luu_du_thao={ho_so[0].key})
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.THANH_CONG and "Lưu dự thảo" in bg.ghi_chu


def test_loi_hoan_tat_khong_mo_du_thao(ho_so, store):
    port = FakeMplis(loi_hoan_tat={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert "mo_du_thao" not in port.goi


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
    assert port.goi == ["dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao"]
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
    assert all(b in tg[0] for b in ("mo_form", "dien", "luu", "chon_gcn", "chuyen_xu_ly", "dien_chuyen_quyen", "hoan_tat", "mo_du_thao", "luu_du_thao", "doc"))


def _voi_so(hs, so):
    d = hs.dong[0]
    return hs.model_copy(update={"dong": (d.model_copy(update={"thua": d.thua.model_copy(update={"ma_phat_hanh": so})}),) + hs.dong[1:]})


def _mo_ta(hs):
    return f"tờ {hs.dau.thua.so_to}, thửa {hs.dau.thua.so_thua}"


def test_so_da_cap_thi_hoi_so_moi_truoc_khi_tao_va_wizard_dung_so_moi(ho_so, store):
    ds = [_voi_so(ho_so[0], "AA 1"), _voi_so(ho_so[1], "AA 2"), ho_so[2]]
    hoi = []
    port = FakeMplis(so_da_cap_san={"AA 1"}, hoi_so_moi=lambda mo_ta, so: hoi.append((mo_ta, so)) or "ab 9")
    run(ds, port, store)
    assert hoi == [(_mo_ta(ds[0]), "AA 1")]
    assert port.so_da_quet == ["AA 1", "AA 2", ho_so[2].dau.thua.ma_phat_hanh, "AB 9"]  # quét cả lô trước, rồi kiểm số mới
    assert port.so_dung == {ds[0].key: "AB 9", ds[1].key: "AA 2", ds[2].key: ho_so[2].dau.thua.ma_phat_hanh}
    assert all(store.get(h.key).trang_thai is TrangThai.THANH_CONG for h in ds)


def test_so_da_cap_ma_bo_qua_thi_khong_tao_gi(ho_so, store):
    ds = [_voi_so(ho_so[0], "AA 1")]
    port = FakeMplis(so_da_cap_san={"AA 1"}, hoi_so_moi=lambda *_: None)
    ev = run(ds, port, store)
    bg = store.get(ds[0].key)
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and bg.ghi_chu == 'Cần kiểm tra lại số phát hành "AA 1"' and not bg.ma_ho_so
    assert port.so_lan_luu == 0 and [e[1] for e in ev] == ["Cần kiểm tra"]


def test_so_moi_cung_da_cap_thi_hoi_lai(ho_so, store):
    ds = [_voi_so(ho_so[0], "AA 1")]
    tra_loi = iter(["AB 1", "AB 2"])
    port = FakeMplis(so_da_cap_san={"AA 1", "AB 1"}, hoi_so_moi=lambda *_: next(tra_loi))
    run(ds, port, store)
    assert port.so_dung[ds[0].key] == "AB 2" and store.get(ds[0].key).trang_thai is TrangThai.THANH_CONG


def test_chay_thu_khong_quet_so_phat_hanh(ho_so, store):
    port = FakeMplis(so_da_cap_san={"AA 1"})
    run([_voi_so(ho_so[0], "AA 1")], port, store, dry=True)
    assert port.so_da_quet == []


def test_khong_quet_duoc_van_chay_tiep(ho_so, store):
    ds = [_voi_so(ho_so[0], "AA 1")]
    port = FakeMplis(loi_quet=True)
    run(ds, port, store)
    assert store.get(ds[0].key).trang_thai is TrangThai.THANH_CONG


def test_ho_so_da_co_ma_khong_quet_lai(ho_so, store):
    ds = [_voi_so(ho_so[0], "AA 1")]
    store.mark(ds[0].key, TrangThai.DA_CHUYEN_XU_LY, "dở", "HS-X")
    port = FakeMplis(so_da_cap_san={"AA 1"})
    run(ds, port, store)
    assert port.so_da_quet == []


def test_xoa_lich_su_lo_khong_xoa_trang_thai_ho_so(store):
    store.ghi_lo("a.xlsx", "Chạy thử", 1, "1 Chạy thử", ["k1"])
    store.ghi_lo("b.xlsx", "Chạy thật", 1, "1 Thành công", ["k2"])
    store.mark("k2", TrangThai.THANH_CONG, "xong", "HS-1")
    cu = store.ds_lo()
    store.xoa_lo(next(x["id"] for x in cu if x["file"] == "b.xlsx"))
    assert [x["file"] for x in store.ds_lo()] == ["a.xlsx"]
    assert store.get("k2").trang_thai is TrangThai.THANH_CONG  # trạng thái giữ lại để không tạo trùng
    store.xoa_het_lo()
    assert store.ds_lo() == [] and store.get("k2").ma_ho_so == "HS-1"



class _FakeGhiMoc(FakeMplis):
    """Ghi lại trạng thái trong store ngay lúc wizard bắt đầu."""
    store = None
    moc: list = []

    def dien_chuyen_quyen(self, hs, ma_ho_so):
        self.moc.append(self.store.get(hs.key).trang_thai)
        super().dien_chuyen_quyen(hs, ma_ho_so)


def test_chay_thu_khong_dong_toi_ho_so_dang_tao(ho_so, store):
    port = FakeMplis(ngat_sau_luu={ho_so[0].key})
    run(ho_so[:1], port, store)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.DANG_TAO
    port.goi.clear()
    ev = run(ho_so[:1], port, store, dry=True)
    assert port.goi == [] and store.get(ho_so[0].key).trang_thai is TrangThai.DANG_TAO
    assert ev[-1][1] == "Bỏ qua"


def test_chay_thu_thay_trung_khong_ghi_trang_thai(ho_so, store):
    port = FakeMplis()
    run(ho_so[:1], port, store)
    store.reset(ho_so[0].key)
    ev = run(ho_so[:1], port, store, dry=True)
    assert ev[-1][1] == "Đã có sẵn" and store.get(ho_so[0].key).trang_thai is TrangThai.CHO


def test_bat_dau_wizard_da_ghi_moc_de_bi_ngat_khong_lam_lai(ho_so, store):
    port = _FakeGhiMoc()
    port.store, port.moc = store, []
    run(ho_so[:1], port, store)
    assert port.moc == [TrangThai.DANG_HOAN_TAT]


def test_thieu_truong_wizard_bat_buoc_thi_khong_tao(ho_so, store):
    d = ho_so[0].dong[0]
    thieu = ho_so[0].model_copy(update={"dong": (d.model_copy(update={"nha": d.nha.model_copy(update={"dt_xay_dung": None})}),)})
    port = FakeMplis()
    ev = run([thieu], port, store)
    bg = store.get(thieu.key)
    assert port.so_lan_luu == 0 and bg.trang_thai is TrangThai.LOI and "Diện tích xây dựng" in bg.ghi_chu
    assert ev[-1][1] == "Lỗi"


class _FakeDocLech(FakeMplis):
    def doc(self, hs, ma_ho_so):
        return dict(super().doc(hs, ma_ho_so), cccd_nop="001234567890")


def test_ghi_chu_lech_khong_luu_cccd_day_du(ho_so, store):
    port = _FakeDocLech()
    run(ho_so[:1], port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.CAN_KIEM_TRA and "001234567890" not in bg.ghi_chu and "0012•••890" in bg.ghi_chu


def test_tai_khoan_khac_chu_hoa_van_la_cua_minh(ho_so, store):
    port = FakeMplis(tai_khoan_chuyen="LtMung.NNMT")
    Runner(ho_so[:1], port, store, RunOptions(dry_run=False, tai_khoan=" ltmung.nnmt ")).run()
    assert "dien_chuyen_quyen" in port.goi and store.get(ho_so[0].key).trang_thai is TrangThai.THANH_CONG


def test_quet_thua_truoc_khi_tao_thua_sai_thi_khong_tao(ho_so, store):
    port = FakeMplis(loi_thua={ho_so[0].key: "Diện tích trên MPLIS (107,5) khác Excel (84)"})
    ev = run(ho_so, port, store)
    bg = store.get(ho_so[0].key)
    assert bg.trang_thai is TrangThai.LOI and "107,5" in bg.ghi_chu and port.so_lan_luu == 2
    assert [e[1] for e in ev if e[0] == ho_so[0].key] == ["Lỗi"]
    assert all(store.get(h.key).trang_thai is TrangThai.THANH_CONG for h in ho_so[1:])


def test_khong_quet_duoc_thua_van_chay_nhu_cu(ho_so, store):
    port = FakeMplis(loi_kiem_thua=True)
    run(ho_so, port, store)
    assert port.so_lan_luu == 3


def test_chay_thu_khong_quet_thua(ho_so, store):
    port = FakeMplis(loi_thua={ho_so[0].key: "Không thấy thửa"})
    run(ho_so, port, store, dry=True)
    assert store.get(ho_so[0].key).trang_thai is TrangThai.CHO


def test_lich_su_luu_che_do_gom_va_sheet(store):
    store.ghi_lo("a.xlsx", "Chạy thử", 1, "1 Chạy thử", ["k1"], che_do_gom="theo_ma_dau_vao", sheet="Phieu chuyen")
    x = store.ds_lo()[0]
    assert x["che_do_gom"] == "theo_ma_dau_vao" and x["sheet"] == "Phieu chuyen"


def test_file_trang_thai_cu_chua_co_cot_che_do_gom_van_doc_duoc(tmp_path):
    import sqlite3
    db = tmp_path / "cu.sqlite3"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE lo (id INTEGER PRIMARY KEY AUTOINCREMENT, thoi_gian TEXT NOT NULL, file TEXT NOT NULL, che_do TEXT NOT NULL,"
              " so_ho_so INTEGER NOT NULL, tom_tat TEXT NOT NULL, keys TEXT NOT NULL)")
    c.execute("INSERT INTO lo(thoi_gian, file, che_do, so_ho_so, tom_tat, keys) VALUES ('2026-11-01T08:00:00','b.xlsx','Chạy thật',2,'2 Thành công','[]')")
    c.commit()
    c.close()
    x = StateStore(db).ds_lo()[0]
    assert x["file"] == "b.xlsx" and x["che_do_gom"] == "" and x["sheet"] == ""


def test_log_loi_khong_ghi_ho_ten(ho_so, store):
    dong = []
    sink = logger.add(dong.append, format="{message}")
    try:
        run(ho_so[:1], FakeMplis(loi_chuyen_quyen={ho_so[0].key}), store)
    finally:
        logger.remove(sink)
    assert dong and not any(n.ho_ten in m for m in dong for n in ho_so[0].dau.nguoi)
