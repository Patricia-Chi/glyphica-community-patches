import unittest
from unittest.mock import patch

from gcp.cli import verify
from gcp.patches import microsoft_shuangpin


class PatchTests(unittest.TestCase):
    def test_unknown_revision_is_refused(self):
        unknown = b'// another revision'
        self.assertEqual(microsoft_shuangpin.status(unknown), 'unsupported')
        with self.assertRaises(ValueError):
            microsoft_shuangpin.transform(unknown)

    def test_marker_alone_does_not_mean_installed(self):
        unknown = ('\t// 微软双拼\n' + microsoft_shuangpin.ADDITION + '\n\t// 小鹤双拼').encode()
        self.assertEqual(microsoft_shuangpin.status(unknown), 'unsupported')

    def test_missing_node_fails_before_reading_or_writing(self):
        with patch('gcp.cli.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Node.js'):
                verify(microsoft_shuangpin, None, b'')


if __name__ == '__main__':
    unittest.main()
