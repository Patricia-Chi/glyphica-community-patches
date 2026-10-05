"""Sphere SPK v1 reader/writer; unchanged entries retain compressed bytes."""
from dataclasses import dataclass
import struct
import zlib


@dataclass
class Entry:
    name: bytes
    content: bytes
    compressed: bytes

    @property
    def path(self):
        return self.name.rstrip(b'\0').decode('utf-8')


class Archive:
    def __init__(self, data):
        if len(data) < 16:
            raise ValueError('Truncated SPK header')
        magic, version, count, index = struct.unpack_from('<4sHII', data)
        if magic != b'.spk' or version != 1 or not 16 <= index <= len(data):
            raise ValueError('Unsupported or invalid SPK archive')
        self.header = data[:16]
        self.entries = []
        cursor = index
        names = set()
        for _ in range(count):
            if cursor + 16 > len(data):
                raise ValueError('Truncated SPK index')
            version, length, offset, size, packed = struct.unpack_from('<HHIII', data, cursor)
            cursor += 16
            if (version != 1 or length < 2 or cursor + length > len(data)
                    or offset < 16 or offset + packed > index):
                raise ValueError('Invalid SPK entry')
            name = bytes(data[cursor:cursor + length])
            cursor += length
            if not name.endswith(b'\0') or b'\0' in name[:-1]:
                raise ValueError('Invalid SPK filename')
            if name in names:
                raise ValueError('Duplicate SPK filename')
            names.add(name)
            compressed = data[offset:offset + packed]
            content = zlib.decompress(compressed)
            if len(content) != size:
                raise ValueError('SPK size mismatch')
            self.entries.append(Entry(name, content, compressed))
        if cursor != len(data):
            raise ValueError('Unexpected data after SPK index')

    def get(self, path):
        for entry in self.entries:
            if entry.path == path:
                return entry.content
        raise ValueError(f'Missing archive entry: {path}')

    def replace(self, replacements):
        unknown = set(replacements) - {e.path for e in self.entries}
        if unknown:
            raise ValueError(f'Unknown replacement paths: {unknown}')
        output = bytearray(self.header)
        index = bytearray()
        for entry in self.entries:
            content = replacements.get(entry.path, entry.content)
            compressed = (entry.compressed if content == entry.content
                          else zlib.compress(content, 9))
            index.extend(struct.pack('<HHIII', 1, len(entry.name), len(output),
                                     len(content), len(compressed)))
            index.extend(entry.name)
            output.extend(compressed)
        struct.pack_into('<I', output, 10, len(output))
        output.extend(index)
        result = bytes(output)
        checked = Archive(result)
        for old, new in zip(self.entries, checked.entries):
            if old.name != new.name or new.content != replacements.get(old.path, old.content):
                raise ValueError('Rebuilt archive verification failed')
            if old.path not in replacements and old.compressed != new.compressed:
                raise ValueError('Unrelated compressed entry changed')
        return result
