"""Bootstrap or update a managed installation from this retained checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from steertrace.cli import main

if __name__ == '__main__':
    raise SystemExit(main(['update', *sys.argv[1:]]))
