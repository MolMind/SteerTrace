"""Publish a tested default-branch commit, or safely skip an exact rerun."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import release as releasing


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def should_publish(latest, rules, commit, previous):
    if previous is None:
        return True
    if releasing.version(rules['minimum_supported_version']) < releasing.version(previous['minimum_supported_version']):
        raise ValueError('Minimum supported version cannot decrease.')
    if releasing.version(latest) < releasing.version(previous['latest_version']):
        raise ValueError('An older version cannot replace the latest stable release.')
    if latest == previous['latest_version']:
        if previous['commit'] != commit:
            raise ValueError('Version already published from another commit; prepare a new version.')
        return False
    return True


def ensure_tag(tag, commit):
    # Query the exact remote tag, preferring the peeled commit for annotated tags.
    remote = subprocess.run(['git', 'ls-remote', '--exit-code', '--tags', 'origin',
                             f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}'], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    if remote.returncode not in (0, 2):
        raise RuntimeError('Cannot inspect remote release tag: ' + remote.stderr)
    refs = dict(line.split()[::-1] for line in remote.stdout.splitlines())
    found = refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}'))
    if found and found != commit:
        raise ValueError('Release tag already points to a different commit; refusing to move it.')
    local = subprocess.run(['git', 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}'],
                           cwd=ROOT, capture_output=True, text=True, check=False)
    if local.returncode == 0 and local.stdout.strip() != commit:
        raise ValueError('Local release tag points to a different commit.')
    if local.returncode != 0:
        if found:
            git('fetch', 'origin', f'refs/tags/{tag}:refs/tags/{tag}')
        else:
            git('tag', tag, commit)
    if not found:
        git('push', 'origin', f'refs/tags/{tag}')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    latest, rules = releasing.check()
    commit = git('rev-parse', 'HEAD')
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Publishing requires clean committed source.')
    try:
        previous = releasing.fetch_policy()
    except urllib.error.HTTPError as exc:
        if exc.code != 404 or exc.filename != 'https://api.github.com/repos/MolMind/SteerTrace/releases/latest':
            raise
        previous = None
    if not should_publish(latest, rules, commit, previous):
        print(f'v{latest} is already published from this commit; no changes made.')
        return
    tag = 'v' + latest
    ensure_tag(tag, commit)
    # Publish in this same run. GITHUB_TOKEN tag pushes do not start another workflow.
    subprocess.run([sys.executable, ROOT / 'scripts/release.py', '--build', args.output], cwd=ROOT, check=True)
    subprocess.run(['gh', 'release', 'create', tag,
                    args.output / f'steertrace-{latest}.zip', args.output / 'steertrace-update.json',
                    '--verify-tag', '--latest', '--title', 'SteerTrace ' + tag,
                    '--notes-file', args.output / 'release-notes.md'], cwd=ROOT, check=True)
    print(f'Published {tag} from {commit}.')


if __name__ == '__main__':
    main()
