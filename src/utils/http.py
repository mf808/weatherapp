import requests

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
_CHUNK_SIZE = 64 * 1024


def safe_get(url: str, **kwargs) -> requests.Response:
    """GET with response size guard."""
    kwargs.setdefault("timeout", (5, 10))  # (connect, read)
    kwargs["stream"] = True
    resp = requests.get(url, **kwargs)
    resp.raise_for_status()
    _read_capped(resp)
    return resp


def safe_post(url: str, **kwargs) -> requests.Response:
    """POST with response size guard."""
    kwargs.setdefault("timeout", (5, 10))
    kwargs["stream"] = True
    resp = requests.post(url, **kwargs)
    resp.raise_for_status()
    _read_capped(resp)
    return resp


def _read_capped(resp: requests.Response):
    """Read the body enforcing MAX_RESPONSE_BYTES while streaming.

    The Content-Length header is checked first as a cheap fast-fail, but it can
    be absent (chunked encoding) or wrong, so the actual byte count is enforced
    during the read. Afterwards resp.content/.json() work as usual.
    """
    cl = resp.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > MAX_RESPONSE_BYTES:
        resp.close()
        raise ValueError(f"Response too large: {cl} bytes (max {MAX_RESPONSE_BYTES})")

    total = 0
    chunks = []
    for chunk in resp.iter_content(chunk_size=_CHUNK_SIZE):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            resp.close()
            raise ValueError(f"Response too large: exceeded {MAX_RESPONSE_BYTES} bytes while reading")
        chunks.append(chunk)
    resp._content = b"".join(chunks)
