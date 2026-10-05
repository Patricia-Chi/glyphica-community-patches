"""Optional local integration test. Never publishes or modifies the source archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def run(*args, success=True):
    result = subprocess.run([sys.executable, str(ROOT / 'glyphica_patch.py'), *args],
                            capture_output=True, encoding='utf-8', timeout=180)
    print(result.stdout)
    if (result.returncode == 0) != success:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    original = args.archive.read_bytes()
    original_hash = hashlib.sha256(original).hexdigest()
    with tempfile.TemporaryDirectory(prefix='glyphica-test-') as temp:
        game_dir = Path(temp) / 'Glyphica path with spaces 中文'
        game_dir.mkdir()
        game = game_dir / 'glyphica.spk'
        game.write_bytes(original)
        run('list')
        assert 'applicable' in run('status', '--game-dir', str(game_dir))
        run('check', '--patch', 'microsoft-shuangpin', '--game-dir', str(game_dir))
        assert sorted(p.name for p in game_dir.iterdir()) == ['glyphica.spk']
        assert game.read_bytes() == original
        run('apply', '--patch', 'microsoft-shuangpin', '--game-dir', str(game_dir))
        patched = game.read_bytes()
        assert patched != original
        records = (game_dir / '.glyphica-community-patches/history.json').read_bytes()
        run('apply', '--patch', 'microsoft-shuangpin', '--game-dir', str(game_dir))
        assert game.read_bytes() == patched
        assert (game_dir / '.glyphica-community-patches/history.json').read_bytes() == records
        # Move the entire game directory: history must not depend on absolute paths.
        moved = Path(temp) / 'Moved game 中文'
        game_dir.rename(moved)
        game = moved / 'glyphica.spk'
        game.write_bytes(patched + b'external modification')
        run('restore', '--game-dir', str(moved), success=False)
        assert game.read_bytes() == patched + b'external modification'
        game.write_bytes(patched)
        run('restore', '--game-dir', str(moved))
        assert game.read_bytes() == original
        assert json.loads((moved / '.glyphica-community-patches/history.json').read_text()) == []
        # Simulate an already-patched external install, without a managed backup.
        shutil.rmtree(moved / '.glyphica-community-patches')
        game.write_bytes(patched)
        assert 'Already patched' in run('apply', '--patch', 'microsoft-shuangpin', '--game-dir', str(moved))
        run('restore', '--game-dir', str(moved))
        assert game.read_bytes() == patched
        assert not (moved / '.glyphica-community-patches').exists()
    assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == original_hash
    print('PASS: dry run, apply, idempotence, directory relocation, update refusal, byte-exact restore, external patch detection. Source untouched.')


if __name__ == '__main__':
    main()
