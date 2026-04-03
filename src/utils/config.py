import os


def resolve_env(value: str) -> str:
    """Resolve ${ENV_VAR} or ${ENV_VAR:-default} references.

    Supports:
        ${VAR}            — required, raises if not set
        ${VAR:-fallback}  — optional, uses fallback if not set
    """
    if not isinstance(value, str) or not value.startswith("${") or not value.endswith("}"):
        return str(value) if value is not None else ""

    inner = value[2:-1]

    if ":-" in inner:
        env_key, default = inner.split(":-", 1)
        return os.environ.get(env_key, default)

    env_key = inner
    val = os.environ.get(env_key)
    if val is None:
        raise EnvironmentError(f"Required environment variable '{env_key}' is not set")
    return val
