"""Cross-platform installation smoke check; no real client settings are changed."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='steertrace-install-') as temporary:
        # Exercise paths with spaces and non-ASCII characters on both platforms.
        home = Path(temporary) / '安装 check'
        home.mkdir()
        environment = home / 'environment'
        venv.create(environment, with_pip=True)
        binary = environment / ('Scripts' if os.name == 'nt' else 'bin')
        python = binary / ('python.exe' if os.name == 'nt' else 'python')
        cli = binary / ('steertrace.exe' if os.name == 'nt' else 'steertrace')
        subprocess.run([str(python), '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', str(ROOT)], check=True)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)

        def run(*args: object) -> str:
            result = subprocess.run([str(cli), *map(str, args)], cwd=home,
                                    check=True, capture_output=True, text=True,
                                    encoding='utf-8')
            return result.stdout

        assert run('--version').strip() == '0.1.0'
        subprocess.run([str(python), '-c', '''from importlib.resources import files
assets = files('steertrace').joinpath('assets')
for name in ['report.css', 'report.js', 'tabler-chevron-right.svg', 'tabler-LICENSE.txt']:
    assert assets.joinpath(name).read_text(encoding='utf-8')
'''], cwd=home, check=True)

        # Validate the copy-based Skill installation route, without requiring symlinks
        # or writing to a real user's client configuration. Keep the full checkout.
        skill = home / 'client skills' / 'steer-trace'
        shutil.copytree(ROOT / 'skills/steer-trace', skill)
        body = (skill / 'SKILL.md').read_text(encoding='utf-8')
        assert re.search(r'^name: steer-trace$', body, re.MULTILINE)
        for document in skill.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if target.startswith(('http:', 'https:', '#')):
                    continue
                relative = target.split('#')[0]
                # Skill-local links resolve in the installed copy; repository-level
                # links resolve against the retained checkout's matching reference.
                source = ROOT / 'skills/steer-trace' / document.relative_to(skill)
                assert (document.parent / relative).exists() or (source.parent / relative).exists(), target
        assert (ROOT / 'docs/reference/event-schema.md').is_file()

        run('import', '--input', ROOT / 'examples/synthetic/conversation.json',
            '--output', home / 'conversation.json')
        run('prepare', '--conversation', home / 'conversation.json', '--project', ROOT,
            '--docs', 'examples/synthetic/plan.md', '--output', home / 'review')
        analysis = json.loads((ROOT / 'examples/synthetic/analysis.json').read_text(encoding='utf-8'))
        analysis['run_id'] = json.loads((home / 'review/manifest.json').read_text(encoding='utf-8'))['run_id']
        events = home / 'events.json'
        events.write_text(json.dumps(analysis, ensure_ascii=False), encoding='utf-8')
        checked = json.loads(run('validate', '--run', home / 'review', '--events', events))
        assert checked['valid']
        run('report', '--run', home / 'review', '--events', events, '--output', home / 'report.html')
        assert (home / 'report.html').read_text(encoding='utf-8').startswith('<!doctype html>')
        print('PASS: isolated package install, CLI, packaged assets, Skill copy/references, '
              'Unicode/space paths, and synthetic report workflow. '
              'Real client discovery and current-session access require client verification.')


if __name__ == '__main__':
    main()
