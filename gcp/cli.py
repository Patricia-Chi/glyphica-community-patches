import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib
from contextlib import contextmanager

from . import __version__
from .patches import PATCHES
from .spk import Archive

ROOT = Path(__file__).resolve().parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=None):
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        if temporary.read_bytes() != data:
            raise ValueError('Temporary file verification failed')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def verify(patch, archive, changed):
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js is required for validation. Install it, then restart your terminal.')
    payload = {'original': archive.get(patch.TARGET).decode('utf-8'),
               'patched': changed.decode('utf-8'),
               'pinyin': archive.get('scripts/libs/pinyin.js').decode('utf-8')}
    result = subprocess.run([node, str(ROOT / 'tests' / patch.TEST)],
                            input=json.dumps(payload).encode('utf-8'),
                            capture_output=True, timeout=120)
    print(result.stdout.decode('utf-8', errors='replace'), end='')
    if result.returncode:
        raise ValueError('JavaScript validation failed:\n' + result.stderr.decode('utf-8', errors='replace'))


def state_path(game):
    return game.parent / '.glyphica-community-patches'


def history(folder):
    path = folder / 'history.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('Invalid patch history')
    for item in data:
        for key in ('before', 'after'):
            value = item[key]
            if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Invalid history checksum')
    return data


def save_history(folder, records):
    atomic_write(folder / 'history.json', (json.dumps(records, indent=2) + '\n').encode('utf-8'))


@contextmanager
def operation_lock(folder):
    lock = folder / 'operation.lock'
    try:
        handle = lock.open('x')
    except FileExistsError:
        raise ValueError('Another operation may be running. See docs/recovery.md before removing operation.lock.')
    try:
        with handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def restore(game, folder):
    if not folder.exists():
        print('No managed backup. External/older patches need their original backup.')
        return
    with operation_lock(folder):
        original = game.read_bytes()
        records = recover_history(folder, history(folder), digest(original))
        if not records:
            print('No managed patch to restore. External/older patches need their original backup.')
            return
        record = records[-1]
        data = (folder / (record['before'] + '.spk')).read_bytes()
        if digest(data) != record['before']:
            raise ValueError('Backup checksum mismatch')
        Archive(data)
        if game.read_bytes() != original:
            raise ValueError('Game changed during restore')
        atomic_write(game, data, game.stat().st_mode & 0o777)
        save_history(folder, records[:-1])
        print(f'Restored state before {record["patch"]}. Backups retained in {folder}')


def recover_history(folder, records, current):
    # A crash may occur between updating the journal and replacing the game.
    if records and records[-1]['before'] == current:
        records = records[:-1]
        save_history(folder, records)
    if records and records[-1]['after'] != current:
        raise ValueError('Game differs from patch history (possibly a Steam update). Refusing to overwrite it. See docs/recovery.md.')
    return records


def operate(args):
    game = args.game_dir.expanduser().resolve() / 'glyphica.spk'
    if not game.is_file():
        raise ValueError(f'Game archive not found: {game}')
    original = game.read_bytes()
    current = digest(original)
    folder = state_path(game)
    if args.command == 'restore':
        restore(game, folder)
        return
    archive = Archive(original)
    if args.command == 'status':
        for patch in PATCHES.values():
            print(f'{patch.ID}: {patch.status(archive.get(patch.TARGET))}')
        records = history(folder)
        print(f'Managed history: {len(records)} patch(es)')
        if records and current != records[-1]['after']:
            print('History does not match current archive; check docs/recovery.md before applying/restoring.')
        return
    patch = PATCHES[args.patch]
    status = patch.status(archive.get(patch.TARGET))
    if status == 'already-patched':
        print('Already patched; no files changed. Existing external patches are not adopted into restore history.')
        return
    if status != 'applicable':
        raise ValueError('Unsupported script revision. No patch applied; see docs/patches.md.')
    changed = patch.transform(archive.get(patch.TARGET))
    verify(patch, archive, changed)
    output = archive.replace({patch.TARGET: changed})
    print(f'Validated {len(archive.entries)} archive entries; target: {patch.TARGET}')
    if args.command == 'check':
        print('Check passed. No files changed.')
        return
    folder.mkdir(exist_ok=True)
    with operation_lock(folder):
        if game.read_bytes() != original:
            raise ValueError('Game changed during validation')
        records = recover_history(folder, history(folder), current)
        backup = folder / (current + '.spk')
        if backup.exists():
            if backup.read_bytes() != original:
                raise ValueError('Existing backup checksum mismatch')
        else:
            atomic_write(backup, original)
        records.append({'patch': patch.ID, 'tool_version': __version__,
                        'before': current, 'after': digest(output)})
        # Journal first: a failed replacement can be detected on the next run.
        save_history(folder, records)
        atomic_write(game, output, game.stat().st_mode & 0o777)
        print(f'Applied {patch.ID}. Backup and portable history: {folder}')


def main(argv=None):
    # Keep Chinese validation output usable on Windows terminals as well.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='Unofficial, reversible Glyphica community patches')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list', help='List available patches')
    for name in ('status', 'check', 'apply', 'restore'):
        command = sub.add_parser(name)
        command.add_argument('--game-dir', required=True, type=Path,
                             help='Glyphica directory containing glyphica.spk')
        if name in ('check', 'apply'):
            command.add_argument('--patch', required=True, choices=sorted(PATCHES))
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            for patch in PATCHES.values():
                print(f'{patch.ID}: {patch.DESCRIPTION}')
        else:
            operate(args)
    except (OSError, ValueError, KeyError, TypeError, zlib.error, subprocess.TimeoutExpired) as error:
        print(f'Error: {error}')
        return 1
    return 0
