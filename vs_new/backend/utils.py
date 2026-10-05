"""
utils.py
--------
Small shared helpers: JSON response building and simple input validation.
Kept dependency-free (standard library only), per project constraints.
"""

import json


class ValidationError(Exception):
    """Raised when incoming request data fails validation."""
    pass


def json_body_or_400(handler):
    """
    Read and parse the JSON body of a request.
    Raises ValidationError with a clear message on bad input.
    """
    try:
        length = int(handler.headers.get("Content-Length", 0))
    except (TypeError, ValueError):
        length = 0

    if length == 0:
        return {}

    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("Request body must be valid JSON.")

    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def require_fields(data, fields):
    """Ensure all given fields exist and are non-empty (0 is allowed)."""
    missing = []
    for f in fields:
        if f not in data or data[f] is None or data[f] == "":
            missing.append(f)
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def require_number(data, field, allow_negative=False, allow_zero=True):
    value = data.get(field)
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Field '{field}' must be a number.")
    if not allow_negative and num < 0:
        raise ValidationError(f"Field '{field}' cannot be negative.")
    if not allow_zero and num == 0:
        raise ValidationError(f"Field '{field}' cannot be zero.")
    return num


def send_json(handler, status_code, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def send_error_json(handler, status_code, message):
    send_json(handler, status_code, {"success": False, "error": message})


def send_success_json(handler, payload=None, status_code=200):
    result = {"success": True}
    if payload is not None:
        result["data"] = payload
    send_json(handler, status_code, result)


def get_bearer_token(handler):
    """Extract the token from 'Authorization: Bearer <token>', or None."""
    header = handler.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None
