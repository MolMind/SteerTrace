"""Prepare version changes, check release policy, and build release artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from steertrace.updates import fetch_policy, policy, version


def current():
    return re.search(r'__version__ = "([^"]+)"', (ROOT / 'src/steertrace/__init__.py').read_text(encoding='utf-8')).group(1)


def check():
    latest = current()
    version(latest)
    rules = json.loads((ROOT / 'release-policy.json').read_text(encoding='utf-8'))
    if version(rules['minimum_supported_version']) > version(latest):
        raise ValueError('Minimum supported version exceeds source version.')
    if not rules.get('reason', '').strip():
        raise ValueError('Release policy requires a reason, including mandatory-update rationale.')
    if f'## {latest}\n' not in (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'):
        raise ValueError('Current version needs a CHANGELOG section.')
    config = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    if 'dynamic = ["version"]' not in config or 'attr = "steertrace.__version__"' not in config:
        raise ValueError('Package version must use the single source of truth.')
    return latest, rules


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--check-remote', action='store_true', help='Require a version newer than the current stable GitHub Release.')
    parser.add_argument('--bump', choices=['patch', 'minor', 'major'])
    parser.add_argument('--reason')
    parser.add_argument('--minimum-supported')
    parser.add_argument('--build', type=Path, help='New output directory for GitHub Release assets.')
    args = parser.parse_args()
    if args.bump:
        if not args.reason:
            parser.error('--bump requires --reason')
        numbers = list(version(current()))
        index = {'major': 0, 'minor': 1, 'patch': 2}[args.bump]
        numbers[index] += 1
        for i in range(index + 1, 3):
            numbers[i] = 0
        latest = '.'.join(map(str, numbers))
        rules = json.loads((ROOT / 'release-policy.json').read_text(encoding='utf-8'))
        minimum = args.minimum_supported or rules['minimum_supported_version']
        if not version(rules['minimum_supported_version']) <= version(minimum) <= version(latest):
            raise ValueError('Minimum supported version cannot decrease or exceed latest.')
        p = ROOT / 'src/steertrace/__init__.py'
        p.write_text(p.read_text(encoding='utf-8').replace(f'__version__ = "{current()}"', f'__version__ = "{latest}"'), encoding='utf-8')
        rules.update(minimum_supported_version=minimum, reason=args.reason)
        (ROOT / 'release-policy.json').write_text(json.dumps(rules, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        p = ROOT / 'CHANGELOG.md'
        text = p.read_text(encoding='utf-8')
        heading, _, rest = text.partition('\n')
        p.write_text(heading + f'\n\n## {latest}\n\n- {args.reason}\n' + rest, encoding='utf-8')
    latest, rules = check()
    if args.check_remote:
        try:
            previous = fetch_policy()
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or exc.filename != 'https://api.github.com/repos/MolMind/SteerTrace/releases/latest':
                raise
            previous = None  # First stable release; other errors must not bypass checks.
        if previous:
            if version(latest) <= version(previous['latest_version']):
                raise ValueError('New release version must exceed the published stable version.')
            if version(rules['minimum_supported_version']) < version(previous['minimum_supported_version']):
                raise ValueError('Minimum supported version cannot decrease from the published policy.')
    if args.build:
        status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT, text=True)
        if status.strip():
            raise ValueError('Release artifacts require a clean committed source tree.')
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        tagged = subprocess.check_output(['git', 'rev-parse', f'v{latest}^{{commit}}'], cwd=ROOT, text=True).strip()
        if commit != tagged:
            raise ValueError('Release tag must point to the current commit.')
        # Build outside the checkout (or in an ignored directory).
        args.build.mkdir(parents=True, exist_ok=False)
        archive = args.build / f'steertrace-{latest}.zip'
        subprocess.run(['git', 'archive', '--format=zip', f'--output={archive.resolve()}', commit], cwd=ROOT, check=True)
        manifest = policy({'schema_version': 'steertrace.update/v1', 'latest_version': latest,
                           'minimum_supported_version': rules['minimum_supported_version'],
                           'reason': rules['reason'], 'release_tag': f'v{latest}', 'commit': commit,
                           'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
        log = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8').split(f'## {latest}\n', 1)[1].split('\n## ', 1)[0].strip()
        (args.build / 'release-notes.md').write_text(log + '\n\n' + rules['reason'] + '\n', encoding='utf-8')
        (args.build / 'steertrace-update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Release policy OK: {latest}; minimum supported {rules["minimum_supported_version"]}')


if __name__ == '__main__':
    main()
