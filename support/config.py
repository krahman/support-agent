"""Environment-only configuration; local .env never overrides exported values."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    path = ROOT / '.env'
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.removeprefix('export ').partition('=')
            value = value.strip().strip('\"\'')
            # Blank entries (as in .env.example) must not mask defaults such as OPENROUTER_MODEL.
            if sep and value and key.strip().isidentifier():
                os.environ.setdefault(key.strip(), value)
