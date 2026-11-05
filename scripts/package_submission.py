"""Build an allowlisted submission ZIP, excluding secrets and runtime/IDE state."""
from pathlib import Path
import os
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from support.config import load_env


def main():
    load_env()
    files = [ROOT / name for name in ('main.py', 'pyproject.toml', 'README.md', 'ASSUMPTIONS.md', '.env.example', '.gitignore')]
    for folder, extensions in [('support', {'.py'}), ('tests', {'.py'}), ('evals', {'.py'}),
                               ('data', {'.json'}), ('eval_runs', {'.json'}),
                               ('docs', {'.md'}), ('scripts', {'.py'})]:
        files += sorted(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in extensions)
    secrets = [os.environ[k].encode() for k in ('ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY') if os.environ.get(k)]
    for path in files:
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise SystemExit('Refusing a symlink or file outside the project.')
        if any(secret in path.read_bytes() for secret in secrets):
            raise SystemExit('Refusing archive: credential detected in an included file (value not displayed).')
    target = ROOT / 'dist/apparel-support-agent.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert '.env' not in names and '.env.example' in names
        assert not any(name.startswith(('.venv/', '.idea/', 'state/')) for name in names)
    print(f'Created {target.relative_to(ROOT)} ({len(files)} files, {target.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
