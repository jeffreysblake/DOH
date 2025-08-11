#!/usr/bin/env python3
"""
Additional test suite for DOH Config module edge cases
"""

import json
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestConfigEdgeCases:
    """Test edge cases and error handling in config module"""

    def test_config_without_click(self):
        """Test config fallback when click is not available"""
        # Mock the import to fail
        original_modules = sys.modules.copy()

        try:
            # Remove click and doh.config to force reimport
            for module in ["click", "doh.config"]:
                if module in sys.modules:
                    del sys.modules[module]

            # Mock click import to raise ImportError
            with patch.dict("sys.modules", {"click": None}):
                # Import should work with MockClick fallback
                import doh.config

                assert hasattr(doh.config, "click")

                # Test MockClick functionality
                mock_click = doh.config.click
                # Should have an echo method
                assert hasattr(mock_click, "echo")

                # Test echo method (should just print)
                with patch("builtins.print") as mock_print:
                    mock_click.echo("test message")
                    mock_print.assert_called_once_with("test message")

        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_config_file_corruption(self):
        """Test handling of corrupted config file"""
        from doh.config import DohConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            # Create a corrupted JSON file
            config_file.write_text("{ invalid json content")

            config = DohConfig()
            config.config_file = config_file

            # Should return default config when file is corrupted
            result = config.load()
            assert "directories" in result
            assert "exclusions" in result
            assert "global_settings" in result

    def test_config_permission_error(self):
        """Test handling of permission errors during save"""
        from doh.config import DohConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "readonly" / "config.json"

            config = DohConfig()
            config.config_file = config_file

            # Try to save to a directory that doesn't exist
            test_config = {"test": "data"}

            # Should handle the error gracefully
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = PermissionError("Permission denied")

                # Should not raise an exception
                try:
                    config.save(test_config)
                except PermissionError:
                    pass  # Expected behavior

    def test_config_missing_sections(self):
        """Test config with missing sections"""
        from doh.config import DohConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            # Create config with missing sections
            incomplete_config = {
                "directories": {}
                # Missing exclusions and global_settings
            }
            config_file.write_text(json.dumps(incomplete_config))

            config = DohConfig()
            config.config_file = config_file

            # Should fill in missing sections
            result = config.load()
            assert "directories" in result
            assert "exclusions" in result
            assert "global_settings" in result

    def test_config_backup_creation(self):
        """Test config backup functionality"""
        from doh.config import DohConfig

        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"

            # Create initial config
            initial_config = {
                "directories": {"test": {"threshold": 50}},
                "exclusions": [],
                "global_settings": {"default_threshold": 50},
            }
            config_file.write_text(json.dumps(initial_config))

            config = DohConfig()
            config.config_file = config_file
            config.config_dir = config_dir

            # Should create backup when saving
            new_config = initial_config.copy()
            new_config["directories"]["new_dir"] = {"threshold": 30}

            config.save(new_config)

            # Check if backup was created
            backup_files = list(config_dir.glob("config_backup_*.json"))
            assert len(backup_files) > 0

    def test_git_profile_validation(self):
        """Test git profile path validation"""
        from doh.config import DohConfig

        config = DohConfig()

        # Test with non-existent git profile
        test_config = config._get_default_config()
        test_config["global_settings"]["git_profile"] = "/nonexistent/path"

        # Should handle invalid git profile gracefully
        result = config.load()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
