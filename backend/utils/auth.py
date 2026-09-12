"""Role-based access helpers built on Flask-JWT-Extended."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def roles_required(*roles):
    """Require a valid JWT whose 'role' claim is one of *roles* ('admin' always allowed)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role == "admin" or role in roles:
                return fn(*args, **kwargs)
            return jsonify({"success": False, "error": f"Requires role: {', '.join(roles)}."}), 403

        return wrapper

    return decorator
