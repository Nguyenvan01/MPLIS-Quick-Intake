import pytest
from pathlib import Path
import tomllib

from tiep_nhan.mplis.locators import ChuaCoLocator, Locators

from .conftest import CONFIG


def test_file_locators_hop_le():
    L = Locators.doc(CONFIG / "locators.toml")
    assert L.con_todo() == []


def test_todo_bao_loi_ro_rang():
    L = Locators({"login": {"nut": {"by": "role", "role": "button", "name": "TODO"}}})
    with pytest.raises(ChuaCoLocator, match="login.nut"):
        L.spec("login.nut")
    assert not L.co("login.nut")


def test_dung_locator():
    calls = []

    class Scope:
        def get_by_role(self, role, name=None, exact=True):
            calls.append((role, name, exact))
            return self

        def nth(self, i):
            calls.append(("nth", i))
            return self

    L = Locators({"a": {"b": {"by": "role", "role": "button", "name": "Lưu", "nth": 1}}})
    L.get(Scope(), "a.b")
    assert calls == [("button", "Lưu", True), ("nth", 1)]


def test_tiep_nhan_khong_con_todo():
    L = Locators.doc(CONFIG / "locators.toml")
    assert L.section("tiep_nhan")
    assert L.section("chuyen_quyen")
    assert not [p for p in L.con_todo() if p.startswith(("tiep_nhan.", "tra_cuu.", "chuyen_quyen."))]


def test_moi_locator_co_du_khoa_theo_kieu():
    can = {"role": "role", "label": "text", "placeholder": "text", "text": "text", "test_id": "id", "css": "value"}

    def duyet(node):
        for v in node.values():
            if isinstance(v, dict) and "by" in v:
                assert can[v["by"]] in v, v
            elif isinstance(v, dict):
                duyet(v)

    duyet(tomllib.loads((Path(__file__).parents[1] / "config" / "locators.toml").read_text(encoding="utf-8")))
