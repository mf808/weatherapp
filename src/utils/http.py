import requests

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB


def safe_get(url: str, **kwargs) -> requests.Response:
    """GET with response size guard."""
    kwargs.setdefault("timeout", (5, 10))  # (connect, read)
    kwargs["stream"] = True
    resp = requests.get(url, **kwargs)
    resp.raise_for_status()
    _check_size(resp)
    # Read content so .json() works after stream
    _ = resp.content
    return resp


def safe_post(url: str, **kwargs) -> requests.Response:
    """POST with response size guard."""
    kwargs.setdefault("timeout", (5, 10))
    kwargs["stream"] = True
    resp = requests.post(url, **kwargs)
    resp.raise_for_status()
    _check_size(resp)
    _ = resp.content
    return resp


def _check_size(resp: requests.Response):
    cl = resp.headers.get("content-length")
    if cl and int(cl) > MAX_RESPONSE_BYTES:
        resp.close()
        raise ValueError(f"Response too large: {cl} bytes (max {MAX_RESPONSE_BYTES})")
