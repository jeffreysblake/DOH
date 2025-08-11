#!/usr/bin/env python3
"""
Comprehensive test suite for DOH git statistics and temp branch functionality
"""

import os
import shutil
import tempfile
import subprocess
import json
from pathlib import Path
import pytest
from datetime import datetime

# Import our DOH classes
from doh import GitStats

class TestGitStats:
    """Test GitStats functionality including temp branches and enhanced commit messages"""
    
    @pytest.fixture
    def git_repo(self):
        """Create a temporary git repository for testing"""
        test_dir = Path(tempfile.mkdtemp())
        
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=test_dir, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=test_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=test_dir, check=True)
        
        # Create initial commit
        test_file = test_dir / "README.md"
        test_file.write_text("# Test Project\nInitial content\n")
        subprocess.run(['git', 'add', '.'], cwd=test_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=test_dir, check=True)
        
        yield test_dir
        
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    def test_is_git_repo(self, git_repo):
        """Test git repository detection"""
        assert GitStats.is_git_repo(git_repo)
        
        # Test non-git directory
        non_git_dir = Path(tempfile.mkdtemp())
        try:
            assert not GitStats.is_git_repo(non_git_dir)
        finally:
            shutil.rmtree(non_git_dir)
    
    def test_get_stats_clean_repo(self, git_repo):
        """Test stats for clean repository"""
        stats = GitStats.get_stats(git_repo)
        
        assert stats is not None
        assert stats['total_changes'] == 0
        assert stats['added'] == 0
        assert stats['deleted'] == 0
        assert stats['files_changed'] == 0
        assert stats['untracked'] == 0
    
    def test_get_stats_with_changes(self, git_repo):
        """Test stats with file modifications"""
        # Modify existing file
        readme = git_repo / "README.md"
        readme.write_text("# Test Project\nModified content\nNew line\n")
        
        # Add new file
        new_file = git_repo / "new_file.txt"
        new_file.write_text("New file content\nSecond line\n")
        
        stats = GitStats.get_stats(git_repo)
        
        assert stats['total_changes'] > 0
        assert stats['files_changed'] == 1  # Only tracked files count here
        assert stats['untracked'] == 1  # New file is untracked
        assert len(stats['file_stats']) == 2  # Both files in stats
    
    def test_format_file_changes(self, git_repo):
        """Test file change formatting for commit messages"""
        # Create various types of changes
        readme = git_repo / "README.md"
        readme.write_text("# Test Project\nModified content\n")
        
        new_file = git_repo / "new.txt"
        new_file.write_text("New file\n")
        
        stats = GitStats.get_stats(git_repo)
        formatted = GitStats.format_file_changes(stats['file_stats'])
        
        assert "new.txt (+1)" in formatted
        assert "README.md (~" in formatted or "README.md (+1/-1)" in formatted
    
    def test_create_enhanced_commit_message(self, git_repo):
        """Test enhanced commit message creation"""
        # Make changes
        readme = git_repo / "README.md"
        readme.write_text("# Test Project\nModified content\nAnother line\n")
        
        stats = GitStats.get_stats(git_repo)
        commit_msg = GitStats.create_enhanced_commit_message("TestProject", stats, 50)
        
        assert "Auto-commit:" in commit_msg
        assert "Project: TestProject" in commit_msg
        assert "Threshold: 50 lines" in commit_msg
        assert "File Changes:" in commit_msg
        assert "README.md" in commit_msg
        assert "Auto-committed by DOH monitoring system" in commit_msg
    
    def test_temp_branch_creation(self, git_repo):
        """Test temporary branch creation and management"""
        # Get or create temp branch
        branch_name = GitStats.get_or_create_temp_branch(git_repo)
        
        assert branch_name.startswith("doh-auto-commits-")
        
        # Check current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'], 
            cwd=git_repo, capture_output=True, text=True, check=True
        )
        current_branch = result.stdout.strip()
        assert current_branch == branch_name
    
    def test_temp_branch_reuse(self, git_repo):
        """Test that existing temp branch is reused"""
        # Create first temp branch
        branch1 = GitStats.get_or_create_temp_branch(git_repo)
        
        # Should reuse same branch
        branch2 = GitStats.get_or_create_temp_branch(git_repo)
        
        assert branch1 == branch2
    
    def test_list_temp_branches(self, git_repo):
        """Test listing temporary branches"""
        # Initially no temp branches
        branches = GitStats.list_temp_branches(git_repo)
        assert len(branches) == 0
        
        # Create temp branch
        GitStats.get_or_create_temp_branch(git_repo)
        
        # Should list the temp branch
        branches = GitStats.list_temp_branches(git_repo)
        assert len(branches) == 1
        assert branches[0]['name'].startswith("doh-auto-commits-")
        assert branches[0]['commit_count'] > 0
    
    def test_switch_to_temp_branch(self, git_repo):
        """Test switching to temp branch"""
        # Create temp branch
        temp_branch = GitStats.get_or_create_temp_branch(git_repo)
        
        # Switch back to master
        subprocess.run(['git', 'checkout', 'master'], cwd=git_repo, check=True)
        
        # Switch to temp branch
        assert GitStats.switch_to_temp_branch(git_repo, temp_branch)
        
        # Verify current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'], 
            cwd=git_repo, capture_output=True, text=True, check=True
        )
        current_branch = result.stdout.strip()
        assert current_branch == temp_branch
    
    def test_squash_temp_commits(self, git_repo):
        """Test squashing temp branch commits into main branch"""
        # Make changes and commit to temp branch
        temp_branch = GitStats.get_or_create_temp_branch(git_repo)
        
        # Make some commits on temp branch
        new_file = git_repo / "temp_changes.txt"
        new_file.write_text("Temp change 1\n")
        subprocess.run(['git', 'add', '.'], cwd=git_repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'Temp commit 1'], cwd=git_repo, check=True)
        
        new_file.write_text("Temp change 1\nTemp change 2\n")
        subprocess.run(['git', 'add', '.'], cwd=git_repo, check=True)
        subprocess.run(['git', 'commit', '-m', 'Temp commit 2'], cwd=git_repo, check=True)
        
        # Squash into master
        success = GitStats.squash_temp_commits(git_repo, 'master', 'Squashed temp changes')
        
        assert success
        
        # Should be back on master
        result = subprocess.run(
            ['git', 'branch', '--show-current'], 
            cwd=git_repo, capture_output=True, text=True, check=True
        )
        current_branch = result.stdout.strip()
        assert current_branch == 'master'
        
        # Temp branch should be deleted
        result = subprocess.run(
            ['git', 'branch', '--list', 'doh-auto-commits-*'], 
            cwd=git_repo, capture_output=True, text=True, check=True
        )
        assert temp_branch not in result.stdout
        
        # Changes should be in master
        assert (git_repo / "temp_changes.txt").exists()
    
    def test_untracked_files_handling(self, git_repo):
        """Test handling of untracked files in statistics"""
        # Create untracked files
        untracked1 = git_repo / "untracked1.txt"
        untracked1.write_text("Line 1\nLine 2\nLine 3\n")
        
        untracked2 = git_repo / "untracked2.txt"
        untracked2.write_text("Single line\n")
        
        stats = GitStats.get_stats(git_repo)
        
        assert stats['untracked'] == 2
        assert stats['untracked_lines'] == 4  # 3 + 1 lines
        
        # Check file stats include untracked files
        untracked_stats = [f for f in stats['file_stats'] if f['status'] == 'new']
        assert len(untracked_stats) == 2
    
    def test_staged_files_handling(self, git_repo):
        """Test handling of staged files in new repositories"""
        # Create new repo without initial commit
        new_repo = Path(tempfile.mkdtemp())
        try:
            subprocess.run(['git', 'init'], cwd=new_repo, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=new_repo, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=new_repo, check=True)
            
            # Add files without committing
            staged_file = new_repo / "staged.txt"
            staged_file.write_text("Staged content\n")
            subprocess.run(['git', 'add', '.'], cwd=new_repo, check=True)
            
            stats = GitStats.get_stats(new_repo)
            
            assert stats is not None
            assert stats['total_changes'] == 1  # Staged file counts as change
            assert len(stats['file_stats']) == 1
            assert stats['file_stats'][0]['status'] == 'new'
            
        finally:
            shutil.rmtree(new_repo)
    
    def test_binary_file_handling(self, git_repo):
        """Test that binary files are handled gracefully"""
        # Create a binary file (simulate with bytes that would cause UnicodeDecodeError)
        binary_file = git_repo / "binary.dat"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xFF\xFE\xFD')
        
        # Should not crash when getting stats
        stats = GitStats.get_stats(git_repo)
        
        assert stats is not None
        assert stats['untracked'] == 1
        assert stats['untracked_lines'] >= 1  # Binary files count as 1 line minimum

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
