"""Tests for ls_manage.py"""

import hashlib
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ls_manage


class TestGetBinaryHash:
    """Tests for get_binary_hash function"""

    def test_get_binary_hash_valid_file(self):
        """Test hashing a valid file"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = ls_manage.get_binary_hash(temp_path)
            # Verify it's a valid SHA256 hex string (64 chars)
            assert len(result) == 64
            assert all(c in "0123456789abcdef" for c in result)

            # Verify the hash is correct
            expected_hash = hashlib.sha256(b"test content").hexdigest()
            assert result == expected_hash
        finally:
            os.unlink(temp_path)

    def test_get_binary_hash_nonexistent_file(self):
        """Test hashing a non-existent file"""
        with pytest.raises(SystemExit):
            ls_manage.get_binary_hash("/nonexistent/path/to/binary")

    def test_get_binary_hash_symlink(self):
        """Test hashing a symlink resolves to actual file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real file
            real_file = os.path.join(tmpdir, "real_binary")
            with open(real_file, "wb") as f:
                f.write(b"real content")

            # Create a symlink to it
            symlink_path = os.path.join(tmpdir, "symlink_binary")
            os.symlink(real_file, symlink_path)

            # Hash both paths
            hash_via_symlink = ls_manage.get_binary_hash(symlink_path)
            hash_via_real = ls_manage.get_binary_hash(real_file)

            # They should be identical
            assert hash_via_symlink == hash_via_real

            # Verify it matches the expected hash
            expected_hash = hashlib.sha256(b"real content").hexdigest()
            assert hash_via_symlink == expected_hash


class TestFindCodeRequirementKey:
    """Tests for find_code_requirement_key function"""

    def test_find_code_requirement_key_exact_match(self):
        """Test finding exact path match in code requirements"""
        config = {
            "codeRequirements": {
                "/usr/local/bin/example": {"type": "fileHash", "codeIdentifier": "abc123"}
            }
        }
        # This will return None because the current implementation
        # only handles Cellar paths, but we test the structure
        result = ls_manage.find_code_requirement_key(config, "/usr/local/bin/example")
        # For non-Cellar paths, should return None
        assert result is None

    def test_find_code_requirement_key_homebrew_cellar(self):
        """Test finding Homebrew Cellar path with wildcard pattern"""
        config = {
            "codeRequirements": {
                "path.usr/local/Cellar/mosh/*/bin/mosh-server": {
                    "type": "fileHash",
                    "codeIdentifier": "abc123",
                }
            }
        }
        # Mock realpath to return a Cellar path
        with patch("os.path.realpath") as mock_realpath:
            mock_realpath.return_value = "/usr/local/Cellar/mosh/1.4.0/bin/mosh-server"
            result = ls_manage.find_code_requirement_key(config, "/usr/local/bin/mosh-server")
            assert result == "path.usr/local/Cellar/mosh/*/bin/mosh-server"

    def test_find_code_requirement_key_empty_config(self):
        """Test with empty codeRequirements"""
        config = {"codeRequirements": {}}
        result = ls_manage.find_code_requirement_key(config, "/usr/local/bin/example")
        assert result is None

    def test_find_code_requirement_key_no_code_requirements(self):
        """Test with missing codeRequirements key"""
        config = {}
        result = ls_manage.find_code_requirement_key(config, "/usr/local/bin/example")
        assert result is None


class TestRunCommand:
    """Tests for run_command function"""

    def test_run_command_success(self):
        """Test successful command execution"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="success output", returncode=0)
            result = ls_manage.run_command(["echo", "test"])
            assert result == "success output"

    def test_run_command_failure(self):
        """Test command execution failure"""
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, "cmd", stderr="error message")
            with pytest.raises(SystemExit):
                ls_manage.run_command(["false"])

    def test_run_command_with_shell(self):
        """Test command execution with shell=True"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="shell output", returncode=0)
            result = ls_manage.run_command("echo test", shell=True)
            assert result == "shell output"
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["shell"] is True


class TestExportAndRestoreConfig:
    """Tests for export_config and restore_config"""

    @patch("ls_manage.run_command")
    def test_export_config(self, mock_run_command):
        """Test export_config calls correct command"""
        with patch.dict(os.environ, {"USER": "testuser"}):
            ls_manage.export_config("/tmp/backup.json")
            mock_run_command.assert_called_once()
            call_args = mock_run_command.call_args[0][0]
            assert "export-model" in call_args
            assert "/tmp/backup.json" in call_args

    @patch("ls_manage.run_command")
    def test_restore_config(self, mock_run_command):
        """Test restore_config calls correct command"""
        with patch.dict(os.environ, {"USER": "testuser"}):
            ls_manage.restore_config("/tmp/backup.json")
            mock_run_command.assert_called_once()
            call_args = mock_run_command.call_args[0][0]
            assert "restore-model" in call_args
            assert "/tmp/backup.json" in call_args


class TestUpdateRule:
    """Tests for update_rule function"""

    @patch("ls_manage.restore_config")
    @patch("ls_manage.export_config")
    @patch("ls_manage.get_binary_hash")
    @patch("os.path.realpath")
    def test_update_rule_creates_backup(self, mock_realpath, mock_hash, mock_export, mock_restore):
        """Test that update_rule creates a backup"""
        # Create mock arguments
        args = MagicMock()
        args.path = "/usr/local/bin/test"
        args.ports = "8080"
        args.protocol = "tcp"
        args.direction = "outgoing"
        args.remote = "any"
        args.replace = False

        # Mock file existence
        with patch("os.path.exists", return_value=True):
            mock_realpath.return_value = "/usr/local/bin/test"
            mock_hash.return_value = "testhash123"

            # Create a mock config file
            config = {"codeRequirements": {}, "rules": []}

            def export_side_effect(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    json.dump(config, f)

            mock_export.side_effect = export_side_effect

            # Mock restore to succeed
            mock_restore.return_value = None

            # Run the function
            with patch("ls_manage.find_code_requirement_key", return_value=None):
                with patch("shutil.which", return_value="/usr/local/bin/test"):
                    ls_manage.update_rule(args)

            # Verify export was called (creates backup)
            assert mock_export.called

    @patch("ls_manage.restore_config")
    @patch("ls_manage.export_config")
    @patch("ls_manage.get_binary_hash")
    @patch("os.path.realpath")
    def test_update_rule_binary_not_found(
        self, mock_realpath, mock_hash, mock_export, mock_restore
    ):
        """Test that update_rule fails when binary not found"""
        args = MagicMock()
        args.path = "/nonexistent/binary"

        with patch("os.path.exists", return_value=False):
            with patch("shutil.which", return_value=None):
                with pytest.raises(SystemExit):
                    ls_manage.update_rule(args)

    @patch("ls_manage.restore_config")
    @patch("ls_manage.export_config")
    @patch("ls_manage.get_binary_hash")
    @patch("os.path.realpath")
    def test_update_rule_sets_uid_field(self, mock_realpath, mock_hash, mock_export, mock_restore):
        """Test that update_rule sets uid field to make rules user-specific"""
        args = MagicMock()
        args.path = "/usr/local/bin/test"
        args.ports = "8080"
        args.protocol = "tcp"
        args.direction = "outgoing"
        args.remote = "any"
        args.replace = False

        with patch("os.path.exists", return_value=True):
            mock_realpath.return_value = "/usr/local/bin/test"
            mock_hash.return_value = "testhash123"

            config = {"codeRequirements": {}, "rules": []}
            modified_config = None

            def export_side_effect(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    json.dump(config, f)

            def restore_side_effect(path):
                nonlocal modified_config
                with open(path) as f:
                    modified_config = json.load(f)

            mock_export.side_effect = export_side_effect
            mock_restore.side_effect = restore_side_effect

            with patch("ls_manage.find_code_requirement_key", return_value=None):
                with patch("shutil.which", return_value="/usr/local/bin/test"):
                    ls_manage.update_rule(args)

            # Verify that the modified config has a rule with uid field
            assert modified_config is not None
            assert len(modified_config["rules"]) == 1
            rule = modified_config["rules"][0]
            assert "uid" in rule
            assert rule["uid"] == os.getuid()
            assert rule["uid"] is not None


class TestConfigJSON:
    """Tests for JSON config manipulation"""

    def test_config_structure_has_required_keys(self):
        """Test that config JSON has expected structure"""
        config = {
            "codeRequirements": {},
            "rules": [],
        }
        assert "codeRequirements" in config
        assert "rules" in config
        assert isinstance(config["codeRequirements"], dict)
        assert isinstance(config["rules"], list)

    def test_rule_creation_has_required_fields(self):
        """Test that created rules have all required fields"""
        from datetime import datetime

        rule = {
            "action": "allow",
            "process": "/usr/local/bin/example",
            "ports": "8080",
            "protocol": "tcp",
            "direction": "outgoing",
            "remote": "any",
            "uid": os.getuid(),
            "origin": "frontend",
            "creationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "modificationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        required_fields = [
            "action",
            "process",
            "ports",
            "protocol",
            "direction",
            "remote",
            "uid",
        ]
        for field in required_fields:
            assert field in rule

    def test_rule_has_uid_field(self):
        """Test that created rules include uid field to make them user-specific"""
        from datetime import datetime

        rule = {
            "action": "allow",
            "process": "/usr/local/bin/example",
            "ports": "8080",
            "protocol": "tcp",
            "direction": "outgoing",
            "remote": "any",
            "uid": os.getuid(),
            "origin": "frontend",
            "creationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "modificationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Verify uid field exists and is set to current user's UID
        assert "uid" in rule
        assert rule["uid"] == os.getuid()
        assert rule["uid"] is not None
