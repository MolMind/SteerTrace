"""Public release metadata and transactional, opt-in managed installations."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import venv
import zipfile

from .storage import TraceError

REPOSITORY = 'https://github.com/MolMind/SteerTrace'
LATEST = 'https://api.github.com/repos/MolMind/SteerTrace/releases/latest'
MARKER = '.steertrace-install.json'
MAX_METADATA = 128 * 1024
MAX_ARCHIVE = 32 * 1024 * 1024


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise TraceError('Expected a stable major.minor.patch version.')
    return tuple(map(int, value.split('.')))


def policy(data):
    if not isinstance(data, dict) or data.get('schema_version') != 'steertrace.update/v1':
        raise TraceError('Unsupported update manifest.')
    latest, minimum = data.get('latest_version'), data.get('minimum_supported_version')
    if version(minimum) > version(latest):
        raise TraceError('Minimum supported version exceeds latest release.')
    if data.get('release_tag') != 'v' + latest:
        raise TraceError('Release tag/version mismatch.')
    if not re.fullmatch(r'[a-f0-9]{64}', str(data.get('sha256', ''))):
        raise TraceError('Release archive requires SHA-256.')
    if not re.fullmatch(r'[a-f0-9]{40}', str(data.get('commit', ''))):
        raise TraceError('Release requires a source commit.')
    if not isinstance(data.get('reason'), str) or not data['reason'].strip():
        raise TraceError('Release update reason is missing.')
    return data


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise TraceError(f'Cannot read installation metadata: {path}') from exc


def download(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'SteerTrace-updater', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise TraceError('Release download exceeds size limit.')
    return data


def fetch_policy():
    release = json.loads(download(LATEST, MAX_METADATA))
    if not isinstance(release, dict):
        raise TraceError('Invalid GitHub release response.')
    tag = release.get('tag_name')
    if not isinstance(tag, str) or not tag.startswith('v'):
        raise TraceError('Latest release has no stable version tag.')
    version(tag[1:])
    if release.get('draft') or release.get('prerelease'):
        raise TraceError('Automatic updates require a stable public release.')
    data = policy(json.loads(download(f'{REPOSITORY}/releases/download/{tag}/steertrace-update.json', MAX_METADATA)))
    if data['release_tag'] != tag:
        raise TraceError('Latest release and manifest disagree.')
    return data


def tree_hash(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in {'__pycache__', '.git', '.venv', 'build', 'dist'} or part.endswith('.egg-info') for part in relative.parts):
            continue
        if path.is_symlink():
            raise TraceError(f'Managed source contains a symlink: {relative}')
        if path.is_file():
            result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def unpack(data, destination):
    archive = destination.parent / 'release.zip'
    archive.write_bytes(data)
    with zipfile.ZipFile(archive) as zipped:
        size = 0
        names = set()
        for info in zipped.infolist():
            path = PurePosixPath(info.filename)
            size += info.file_size
            if (path.is_absolute() or '..' in path.parts or '\\' in info.filename or
                    ':' in info.filename or info.filename in names or
                    ((info.external_attr >> 16) & 0o170000) == 0o120000 or size > MAX_ARCHIVE * 4):
                raise TraceError('Unsafe release archive member.')
            names.add(info.filename)
        zipped.extractall(destination)
    archive.unlink()


def python_at(environment):
    return environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def clean_environment():
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    return environment


def run(args, cwd):
    subprocess.run([str(a) for a in args], cwd=cwd, env=clean_environment(),
                   check=True, timeout=300, stdout=sys.stderr)


def install_release(root, skill, data, previous, adopt_from=None):
    if skill.is_symlink():
        raise TraceError('Skill uses a symlink; migrate explicitly to a managed copy before updating.')
    if previous:
        if tree_hash(skill) != previous['skill_hash'] or tree_hash(Path(previous['source'])) != previous['source_hash']:
            raise TraceError('Local modifications detected; preserve them before updating.')
    elif skill.exists():
        if not adopt_from or tree_hash(skill) != tree_hash(adopt_from / 'skills/steer-trace'):
            raise TraceError('Existing Skill is not managed; --adopt-from must match its unmodified source checkout.')
    original_skill_hash = tree_hash(skill) if skill.exists() else None
    release_dir = root / 'releases' / (data['latest_version'] + '-' + uuid.uuid4().hex)
    release_dir.mkdir(parents=True)
    staged_skill = skill.with_name(skill.name + '.new-' + uuid.uuid4().hex)
    backup = skill.with_name(skill.name + '.backup-' + uuid.uuid4().hex)
    switched = False
    try:
        payload = download(f"{REPOSITORY}/releases/download/{data['release_tag']}/steertrace-{data['latest_version']}.zip", MAX_ARCHIVE)
        if hashlib.sha256(payload).hexdigest() != data['sha256']:
            raise TraceError('Release archive SHA-256 mismatch.')
        source = release_dir / 'source'
        unpack(payload, source)
        # All executable files come from the official release, only after digest verification.
        init = (source / 'src/steertrace/__init__.py').read_text(encoding='utf-8')
        if f'__version__ = "{data["latest_version"]}"' not in init:
            raise TraceError('Source/package version mismatch.')
        for name in ('skills/steer-trace/SKILL.md', 'docs/reference/event-schema.md', 'scripts/update.py'):
            if not (source / name).is_file():
                raise TraceError(f'Release is missing {name}.')
        source_hash = tree_hash(source)
        environment = release_dir / 'environment'
        venv.create(environment, with_pip=True)
        python = python_at(environment)
        run([python, '-m', 'pip', 'install', '--no-deps', source], release_dir)
        found = subprocess.check_output([str(python), '-m', 'steertrace', '--version'], text=True, timeout=30, cwd=release_dir, env=clean_environment()).strip()
        if found != data['latest_version']:
            raise TraceError('Installed CLI version does not match the release.')
        run([python, source / 'scripts/demo.py', release_dir / 'smoke'], release_dir)
        run([python, '-m', 'steertrace', 'report', '--run', release_dir / 'smoke',
             '--events', release_dir / 'smoke/events.json', '--output', release_dir / 'smoke/installed.html'], release_dir)
        shutil.copytree(source / 'skills/steer-trace', staged_skill)
        state = {'version': found, 'commit': data['commit'], 'source': str(source), 'python': str(python),
                 'skill_dir': str(skill), 'install_root': str(root), 'source_hash': source_hash}
        atomic_json(staged_skill / MARKER, {k: state[k] for k in ('version', 'source', 'python', 'install_root')})
        state['skill_hash'] = tree_hash(staged_skill)
        # Detect edits that happened while staging, before touching the active Skill.
        if skill.is_symlink() or (tree_hash(skill) if skill.exists() else None) != original_skill_hash:
            raise TraceError('Skill changed during staging; update cancelled.')
        if previous and (tree_hash(skill) != previous['skill_hash'] or tree_hash(Path(previous['source'])) != previous['source_hash']):
            raise TraceError('Installation changed during staging; update cancelled.')
        if previous:
            atomic_json(root / 'history' / (previous['version'] + '-' + uuid.uuid4().hex + '.json'), previous)
        if skill.exists():
            skill.rename(backup)
        try:
            staged_skill.rename(skill)
            switched = True
            atomic_json(root / 'state.json', state)
        except BaseException:
            if switched:
                shutil.rmtree(skill)
            if backup.exists():
                backup.rename(skill)
            raise
        # Keep the backup and previous release for recovery; no old install is deleted.
        return state
    except BaseException:
        if staged_skill.exists():
            shutil.rmtree(staged_skill)
        if not switched:
            shutil.rmtree(release_dir)
        raise


def update(root, skill_dir=None, check_only=False, force_check=False, adopt_from=None):
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    # A lock covers metadata, staging and switching, including concurrent agent calls.
    lock = root / 'update.lock'
    try:
        descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise TraceError('Another update is running. If interrupted, inspect and remove update.lock before retrying.') from exc
    os.close(descriptor)
    try:
        return _update(root, skill_dir, check_only, force_check, adopt_from)
    finally:
        lock.unlink(missing_ok=True)


def _update(root, skill_dir, check_only, force_check, adopt_from):
    state = read_json(root / 'state.json') if (root / 'state.json').exists() else None
    skill = Path(state['skill_dir']) if state else skill_dir
    if not skill:
        raise TraceError('First managed installation requires --skill-dir.')
    skill = skill.expanduser().absolute()
    # Managed installation must live outside the client Skill directory.
    if skill == root or skill in root.parents or root in skill.parents:
        raise TraceError('Installation root and Skill directory must be separate trees.')
    if state and skill_dir and skill_dir.expanduser().absolute() != skill:
        raise TraceError('--skill-dir differs from the registered installation.')
    skill.parent.mkdir(parents=True, exist_ok=True)
    cache_path = root / 'update-cache.json'
    cache = read_json(cache_path) if cache_path.exists() else {}
    cached = policy(cache['policy']) if cache.get('policy') else None
    now = time.time()
    offline = False
    data = cached
    verified_at = cache.get('checked_at')
    if force_check or not cached or not 0 <= now - cache.get('checked_at', 0) < 86400:
        try:
            candidate = fetch_policy()
            # Never relax an already learned minimum on an older/replayed manifest.
            if cached and (version(candidate['minimum_supported_version']) < version(cached['minimum_supported_version']) or
                           version(candidate['latest_version']) < version(cached['latest_version'])):
                raise TraceError('Remote release policy regressed.')
            atomic_json(cache_path, {'checked_at': now, 'policy': candidate})
            data = candidate
            verified_at = now
        except (OSError, ValueError, TraceError) as exc:
            offline = True
            network_error = str(exc)
    installed = state['version'] if state else None
    required = bool(installed and data and version(installed) < version(data['minimum_supported_version']))
    available = bool(data and (not installed or version(installed) < version(data['latest_version'])))
    result = {'installed_version': installed, 'latest_version': data['latest_version'] if data else None,
              'required': required, 'offline': offline, 'update_available': available,
              'checked_at': datetime.fromtimestamp(verified_at, timezone.utc).isoformat() if verified_at is not None else None,
              'can_run': bool(state) and not required,
              'status': 'required' if required else 'available' if available else 'offline' if offline else 'current'}
    if offline:
        result['message'] = 'Latest version could not be confirmed: ' + network_error
    if data:
        result['reason'] = data['reason']
    if state:
        result.update({k: state[k] for k in ('python', 'source')})
    if available and not check_only:
        try:
            state = install_release(root, skill, data, state, adopt_from)
            result.update(status='updated', installed_version=state['version'], can_run=True, required=False, update_available=False,
                          python=state['python'], source=state['source'])
        except (OSError, ValueError, TraceError, subprocess.SubprocessError) as exc:
            result.update(status='update_failed', message=str(exc))
    return result
