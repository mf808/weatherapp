"""Fetches app secrets from Azure Key Vault at container start, then execs the
real process — this re-runs on every container start (including Watchtower
auto-restarts), which is the point: nothing on disk needs to be kept in sync.

If AZURE_CLIENT_ID isn't set (e.g. local `docker compose up`), this is a
no-op — secrets are expected to already be in the environment via the local
.env, same as before this existed.

creds.json is the one exception to "always fetch fresh": it holds Netatmo's
OAuth refresh token, which the app itself rewrites on every single fetch()
call (see src/datasources/netatmo.py — refresh_token rotates every time, not
just on expiry). So the vault's copy is a point-in-time disaster-recovery
seed, not a live mirror — overwriting an already-present creds.json here
would clobber a valid rotated token with a stale one and break Netatmo auth.
Only write it if the file doesn't already exist.

Network calls retry a bounded number of times with exponential backoff, to
ride out a brief Azure hiccup without failing the container over it. If all
attempts fail, the exception propagates and the process exits non-zero —
Docker's `restart: unless-stopped` then keeps retrying the container
indefinitely with its own backoff, so a longer outage still recovers on its
own once Azure is reachable again, it just becomes a visible restart loop
instead of a silent infinite wait inside this script.
"""
import os
import sys
import time

import requests

VAULT_NAME = "kv-basswarp-secrets"
VAULT_URL = f"https://{VAULT_NAME}.vault.azure.net"
SECRET_API_VERSION = "7.4"

MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1  # 1, 2, 4, 8, 16

SECRET_TO_ENV_VAR = {
    "nas-weatherapp-netatmo-client-id": "CLIENT_ID",
    "nas-weatherapp-netatmo-client-secret": "CLIENT_SECRET",
    "nas-weatherapp-netatmo-device-id": "DEVICE_ID",
    "nas-weatherapp-netatmo-outdoormodule-id": "OUTDOOMODULE_ID",
    "nas-weatherapp-owm-appid": "OPENWEATHERMAP_APPID",
}

CREDS_JSON_SECRET = "nas-weatherapp-creds-json"
CREDS_JSON_PATH = "/app/creds.json"


def _retry(func, *args, **kwargs):
    for attempt in range(MAX_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except requests.RequestException as e:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            wait = BACKOFF_BASE_SECONDS * (2 ** attempt)
            print(f"entrypoint: attempt {attempt + 1}/{MAX_ATTEMPTS} failed ({e}), retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)


def get_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://vault.azure.net/.default",
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_secret(token: str, name: str) -> str:
    resp = requests.get(
        f"{VAULT_URL}/secrets/{name}",
        params={"api-version": SECRET_API_VERSION},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["value"]


def main():
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")

    if not (tenant_id and client_id and client_secret):
        print("entrypoint: no AZURE_* bootstrap credential set, skipping Key Vault fetch", file=sys.stderr)
        os.execvp(sys.argv[1], sys.argv[1:])
        return

    token = _retry(get_token, tenant_id, client_id, client_secret)

    for secret_name, env_var in SECRET_TO_ENV_VAR.items():
        os.environ[env_var] = _retry(get_secret, token, secret_name)

    if os.path.exists(CREDS_JSON_PATH) and os.path.getsize(CREDS_JSON_PATH) > 0:
        print(f"entrypoint: {CREDS_JSON_PATH} already present, leaving as-is", file=sys.stderr)
    else:
        print(f"entrypoint: {CREDS_JSON_PATH} missing, seeding from vault", file=sys.stderr)
        value = _retry(get_secret, token, CREDS_JSON_SECRET)
        fd = os.open(CREDS_JSON_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(value)

    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
