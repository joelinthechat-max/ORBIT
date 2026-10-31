"""Regression tests for portable workspace path validation (Windows + Linux)."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

# Make the orbit package importable from the repository root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WorkspacePathValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orbit_root = Path(self.tmp.name).resolve()
        # Import the validator after we can control the environment if needed
        from orbit.app import _validate_and_resolve_workspace
        self.validate = _validate_and_resolve_workspace

    def tearDown(self):
        self.tmp.cleanup()

    def test_forward_slash_accepted(self):
        p = self.validate("DATA/workspace", self.orbit_root)
        self.assertEqual(p, (self.orbit_root / "DATA" / "workspace").resolve())

    def test_backslash_accepted(self):
        p = self.validate(r"DATA\workspace", self.orbit_root)
        self.assertEqual(p, (self.orbit_root / "DATA" / "workspace").resolve())

    def test_nested_relative_accepted(self):
        p = self.validate("DATA/sub/workspace", self.orbit_root)
        self.assertEqual(p, (self.orbit_root / "DATA" / "sub" / "workspace").resolve())

    def test_absolute_unix_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate("/tmp/outside", self.orbit_root)

    def test_absolute_windows_drive_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate(r"C:\Windows", self.orbit_root)
        with self.assertRaises(RuntimeError):
            self.validate("D:/DATA/workspace", self.orbit_root)

    def test_drive_qualified_relative_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate(r"C:DATA\workspace", self.orbit_root)

    def test_unc_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate(r"\\server\share\workspace", self.orbit_root)
        with self.assertRaises(RuntimeError):
            self.validate("//server/share/workspace", self.orbit_root)

    def test_parent_traversal_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate("../workspace", self.orbit_root)
        with self.assertRaises(RuntimeError):
            self.validate("DATA/../../outside", self.orbit_root)

    def test_empty_rejected(self):
        with self.assertRaises(RuntimeError):
            self.validate("", self.orbit_root)
        with self.assertRaises(RuntimeError):
            self.validate("   ", self.orbit_root)

    def test_resolved_stays_inside(self):
        p = self.validate("DATA/workspace", self.orbit_root)
        self.assertTrue(str(p).startswith(str(self.orbit_root)))


if __name__ == "__main__":
    unittest.main()
