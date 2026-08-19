"""Small, local-only JSON store for Clark voucher records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STORE_PATH = DATA_DIR / "vouchers.json"
_LOCK = Lock()


class StaleVoucherError(Exception):
    """Raised when an older browser tab tries to overwrite a newer save."""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _empty_store() -> dict:
    return {"schema_version": 1, "vouchers": {}}


def _read_unlocked() -> dict:
    if not STORE_PATH.exists():
        return _empty_store()
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Clark could not read {STORE_PATH}. The file was left unchanged so it can be recovered."
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("vouchers"), dict):
        raise RuntimeError(f"Clark's voucher file has an unexpected format: {STORE_PATH}")
    return data


def _write_unlocked(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STORE_PATH.with_name(f".{STORE_PATH.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, STORE_PATH)


def list_vouchers(query: str = "") -> list[dict]:
    with _LOCK:
        vouchers = list(_read_unlocked()["vouchers"].values())
    needle = query.casefold().strip()
    if needle:
        vouchers = [
            voucher for voucher in vouchers
            if needle in str(voucher.get("voucher_number", "")).casefold()
            or needle in str(voucher.get("payee", "")).casefold()
        ]
    return sorted(vouchers, key=lambda item: item.get("updated_at", ""), reverse=True)


def get_voucher(voucher_id: str) -> dict | None:
    with _LOCK:
        voucher = _read_unlocked()["vouchers"].get(voucher_id)
    return deepcopy(voucher) if voucher else None


def get_vouchers(voucher_ids: list[str]) -> list[dict]:
    with _LOCK:
        records = _read_unlocked()["vouchers"]
        return [deepcopy(records[voucher_id]) for voucher_id in voucher_ids if voucher_id in records]


def save_voucher(values: dict, voucher_id: str = "", expected_version: int | None = None) -> dict:
    with _LOCK:
        store = _read_unlocked()
        records = store["vouchers"]
        current = records.get(voucher_id) if voucher_id else None
        if current and expected_version is not None and int(current.get("record_version", 1)) != expected_version:
            raise StaleVoucherError(voucher_id)

        timestamp = _now()
        if current:
            saved = deepcopy(current)
            saved.update(values)
            saved["updated_at"] = timestamp
            saved["record_version"] = int(current.get("record_version", 1)) + 1
        else:
            voucher_id = uuid4().hex
            saved = {
                "id": voucher_id,
                **values,
                "created_at": timestamp,
                "updated_at": timestamp,
                "record_version": 1,
                "print_history": [],
            }
        records[voucher_id] = saved
        _write_unlocked(store)
        return deepcopy(saved)


def add_print_revision(voucher_id: str, revision: dict) -> dict:
    with _LOCK:
        store = _read_unlocked()
        saved = store["vouchers"].get(voucher_id)
        if not saved:
            raise KeyError(voucher_id)
        saved.setdefault("print_history", []).append(revision)
        saved["updated_at"] = _now()
        saved["record_version"] = int(saved.get("record_version", 1)) + 1
        _write_unlocked(store)
        return deepcopy(saved)


