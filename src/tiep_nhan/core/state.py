"""Trạng thái từng hồ sơ trong SQLite (xem sơ đồ máy trạng thái ở docs/kien-truc.md)."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class TrangThai(StrEnum):
    CHO = "cho"
    DANG_TAO = "dang_tao"          # đã bấm Lưu, chưa xác nhận — lần sau PHẢI tìm trùng trước
    DA_LUU = "da_luu"              # đã có mã hồ sơ, chưa chọn GCN — chạy lại đi tiếp, không tạo mới
    DA_CHON_GCN = "da_chon_gcn"    # đã gắn GCN, chưa chuyển người xử lý
    DA_CHUYEN_XU_LY = "da_chuyen_xu_ly"  # đã chuyển bước Thụ lý, chưa làm wizard
    DA_CHUYEN_NGUOI_KHAC = "da_chuyen_nguoi_khac"  # đã chuyển cho tài khoản khác, tool xong phần việc
    DANG_HOAN_TAT = "dang_hoan_tat"      # sắp bấm Hoàn tất: bị ngắt thì người kiểm tra, không bấm lại
    THANH_CONG = "thanh_cong"      # đã tạo và tra cứu lại khớp
    DA_CO_SAN = "da_co_san"        # MPLIS đã có hồ sơ trùng, không tạo mới
    CAN_KIEM_TRA = "can_kiem_tra"  # đã tạo nhưng tra cứu lại lệch
    LOI = "loi"                    # lỗi trước khi bấm Lưu

    @property
    def ket_thuc(self) -> bool:
        return self in (TrangThai.THANH_CONG, TrangThai.DA_CO_SAN, TrangThai.DA_CHUYEN_NGUOI_KHAC)


@dataclass
class BanGhi:
    key: str
    trang_thai: TrangThai
    ma_ho_so: str
    ghi_chu: str
    so_lan: int
    cap_nhat: str
    duong_dan: str = ""            # địa chỉ trang hồ sơ trên MPLIS, để chạy lại sau khi tắt tool


class StateStore:
    def __init__(self, path: Path | str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS ho_so (
                   key TEXT PRIMARY KEY, trang_thai TEXT NOT NULL, ma_ho_so TEXT NOT NULL DEFAULT '',
                   ghi_chu TEXT NOT NULL DEFAULT '', so_lan INTEGER NOT NULL DEFAULT 0, cap_nhat TEXT NOT NULL)"""
        )
        if "duong_dan" not in [c[1] for c in self._db.execute("PRAGMA table_info(ho_so)")]:  # file trạng thái bản cũ
            self._db.execute("ALTER TABLE ho_so ADD COLUMN duong_dan TEXT NOT NULL DEFAULT ''")
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS lo (
                   id INTEGER PRIMARY KEY AUTOINCREMENT, thoi_gian TEXT NOT NULL, file TEXT NOT NULL,
                   che_do TEXT NOT NULL, so_ho_so INTEGER NOT NULL, tom_tat TEXT NOT NULL, keys TEXT NOT NULL)"""
        )
        self._db.commit()

    def ghi_lo(self, file: str, che_do: str, so_ho_so: int, tom_tat: str, keys: list[str]) -> None:
        with self._lock:
            self._db.execute("INSERT INTO lo(thoi_gian, file, che_do, so_ho_so, tom_tat, keys) VALUES (?,?,?,?,?,?)",
                             (datetime.now().isoformat(timespec="seconds"), file, che_do, so_ho_so, tom_tat, json.dumps(keys)))
            self._db.commit()

    def ds_lo(self) -> list[dict]:
        with self._lock:
            r = self._db.execute("SELECT thoi_gian, file, che_do, so_ho_so, tom_tat, keys FROM lo ORDER BY id DESC").fetchall()
        return [dict(zip(("thoi_gian", "file", "che_do", "so_ho_so", "tom_tat"), x[:5]), keys=json.loads(x[5])) for x in r]

    def get(self, key: str) -> BanGhi:
        with self._lock:
            r = self._db.execute("SELECT * FROM ho_so WHERE key=?", (key,)).fetchone()
        if not r:
            return BanGhi(key, TrangThai.CHO, "", "", 0, "")
        return BanGhi(r[0], TrangThai(r[1]), r[2], r[3], r[4], r[5], r[6])

    def mark(self, key: str, st: TrangThai, ghi_chu: str = "", ma_ho_so: str | None = None,
             duong_dan: str | None = None) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self._db.execute(
                """INSERT INTO ho_so(key, trang_thai, ma_ho_so, ghi_chu, so_lan, cap_nhat, duong_dan)
                   VALUES (?, ?, COALESCE(?, ''), ?, 1, ?, COALESCE(?, ''))
                   ON CONFLICT(key) DO UPDATE SET trang_thai=excluded.trang_thai,
                     ma_ho_so=COALESCE(?, ho_so.ma_ho_so), ghi_chu=excluded.ghi_chu,
                     so_lan=ho_so.so_lan+1, cap_nhat=excluded.cap_nhat,
                     duong_dan=COALESCE(?, ho_so.duong_dan)""",
                (key, st.value, ma_ho_so, ghi_chu, now, duong_dan, ma_ho_so, duong_dan),
            )
            self._db.commit()

    def reset(self, key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM ho_so WHERE key=?", (key,))
            self._db.commit()
