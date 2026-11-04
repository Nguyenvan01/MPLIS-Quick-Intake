"""Lệnh dòng lệnh cho dev / Claude Code (không cần giao diện).

  uv run python -m tiep_nhan kiem-tra <file.xlsx> [--gop ma_dau_vao]
  uv run python -m tiep_nhan locator-todo
  uv run python -m tiep_nhan kiem-locator --section login         (mở Edge thật)
  uv run python -m tiep_nhan chay-thu <file.xlsx>                  (mở Edge thật, KHÔNG lưu)
  uv run python -m tiep_nhan gui
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .domain.danh_muc import DanhMuc
from .domain.gom_ho_so import CheDoGom
from .infra.config import config_file


def _lo(args):
    from .core.batch import nap_lo
    return nap_lo(Path(args.file), DanhMuc.doc(config_file("danh_muc.toml")), CheDoGom(args.gop))


def cmd_kiem_tra(args) -> int:
    lo = _lo(args)
    print(f"{len(lo.ho_so)} hồ sơ")
    for hs in lo.ho_so:
        print(f"  - {hs.key}: {hs.mo_ta}")
    for v in lo.van_de:
        where = f"dòng {v.excel_row}" if v.excel_row else "file"
        print(f"[{'LỖI' if v.muc == 'loi' else 'cảnh báo'}] {v.ma} {where}: {v.noi_dung}")
    return 1 if lo.co_loi else 0


def cmd_locator_todo(args) -> int:
    from .mplis.locators import Locators
    todo = Locators.doc(config_file("locators.toml")).con_todo()
    print("\n".join(todo) or "Không còn locator TODO.")
    print(f"\nCòn {len(todo)} locator chưa lấy.")
    return 0


def _mplis():
    from .infra.config import Settings
    from .mplis.locators import Locators
    from .mplis.ui_adapter import PlaywrightMplis
    s = Settings.load()
    return s, PlaywrightMplis(s, Locators.doc(config_file("locators.toml")), DanhMuc.doc(config_file("danh_muc.toml")))


def _creds(s):
    from .infra import credentials
    user = s.username or input("Tài khoản MPLIS: ")
    return user, credentials.get_password(user) or getpass.getpass("Mật khẩu: ")


def cmd_kiem_locator(args) -> int:
    s, m = _mplis()
    with m:
        m.page.goto(s.mplis_url)
        if args.section != "login":
            m.dang_nhap(*_creds(s))
            input(f"Mở tới màn hình của [{args.section}] trong Edge rồi nhấn Enter… ")
        for path, kq in m.kiem_section(args.section):
            print(f"{'✓' if kq == 'OK' else '✗'} {path}: {kq}")
    return 0


def cmd_chay_thu(args) -> int:
    from .core.runner import Runner, RunOptions
    from .core.state import StateStore
    from .infra.config import STATE_DB
    lo = _lo(args)
    if lo.co_loi:
        print("File còn lỗi chặn — chạy 'kiem-tra' để xem.")
        return 1
    s, m = _mplis()
    with m:
        m.dang_nhap(*_creds(s))
        Runner(lo.ho_so, m, StateStore(STATE_DB), RunOptions(dry_run=True),
               on_event=lambda k, st, note, ma: print(f"{st:12} {k} {ma} {note}")).run()
    return 0


def main(argv: list[str] | None = None) -> int:
    from .infra.logging import setup
    setup()
    ap = argparse.ArgumentParser(prog="tiep_nhan")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("kiem-tra", "chay-thu"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--gop", choices=[c.value for c in CheDoGom], default=CheDoGom.MOI_DONG.value)
    sub.add_parser("locator-todo")
    p = sub.add_parser("kiem-locator")
    p.add_argument("--section", default="login")
    sub.add_parser("gui")
    args = ap.parse_args(argv)
    match args.cmd:
        case "kiem-tra": return cmd_kiem_tra(args)
        case "chay-thu": return cmd_chay_thu(args)
        case "locator-todo": return cmd_locator_todo(args)
        case "kiem-locator": return cmd_kiem_locator(args)
        case "gui" | None:
            from .app.main_window import main as gui
            return gui()
    return 2


if __name__ == "__main__":
    sys.exit(main())
