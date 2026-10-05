import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from gcp.spk import Archive
from gcp.cli import atomic_write, digest, history, operation_lock, recover_history, restore, save_history


def package(files):
    data = bytearray(struct.pack('<4sHIIH', b'.spk', 1, len(files), 0, 0))
    index = bytearray()
    for name, content in files.items():
        name = name.encode() + b'\0'
        compressed = zlib.compress(content)
        index.extend(struct.pack('<HHIII', 1, len(name), len(data), len(content), len(compressed)))
        index.extend(name)
        data.extend(compressed)
    struct.pack_into('<I', data, 10, len(data))
    return bytes(data + index)


class ArchiveTests(unittest.TestCase):
    def test_replace_preserves_other_compressed_entries(self):
        data = package({'scripts/a.js': b'old', 'asset.bin': bytes(range(256))})
        archive = Archive(data)
        self.assertEqual(archive.replace({}), data)
        result = Archive(archive.replace({'scripts/a.js': b'longer replacement'}))
        self.assertEqual(result.get('scripts/a.js'), b'longer replacement')
        self.assertEqual(result.entries[1], archive.entries[1])
        with self.assertRaises(ValueError):
            archive.replace({'missing': b'x'})

    def test_corrupt_and_truncated_archives_fail(self):
        data = package({'a': b'hello'})
        for bad in (b'', b'wrong header....', data[:-1], data + b'trailer'):
            with self.assertRaises((ValueError, zlib.error)):
                Archive(bad)
        broken = bytearray(data)
        broken[16] = 0
        with self.assertRaises(zlib.error):
            Archive(broken)

    def test_portable_restore_and_update_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / 'glyphica.spk'
            folder = root / '.glyphica-community-patches'
            folder.mkdir()
            before = package({'a': b'original'})
            after = package({'a': b'patched'})
            updated = package({'a': b'steam update'})
            (folder / (digest(before) + '.spk')).write_bytes(before)
            record = {'before': digest(before), 'after': digest(after), 'patch': 'example'}
            save_history(folder, [record])
            game.write_bytes(updated)
            with self.assertRaises(ValueError):
                restore(game, folder)
            self.assertEqual(game.read_bytes(), updated)
            game.write_bytes(after)
            restore(game, folder)
            self.assertEqual(game.read_bytes(), before)
            self.assertEqual(history(folder), [])

    def test_corrupted_backup_is_not_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / 'glyphica.spk'
            before, after = package({'a': b'1'}), package({'a': b'2'})
            game.write_bytes(after)
            folder = root / 'state'
            folder.mkdir()
            (folder / (digest(before) + '.spk')).write_bytes(b'corrupt')
            save_history(folder, [{'patch': 'x', 'before': digest(before), 'after': digest(after)}])
            with self.assertRaises(ValueError):
                restore(game, folder)
            self.assertEqual(game.read_bytes(), after)

    def test_interrupted_journal_and_concurrent_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [{'before': 'a' * 64, 'after': 'b' * 64}]
            save_history(root, records)
            self.assertEqual(recover_history(root, records, 'a' * 64), [])
            with operation_lock(root):
                with self.assertRaises(ValueError):
                    with operation_lock(root):
                        pass
            self.assertFalse((root / 'operation.lock').exists())

    def test_invalid_history_path_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'history.json').write_text(json.dumps([{'before': '../escape', 'after': 'b' * 64}]))
            with self.assertRaises(ValueError):
                history(root)


if __name__ == '__main__':
    unittest.main()
