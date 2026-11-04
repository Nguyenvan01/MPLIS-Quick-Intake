"""Mật khẩu MPLIS lưu trong Windows Credential Manager qua keyring, không ghi ra file."""
from __future__ import annotations

import keyring
from keyring.errors import PasswordDeleteError

SERVICE = "NhapPhieuMPLIS"


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE, username) if username else None


def set_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE, username, password)


def delete_password(username: str) -> None:
    try:
        keyring.delete_password(SERVICE, username)
    except PasswordDeleteError:
        pass
