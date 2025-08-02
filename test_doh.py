#!/usr/bin/env python3
"""
Test suite for DOH (Directory Oh-no, Handle this!)
Comprehensive testing of all functionality
"""

import os
import shutil
import tempfile
import subprocess
import json
from pathlib import Path
import pytest

# Import our DOH classes
from doh import DohCore, DohConfig, GitStats

class TestDohSystem:
    """Test the DOH system"""
    
    @pytest.fixture
    def temp_env(self):
        """Create isolated test environment"""
        # Create temporary directory for tests
        test_dir = Path(tempfile.mkdtemp())
        
        # Save original config
        original_config_dir = Path.home() / ".doh"
        backup_config_dir = None
        if original_config_dir.exists():
            backup_config_dir = Path(tempfile.mkdtemp())
            shutil.copytree(original_config_dir, backup_config_dir / ".doh")
            shutil.rmtree(original_config_dir)
        
        # Set up test config
        test_config_dir = test_dir / ".doh"
        os.environ['HOME'] = str(test_dir)
        
        yield test_dir
        
        # Cleanup
        os.environ['HOME'] = str(Path.home().parent / Path.home().name)
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        # Restore original config
        if backup_config_dir and (backup_config_dir / ".doh").exists():
            if original_config_dir.exists():
                shutil.rmtree(original_config_dir)
            shutil.copytree(backup_config_dir / ".doh", original_config_dir)
            shutil.rmtree(backup_config_dir)
    
    def create_git_repo(self, path: Path):
        """Create a git repository at the given path"""
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init'], cwd=path, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=path, check=True)
    
    def test_basic_initialization(self, temp_env):
        """Test basic config initialization"""
        doh = DohCore()
        config = doh.config.load()
        
        assert config['version'] == '1.0'
        assert 'directories' in config
        assert 'exclusions' in config
        assert 'global_settings' in config
    
    def test_add_directory_to_monitoring(self, temp_env):
        """Test adding a directory to monitoring"""
        # Create git repo
        project_dir = temp_env / "project1"
        self.create_git_repo(project_dir)
        
        # Add some content
        (project_dir / "test.txt").write_text("Hello world")
        
        doh = DohCore()
        
        # Add to monitoring
        assert doh.add_directory(project_dir, 30, "TestProject")
        
        # Verify it's monitored
        assert doh.is_monitored(project_dir)
        
        # Check config
        config = doh.config.load()
        assert str(project_dir) in config['directories']
        assert config['directories'][str(project_dir)]['name'] == 'TestProject'
        assert config['directories'][str(project_dir)]['threshold'] == 30
    
    def test_exclusion_system(self, temp_env):
        """Test directory exclusion"""
        excluded_dir = temp_env / "excluded"
        excluded_dir.mkdir()
        
        doh = DohCore()
        
        # Add to exclusions
        assert doh.add_exclusion(excluded_dir)
        
        # Check if excluded
        assert doh.is_excluded(excluded_dir)
        
        # Check config
        config = doh.config.load()
        assert str(excluded_dir) in config['exclusions']
    
    def test_parent_directory_exclusion(self, temp_env):
        """Test that parent directory exclusion blocks child monitoring"""
        parent_dir = temp_env / "parent"
        child_dir = parent_dir / "child"
        
        # Create git repo in child
        self.create_git_repo(child_dir)
        
        doh = DohCore()
        
        # Exclude parent
        assert doh.add_exclusion(parent_dir)
        
        # Child should be excluded too
        assert doh.is_excluded(child_dir)
        assert doh.find_excluded_parent(child_dir) == parent_dir
        
        # Should not be able to add child to monitoring
        assert not doh.add_directory(child_dir, 25, "Child")
    
    def test_git_stats(self, temp_env):
        """Test git statistics gathering"""
        # Create git repo
        repo_dir = temp_env / "repo"
        self.create_git_repo(repo_dir)
        
        # Check if it's a git repo
        assert GitStats.is_git_repo(repo_dir)
        
        # Add some content and commit
        test_file = repo_dir / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_dir, check=True)
        
        # No changes yet
        stats = GitStats.get_stats(repo_dir)
        assert stats['total_changes'] == 0
        
        # Make some changes
        test_file.write_text("line1\nmodified line2\nline3\nline4\n")
        
        # Check stats
        stats = GitStats.get_stats(repo_dir)
        assert stats['total_changes'] > 0
        assert stats['files_changed'] == 1
    
    def test_config_backup(self, temp_env):
        """Test configuration backup system"""
        doh = DohCore()
        
        # Create initial config
        test_dir = temp_env / "test"
        test_dir.mkdir()
        doh.add_exclusion(test_dir)
        
        # Check backup was created
        config_file = doh.config.config_file
        backup_file = config_file.with_suffix('.json.backup.1')
        
        # Make another change to trigger backup rotation
        test_dir2 = temp_env / "test2"
        test_dir2.mkdir()
        doh.add_exclusion(test_dir2)
        
        # Backup should exist
        assert backup_file.exists()
    
    def test_smart_directory_adding(self, temp_env):
        """Test smart behavior when directory is already monitored"""
        # Create git repo
        project_dir = temp_env / "project"
        self.create_git_repo(project_dir)
        
        doh = DohCore()
        
        # Add directory
        assert doh.add_directory(project_dir, 25, "Project")
        
        # Should report as already monitored
        assert doh.is_monitored(project_dir)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
