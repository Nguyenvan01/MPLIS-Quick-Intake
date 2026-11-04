import pytest

from tiep_nhan.mplis.locators import ChuaCoLocator, Locators

from .conftest import CONFIG


def test_file_locators_hop_le():
    L = Locators.doc(CONFIG / "locators.toml")
    assert "login.o_tai_khoan" in L.con_todo()
    assert "them_moi_nhanh.mau_ma_ho_so" in L.con_todo()


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
