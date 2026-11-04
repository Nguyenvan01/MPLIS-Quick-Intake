"""Đọc config/locators.toml và dựng Playwright Locator.

Mỗi locator là một bảng TOML, ví dụ:
    nut_luu = { by = "role", role = "button", name = "Lưu" }
    o_so_to = { by = "label", text = "Số tờ" }
    o_x     = { by = "css", value = "#txtSoTo" }          # chỉ khi không có nhãn/vai trò
Các khóa: by = role|label|placeholder|text|test_id|css ; exact (mặc định true) ; nth (tùy chọn).
Giá trị "TODO" nghĩa là CHƯA LẤY — gọi tới sẽ báo ChuaCoLocator, không đoán.
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class ChuaCoLocator(RuntimeError):
    pass


class Locators:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    @classmethod
    def doc(cls, path: Path) -> "Locators":
        return cls(tomllib.loads(path.read_text(encoding="utf-8")))

    def spec(self, path: str) -> dict[str, Any]:
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ChuaCoLocator(f"Không có locator '{path}' trong locators.toml")
            node = node[part]
        if not isinstance(node, dict) or "by" not in node:
            raise ChuaCoLocator(f"'{path}' không phải một locator")
        if any(v == "TODO" for v in node.values()):
            raise ChuaCoLocator(f"Locator '{path}' chưa lấy (TODO) — xem docs/locators/README.md")
        return node

    def co(self, path: str) -> bool:
        """True nếu locator đã được khai báo và không còn TODO (dùng cho phần tùy chọn)."""
        try:
            self.spec(path)
            return True
        except ChuaCoLocator:
            return False

    def section(self, path: str) -> dict[str, dict[str, Any]]:
        node: Any = self.data
        for part in path.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return {k: v for k, v in node.items() if isinstance(v, dict) and "by" in v}

    def con_todo(self) -> list[str]:
        out: list[str] = []

        def walk(node: dict, prefix: str) -> None:
            for k, v in node.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict) and "by" in v:
                    if any(x == "TODO" for x in v.values()):
                        out.append(p)
                elif isinstance(v, dict):
                    walk(v, p)
                elif v == "TODO":
                    out.append(p)

        walk(self.data, "")
        return out

    def get(self, scope, path: str):
        """scope = Page | Locator | FrameLocator."""
        s = self.spec(path)
        exact = s.get("exact", True)
        match s["by"]:
            case "role":
                loc = scope.get_by_role(s["role"], name=s.get("name"), exact=exact)
            case "label":
                loc = scope.get_by_label(s["text"], exact=exact)
            case "placeholder":
                loc = scope.get_by_placeholder(s["text"], exact=exact)
            case "text":
                loc = scope.get_by_text(s["text"], exact=exact)
            case "test_id":
                loc = scope.get_by_test_id(s["id"])
            case "css":
                loc = scope.locator(s["value"])
            case other:
                raise ChuaCoLocator(f"'{path}': by='{other}' không hỗ trợ")
        return loc.nth(s["nth"]) if "nth" in s else loc
