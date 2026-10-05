"""Scoped Microsoft Shuangpin overrides, verified on Steam build 24849940."""
import hashlib

ID = 'microsoft-shuangpin'
DESCRIPTION = 'Fix Microsoft Shuangpin ü/üe and related syllable aliases'
TARGET = 'scripts/data/doublePinyin.js'
ORIGINAL_SHA256 = '68f66ce7d7cfac76beaf06974beeda485e38d9d132308dd3264fddbdbf25ed04'
TEST = 'microsoft_shuangpin.cjs'
ADDITION = """
			// Explicit matches precede the shared two-letter passthrough.
			lv: 'ly', nv: 'ny', 'lü': 'ly', 'nü': 'ny',
			ju: ['ju', 'jy'], qu: ['qu', 'qy'],
			xu: ['xu', 'xy'], yu: ['yu', 'yy'],
			jv: ['ju', 'jy'], qv: ['qu', 'qy'],
			xv: ['xu', 'xy'], yv: ['yu', 'yy'],
			'lüe': ['lt', 'lv'], 'nüe': ['nt', 'nv'],"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def transform(data):
    if digest(data) != ORIGINAL_SHA256:
        raise ValueError('Unrecognized doublePinyin.js; patch refused')
    source = data.decode('utf-8')
    start = source.index('\t// 微软双拼')
    end = source.index('\t// 小鹤双拼', start)
    block = source[start:end]
    marker = '\t\twhole: {'
    if block.count("v: 'y', ve: 'v'") != 1 or block.count(marker) != 1:
        raise ValueError('Unexpected Microsoft Shuangpin table')
    newline = '\r\n' if '\r\n' in source else '\n'
    block = block.replace("v: 'y', ve: 'v'", "v: 'y', ve: ['t', 'v']")
    block = block.replace(marker, marker + ADDITION.replace('\n', newline))
    return (source[:start] + block + source[end:]).encode('utf-8')


def status(data):
    if digest(data) == ORIGINAL_SHA256:
        return 'applicable'
    # Recognize the exact existing patch, including the initial local version.
    source = data.decode('utf-8')
    newline = '\r\n' if '\r\n' in source else '\n'
    addition = ADDITION.replace('\n', newline)
    if source.count(addition) == 1:
        candidate = source.replace(addition, '')
        start = candidate.find('\t// 微软双拼')
        end = candidate.find('\t// 小鹤双拼', start)
        if start >= 0 and end > start:
            block = candidate[start:end].replace("v: 'y', ve: ['t', 'v']", "v: 'y', ve: 'v'")
            original = (candidate[:start] + block + candidate[end:]).encode('utf-8')
            if digest(original) == ORIGINAL_SHA256 and transform(original) == data:
                return 'already-patched'
    return 'unsupported'
