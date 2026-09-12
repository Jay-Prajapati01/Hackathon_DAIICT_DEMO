"""Standardised JSON API response builders."""

from typing import Any, Optional

from flask import jsonify


def success_response(data: Any = None, status: int = 200, **extra):
    body = {"success": True}
    if isinstance(data, dict):
        body.update(data)
    elif data is not None:
        body["data"] = data
    body.update(extra)
    return jsonify(body), status


def error_response(message: str, status: int = 400, details: Optional[Any] = None, **extra):
    body = {"success": False, "error": message}
    if details is not None:
        body["details"] = details
    body.update(extra)
    return jsonify(body), status
