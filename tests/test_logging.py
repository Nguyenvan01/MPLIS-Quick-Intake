from __future__ import annotations

from loguru import logger

import tiep_nhan.infra.logging as L


def test_traceback_khong_in_gia_tri_bien(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "LOG_DIR", tmp_path)
    L.setup()
    cccd = "001234567890"
    try:
        raise ValueError(cccd[:1])
    except ValueError:
        logger.exception("lỗi")
    logger.complete()
    logger.remove()
    assert cccd not in capsys.readouterr().err
    assert cccd not in "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.log"))


def test_noi_dung_loi_khong_lo_cccd(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "LOG_DIR", tmp_path)
    L.setup()
    so = "0012" + "34567890"  # ghép lúc chạy, vì traceback in cả dòng mã nguồn
    try:
        raise AssertionError(f'textbox: "{so}"')
    except AssertionError:
        logger.exception("lỗi")
    logger.complete()
    logger.remove()
    log = "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.log"))
    assert so not in capsys.readouterr().err + log and "AssertionError" in log

