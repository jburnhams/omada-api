"""Keep secrets out of anything printed."""

import re

SECRET_KEY = re.compile(r"pass(word)?|secret|token|psk|pin$|private|credential|auth", re.I)


def mask(obj):
    """A copy of `obj` with the value of every secret-looking key replaced by '***' (only when it has a value)."""
    if isinstance(obj, dict):
        return {
            k: (
                "***"
                if SECRET_KEY.search(str(k)) and v not in (None, "", False) and not isinstance(v, (dict, list))
                else mask(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [mask(x) for x in obj]
    return obj
