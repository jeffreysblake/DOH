"""
Git repository statistics gathering
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional

class GitStats:
    """Handles git repository statistics"""
    
    @staticmethod
    def get_stats(directory: Path) -> Optional[Dict]:
        """Get git statistics for a directory"""
        if not GitStats.is_git_repo(directory):
            return None
        
        try:
            # Count untracked files first
            untracked_count = GitStats._count_untracked(directory)
            
            # Check if HEAD exists (repository has commits)
            head_exists = subprocess.run(
                ['git', '-C', str(directory), 'rev-parse', '--verify', 'HEAD'],
                capture_output=True, check=False
            ).returncode == 0
            
            if not head_exists:
                # New repository with no commits - only untracked files matter
                return {
                    'total_changes': 0,
                    'added': 0,
                    'deleted': 0,
                    'files_changed': 0,
                    'untracked': untracked_count
                }
            
            # Get detailed stats for tracked file changes
            result = subprocess.run(
                ['git', '-C', str(directory), 'diff', '--numstat', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            
            added = deleted = files_changed = 0
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            if parts[0] != '-':
                                added += int(parts[0])
                            if parts[1] != '-':
                                deleted += int(parts[1])
                            files_changed += 1
                        except ValueError:
                            continue
            
            return {
                'total_changes': added + deleted,
                'added': added,
                'deleted': deleted,
                'files_changed': files_changed,
                'untracked': untracked_count
            }
            
        except subprocess.CalledProcessError:
            return None
    
    @staticmethod
    def is_git_repo(directory: Path) -> bool:
        """Check if directory is a git repository"""
        try:
            subprocess.run(
                ['git', '-C', str(directory), 'rev-parse', '--git-dir'],
                capture_output=True, check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def _count_untracked(directory: Path) -> int:
        """Count untracked files"""
        try:
            result = subprocess.run(
                ['git', '-C', str(directory), 'ls-files', '--others', '--exclude-standard'],
                capture_output=True, text=True, check=True
            )
            return len([line for line in result.stdout.strip().split('\n') if line])
        except subprocess.CalledProcessError:
            return 0
