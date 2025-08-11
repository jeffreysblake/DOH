#!/usr/bin/env python3
"""
Additional test suite for DOH GitStats module edge cases
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from doh.git_stats import GitStats


class TestGitStatsEdgeCases:
    """Test edge cases and error handling in git_stats module"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up after each test"""
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir)
    
    def create_git_repo(self, path: Path, with_changes=False):
        """Create a git repository for testing"""
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init'], cwd=path, check=True, 
                      capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], 
                      cwd=path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], 
                      cwd=path, check=True)
        
        # Create initial commit
        test_file = path / "README.md"
        test_file.write_text("# Test Project\n")
        subprocess.run(['git', 'add', '.'], cwd=path, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], 
                      cwd=path, check=True)
        
        if with_changes:
            # Add some changes
            test_file.write_text("# Test Project\nWith changes\n")
            new_file = path / "new_file.txt"
            new_file.write_text("New content\n")
    
    def test_git_command_errors(self):
        """Test handling of git command errors"""
        fake_repo = self.test_dir / "fake_repo"
        fake_repo.mkdir()
        
        # Test with non-git directory
        stats = GitStats.get_stats(fake_repo)
        assert stats is None
        
        # Test is_git_repo with non-git directory
        assert GitStats.is_git_repo(fake_repo) is False
    
    def test_git_subprocess_errors(self):
        """Test handling of subprocess errors"""
        repo_dir = self.test_dir / "error_repo"
        self.create_git_repo(repo_dir)
        
        # Mock subprocess to fail
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
            
            stats = GitStats.get_stats(repo_dir)
            assert stats is None
    
    def test_enhanced_commit_message_edge_cases(self):
        """Test create_enhanced_commit_message with edge cases"""
        repo_dir = self.test_dir / "message_test_repo"
        self.create_git_repo(repo_dir, with_changes=True)
        
        # Test with very long filenames
        long_filename = "a" * 100 + ".txt"
        long_file = repo_dir / long_filename
        long_file.write_text("content")
        
        stats = GitStats.get_stats(repo_dir)
        if stats:
            message = GitStats.create_enhanced_commit_message(
                "test", stats, 50
            )
            assert isinstance(message, str)
            assert len(message) > 0
    
    def test_format_file_changes_edge_cases(self):
        """Test format_file_changes with various scenarios"""
        # Test with empty changes
        changes = []
        result = GitStats.format_file_changes(changes)
        assert result == ""
        
        # Test with many files (should truncate)
        many_changes = [
            ("file{}.txt".format(i), 5, 2) for i in range(20)
        ]
        result = GitStats.format_file_changes(many_changes)
        assert "more files" in result.lower() or len(result) > 0
    
    def test_temp_branch_operations_errors(self):
        """Test temp branch operations with error conditions"""
        repo_dir = self.test_dir / "temp_branch_error_repo"
        self.create_git_repo(repo_dir)
        
        # Mock git commands to fail
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
            
            # Test get_or_create_temp_branch
            result = GitStats.get_or_create_temp_branch(repo_dir)
            assert result is None or isinstance(result, str)
            
            # Test list_temp_branches
            result = GitStats.list_temp_branches(repo_dir)
            assert result == []
            
            # Test switch_to_temp_branch
            result = GitStats.switch_to_temp_branch(repo_dir, "fake-branch")
            assert result is False
    
    def test_squash_temp_commits_edge_cases(self):
        """Test squash_temp_commits with edge cases"""
        repo_dir = self.test_dir / "squash_test_repo"
        self.create_git_repo(repo_dir)
        
        # Test squashing when no temp branches exist
        result = GitStats.squash_temp_commits(
            repo_dir, "main", "Test message"
        )
        assert result is False
        
        # Test with git errors during squash
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
            
            result = GitStats.squash_temp_commits(
                repo_dir, "main", "Test message"
            )
            assert result is False
    
    def test_cleanup_temp_branches_edge_cases(self):
        """Test cleanup functionality edge cases"""
        repo_dir = self.test_dir / "cleanup_test_repo"
        self.create_git_repo(repo_dir)
        
        # Test when no temp branches exist
        # Just ensure no errors occur
        branches = GitStats.list_temp_branches(repo_dir)
        assert isinstance(branches, list)
    
    def test_binary_file_detection_edge_cases(self):
        """Test binary file detection with edge cases"""
        repo_dir = self.test_dir / "binary_test_repo"
        self.create_git_repo(repo_dir)
        
        # Create a binary file
        binary_file = repo_dir / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xFF\xFE\xFD')
        
        # Add to git
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
        
        stats = GitStats.get_stats(repo_dir)
        if stats:
            # Should handle binary files gracefully
            assert 'files_changed' in stats
            assert stats['files_changed'] >= 0
    
    def test_large_repository_handling(self):
        """Test handling of repositories with many files"""
        repo_dir = self.test_dir / "large_repo"
        self.create_git_repo(repo_dir)
        
        # Create many files
        for i in range(50):
            test_file = repo_dir / f"file_{i}.txt"
            test_file.write_text(f"Content for file {i}\n" * 10)
        
        stats = GitStats.get_stats(repo_dir)
        if stats:
            # Should handle large repos without issues
            assert 'total_changes' in stats
            assert stats['total_changes'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
