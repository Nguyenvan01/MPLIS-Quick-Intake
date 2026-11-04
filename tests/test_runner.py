"""Runner với MPLIS giả: chống trùng, bị ngắt sau Lưu, lệch khi tra cứu lại, chạy thử."""
import pytest

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
    Runner(ho_so, port, store, RunOptions(dry_run=dry), on_event=lambda *e: events.append(e)).run()
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
