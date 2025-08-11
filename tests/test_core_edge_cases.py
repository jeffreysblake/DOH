#!/usr/bin/env python3
"""
Additional test suite for DOH Core module edge cases
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from doh.core import DohCore


class TestCoreEdgeCases:
    """Test edge cases and error handling in core module"""
    
    def setup_method(self, method):
        """Set up each test with a temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def teardown_method(self, method):
        """Clean up after each test"""
        os.chdir(self.original_cwd)
        # Clean up test directory
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_core_without_click(self):
        """Test core fallback when click is not available"""
        original_modules = sys.modules.copy()
        
        try:
            # Remove click and doh.core to force reimport
            for module in ['click', 'doh.core']:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Mock click import to raise ImportError
            with patch.dict('sys.modules', {'click': None}):
                # Import should work with MockClick fallback
                import doh.core
                assert hasattr(doh.core, 'click')
                
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_add_directory_validation(self):
        """Test add_directory with various invalid inputs"""
        doh = DohCore()
        
        # Test with non-existent directory
        fake_dir = self.test_dir / "nonexistent"
        result = doh.add_directory(fake_dir, threshold=50, name="test")
        assert result is False
        
        # Test with file instead of directory
        test_file = self.test_dir / "test_file"
        test_file.write_text("content")
        result = doh.add_directory(test_file, threshold=50, name="test")
        assert result is False
    
    def test_exclusion_edge_cases(self):
        """Test exclusion system edge cases"""
        doh = DohCore()
        
        # Test excluding non-existent directory
        fake_dir = self.test_dir / "nonexistent"
        result = doh.add_exclusion(fake_dir)
        assert result is True  # Should still add to exclusions
        
        # Test with relative paths
        relative_dir = Path("../relative/path")
        result = doh.add_exclusion(relative_dir)
        assert result is True
    
    def test_remove_directory_edge_cases(self):
        """Test remove_directory with edge cases"""
        doh = DohCore()
        
        # Test removing non-monitored directory
        test_dir = self.test_dir / "not_monitored"
        test_dir.mkdir()
        
        result = doh.remove_directory(test_dir)
        assert result is False
        
        # Test removing with relative path
        result = doh.remove_directory(Path("../nonexistent"))
        assert result is False
    
    def test_remove_exclusion_edge_cases(self):
        """Test remove_exclusion with edge cases"""
        doh = DohCore()
        
        # Test removing non-excluded directory
        test_dir = self.test_dir / "not_excluded"
        test_dir.mkdir()
        
        result = doh.remove_exclusion(test_dir)
        assert result is False
    
    def test_is_excluded_with_nested_paths(self):
        """Test is_excluded with complex nested paths"""
        doh = DohCore()
        
        # Create nested directory structure
        parent_dir = self.test_dir / "parent"
        child_dir = parent_dir / "child" / "grandchild"
        child_dir.mkdir(parents=True)
        
        # Add parent to exclusions
        doh.add_exclusion(parent_dir)
        
        # Child should be excluded due to parent exclusion
        assert doh.is_excluded(child_dir) is True
        
        # Test find_excluded_parent
        excluded_parent = doh.find_excluded_parent(child_dir)
        assert excluded_parent == parent_dir.resolve()
    
    def test_config_error_handling(self):
        """Test handling of config save/load errors"""
        doh = DohCore()
        
        # Mock config save to fail
        with patch.object(doh.config, 'save') as mock_save:
            mock_save.side_effect = Exception("Save failed")
            
            # Should handle error gracefully
            test_dir = self.test_dir / "test_dir"
            test_dir.mkdir()
            
            # This might still fail, but should attempt the operation
            try:
                result = doh.add_directory(test_dir, threshold=50, name="test")
            except Exception:
                pass  # Expected due to mocked failure
            
            assert mock_save.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
