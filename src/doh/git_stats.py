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
            # Count untracked files and lines
            untracked_info = GitStats._get_untracked_info(directory)
            
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
                    'untracked': untracked_info['file_count'],
                    'untracked_lines': untracked_info['line_count']
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
                'untracked': untracked_info['file_count'],
                'untracked_lines': untracked_info['line_count']
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
    def _get_untracked_info(directory: Path) -> dict:
        """Get info about untracked files (count and total lines)"""
        try:
            # Get list of untracked files
            result = subprocess.run(
                ['git', '-C', str(directory), 'ls-files', '--others', '--exclude-standard'],
                capture_output=True, text=True, check=True
            )
            
            untracked_files = [line for line in result.stdout.strip().split('\n') if line]
            if not untracked_files:
                return {'file_count': 0, 'line_count': 0}
            
            total_lines = 0
            for file_path in untracked_files:
                full_path = directory / file_path
                try:
                    # Only count text files, skip binary files
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        total_lines += lines
                except (OSError, UnicodeDecodeError, PermissionError):
                    # Skip files we can't read or binary files
                    # But still count them as 1 line each so they're not ignored
                    total_lines += 1
                    
            return {'file_count': len(untracked_files), 'line_count': total_lines}
        except subprocess.CalledProcessError:
            return {'file_count': 0, 'line_count': 0}

    @staticmethod
    def _count_untracked(directory: Path) -> int:
        """Count lines in untracked files"""
        try:
            # Get list of untracked files
            result = subprocess.run(
                ['git', '-C', str(directory), 'ls-files', '--others', '--exclude-standard'],
                capture_output=True, text=True, check=True
            )
            
            untracked_files = [line for line in result.stdout.strip().split('\n') if line]
            if not untracked_files:
                return 0
            
            total_lines = 0
            for file_path in untracked_files:
                full_path = directory / file_path
                try:
                    # Only count text files, skip binary files
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        total_lines += lines
                except (OSError, UnicodeDecodeError, PermissionError):
                    # Skip files we can't read or binary files
                    # But still count them as 1 line each so they're not ignored
                    total_lines += 1
                    
            return total_lines
        except subprocess.CalledProcessError:
            return 0
