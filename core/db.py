from __future__ import annotations

from typing import Any, Iterable

import streamlit as st

from core.auth import get_client


def select_rows(
    table: str,
    columns: str = "*",
    filters: Iterable[tuple[str, str, Any]] | None = None,
    order: str | None = None,
    desc: bool = False,
    limit: int | None = None,
) -> list[dict]:
    query = get_client().table(table).select(columns)
    for column, operation, value in filters or []:
        method = getattr(query, operation)
        query = method(column, value)
    if order:
        query = query.order(order, desc=desc)
    if limit:
        query = query.limit(limit)
    return query.execute().data or []


def insert_row(table: str, data: dict) -> dict | None:
    result = get_client().table(table).insert(data).execute()
    return result.data[0] if result.data else None


def insert_rows(table: str, data: list[dict]) -> list[dict]:
    return get_client().table(table).insert(data).execute().data or []


def update_rows(
    table: str, data: dict, filters: Iterable[tuple[str, str, Any]]
) -> list[dict]:
    query = get_client().table(table).update(data)
    for column, operation, value in filters:
        query = getattr(query, operation)(column, value)
    return query.execute().data or []


def delete_rows(
    table: str, filters: Iterable[tuple[str, str, Any]]
) -> list[dict]:
    query = get_client().table(table).delete()
    for column, operation, value in filters:
        query = getattr(query, operation)(column, value)
    return query.execute().data or []


def try_action(action, success: str) -> bool:
    try:
        action()
        st.success(success)
        return True
    except Exception as exc:
        message = str(exc)
        if len(message) > 400:
            message = message[:400] + "…"
        st.error(f"Could not save: {message}")
        return False

