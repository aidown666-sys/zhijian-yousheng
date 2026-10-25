import tempfile
import unittest
from pathlib import Path
from tools.audit_secrets import contains_known, findings, protected


class SecretAuditTests(unittest.TestCase):
    def test_known_values_are_caught_without_echoing_values(self):
        known = {'app_id': b'example-account-123', 'app_secret': b'opaque-test-secret-xyz'}
        issues = findings(b'notes: opaque-test-secret-xyz', 'docs/notes.md', known)
        self.assertEqual(issues, ['known-local-credential:app_secret'])
        self.assertNotIn('opaque-test-secret-xyz', repr(issues))

    def test_hardcoded_polyv_fields_and_placeholders(self):
        self.assertIn('hardcoded-field:app_secret', findings(b"'app_secret' => 'opaque-value-123'", 'config.php', {}))
        self.assertEqual(findings(b"'app_secret' => 'YOUR_APP_SECRET'", 'config.example.php', {}), [])
        self.assertEqual(findings(b"'app_secret' => getenv('POLYV_APP_SECRET')", 'config.php', {}), [])

    def test_unit_fixtures_never_hide_real_known_values(self):
        self.assertEqual(findings(b"'app_secret': 'fixture-only'", 'tests/test_config.py', {}), [])
        self.assertEqual(findings(b'fixture-only', 'tests/test_config.py', {'app_secret': b'fixture-only'}), ['known-local-credential:app_secret'])

    def test_protected_paths_and_safe_examples(self):
        for name in ['.env', '.env.production', 'integrations/polyv/server/private/config.php', 'backup.zip', 'tls.key', 'runtime/state.json']:
            self.assertTrue(protected(name), name)
        for name in ['.env.example', 'integrations/polyv/local-bridge.example.json', 'integrations/polyv/server/config.example.php']:
            self.assertFalse(protected(name), name)

    def test_stream_matches_spanning_chunk_boundary(self):
        value = b'fake-credential-for-boundary-test'
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'asset.bin'
            file.write_bytes(b'\0' * (1024 * 1024 - 6) + value + b'\0' * 100)
            self.assertEqual(contains_known(file, {'app_secret': value}), ['known-local-credential:app_secret'])


if __name__ == '__main__':
    unittest.main()
