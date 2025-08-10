"""
Git repository statistics gathering
"""

import subprocess
from datetime import datetime
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
                # New repository with no commits - check for staged files too
                file_stats = []
                
                # Add untracked files
                for file_path, line_count in untracked_info.get('file_details', []):
                    file_stats.append({
                        'file': file_path,
                        'added': line_count,
                        'deleted': 0,
                        'status': 'new'
                    })
                
                # Check for staged files (new files ready to commit)
                staged_info = GitStats._get_staged_new_files_info(directory)
                for file_path, line_count in staged_info.get('file_details', []):
                    file_stats.append({
                        'file': file_path,
                        'added': line_count,
                        'deleted': 0,
                        'status': 'new'
                    })
                
                total_new_lines = untracked_info['line_count'] + staged_info['line_count']
                
                return {
                    'total_changes': staged_info['line_count'],  # Staged files count as changes
                    'added': staged_info['line_count'],
                    'deleted': 0,
                    'files_changed': staged_info['file_count'],
                    'untracked': untracked_info['file_count'],
                    'untracked_lines': untracked_info['line_count'],
                    'file_stats': file_stats
                }
            
            # Get detailed stats for tracked file changes
            result = subprocess.run(
                ['git', '-C', str(directory), 'diff', '--numstat', 'HEAD'],
                capture_output=True, text=True, check=True
            )
            
            added = deleted = files_changed = 0
            file_stats = []
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        try:
                            file_added = 0 if parts[0] == '-' else int(parts[0])
                            file_deleted = 0 if parts[1] == '-' else int(parts[1])
                            file_path = parts[2]
                            
                            added += file_added
                            deleted += file_deleted
                            files_changed += 1
                            
                            # Determine file status
                            if file_added > 0 and file_deleted == 0:
                                status = 'modified' if file_added < 50 else 'added'  # Heuristic for new vs modified
                            elif file_deleted > 0 and file_added == 0:
                                status = 'deleted'
                            else:
                                status = 'modified'
                            
                            file_stats.append({
                                'file': file_path,
                                'added': file_added,
                                'deleted': file_deleted,
                                'status': status
                            })
                        except ValueError:
                            continue
            
            # Add untracked files to file_stats
            for file_path, line_count in untracked_info.get('file_details', []):
                file_stats.append({
                    'file': file_path,
                    'added': line_count,
                    'deleted': 0,
                    'status': 'new'
                })
            
            return {
                'total_changes': added + deleted,
                'added': added,
                'deleted': deleted,
                'files_changed': files_changed,
                'untracked': untracked_info['file_count'],
                'untracked_lines': untracked_info['line_count'],
                'file_stats': file_stats
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
                return {'file_count': 0, 'line_count': 0, 'file_details': []}
            
            total_lines = 0
            file_details = []
            
            for file_path in untracked_files:
                full_path = directory / file_path
                try:
                    # Only count text files, skip binary files
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        total_lines += lines
                        file_details.append((file_path, lines))
                except (OSError, UnicodeDecodeError, PermissionError):
                    # Skip files we can't read or binary files
                    # But still count them as 1 line each so they're not ignored
                    total_lines += 1
                    file_details.append((file_path, 1))
                    
            return {
                'file_count': len(untracked_files), 
                'line_count': total_lines,
                'file_details': file_details
            }
        except subprocess.CalledProcessError:
            return {'file_count': 0, 'line_count': 0, 'file_details': []}

    @staticmethod
    def _get_staged_new_files_info(directory: Path) -> dict:
        """Get info about staged new files (files that are staged but not yet committed)"""
        try:
            # Get list of staged files
            result = subprocess.run(
                ['git', '-C', str(directory), 'diff', '--staged', '--name-only'],
                capture_output=True, text=True, check=True
            )
            
            staged_files = [line for line in result.stdout.strip().split('\n') if line]
            if not staged_files:
                return {'file_count': 0, 'line_count': 0, 'file_details': []}
            
            total_lines = 0
            file_details = []
            
            for file_path in staged_files:
                full_path = directory / file_path
                try:
                    # Only count text files, skip binary files
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = sum(1 for _ in f)
                        total_lines += lines
                        file_details.append((file_path, lines))
                except (OSError, UnicodeDecodeError, PermissionError):
                    # Skip files we can't read or binary files
                    # But still count them as 1 line each so they're not ignored
                    total_lines += 1
                    file_details.append((file_path, 1))
                    
            return {
                'file_count': len(staged_files), 
                'line_count': total_lines,
                'file_details': file_details
            }
        except subprocess.CalledProcessError:
            return {'file_count': 0, 'line_count': 0, 'file_details': []}

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

    @staticmethod
    def format_file_changes(file_stats: list, max_files: int = 5) -> str:
        """Format file changes for commit messages using git diff notation"""
        if not file_stats:
            return "No file changes detected"
        
        # Sort by total changes (added + deleted) descending
        sorted_files = sorted(file_stats, 
                            key=lambda f: f['added'] + f['deleted'], 
                            reverse=True)
        
        formatted_files = []
        for file_info in sorted_files[:max_files]:
            file_path = file_info['file']
            added = file_info['added']
            deleted = file_info['deleted']
            status = file_info['status']
            
            # Format based on change type
            if status == 'new':
                formatted_files.append(f"{file_path} (+{added})")
            elif status == 'deleted':
                formatted_files.append(f"{file_path} (-{deleted})")
            elif added > 0 and deleted > 0:
                formatted_files.append(f"{file_path} (+{added}/-{deleted})")
            elif added > 0:
                formatted_files.append(f"{file_path} (~{added})")
            elif deleted > 0:
                formatted_files.append(f"{file_path} (-{deleted})")
            else:
                formatted_files.append(f"{file_path} (modified)")
        
        result = ", ".join(formatted_files)
        
        # Add summary if there are more files
        if len(file_stats) > max_files:
            remaining = len(file_stats) - max_files
            result += f", +{remaining} more files"
        
        return result

    @staticmethod
    def create_enhanced_commit_message(name: str, stats: dict, threshold: int) -> str:
        """Create an enhanced commit message with per-file statistics"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_changes = stats['total_changes'] + stats.get('untracked_lines', stats['untracked'])
        
        # Create short summary for commit title
        file_summary = GitStats.format_file_changes(stats.get('file_stats', []), max_files=3)
        
        # Commit title (first line)
        commit_title = f"Auto-commit: {file_summary}"
        
        # Detailed commit body
        commit_body = f"""
Project: {name}
Timestamp: {timestamp}
Threshold: {threshold} lines (exceeded with {total_changes} changes)

File Changes:
{GitStats.format_file_changes(stats.get('file_stats', []), max_files=10)}

Summary:
- Lines added: {stats['added']}
- Lines deleted: {stats['deleted']}
- Total line changes: {stats['total_changes']}
- Files modified: {stats['files_changed']}
- Untracked files: {stats['untracked']}

Auto-committed by DOH monitoring system.
"""
        
        return commit_title + commit_body

    @staticmethod
    def get_or_create_temp_branch(directory: Path, prefix: str = "doh-auto-commits") -> str:
        """Get existing temp branch or create a new one"""
        try:
            # Check if we're already on a temp branch
            current_branch = subprocess.run(
                ['git', '-C', str(directory), 'branch', '--show-current'],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            if current_branch.startswith(prefix):
                return current_branch
            
            # Look for existing temp branches
            result = subprocess.run(
                ['git', '-C', str(directory), 'branch', '--list', f'{prefix}-*'],
                capture_output=True, text=True, check=True
            )
            
            existing_branches = [line.strip().replace('* ', '') for line in result.stdout.strip().split('\n') if line.strip()]
            
            if existing_branches:
                # Use the most recent temp branch (last in alphabetical order due to timestamp)
                latest_branch = sorted(existing_branches)[-1]
                return latest_branch
            
            # Create new temp branch with timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            branch_name = f"{prefix}-{timestamp}"
            
            # Create and checkout new branch
            subprocess.run(
                ['git', '-C', str(directory), 'checkout', '-b', branch_name],
                capture_output=True, check=True
            )
            
            return branch_name
            
        except subprocess.CalledProcessError:
            # Fallback to current branch if temp branch creation fails
            return "main"  # or whatever the default branch is

    @staticmethod
    def switch_to_temp_branch(directory: Path, branch_name: str) -> bool:
        """Switch to the specified temp branch"""
        try:
            subprocess.run(
                ['git', '-C', str(directory), 'checkout', branch_name],
                capture_output=True, check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def list_temp_branches(directory: Path, prefix: str = "doh-auto-commits") -> list:
        """List all temp branches in the repository"""
        try:
            result = subprocess.run(
                ['git', '-C', str(directory), 'branch', '--list', f'{prefix}-*'],
                capture_output=True, text=True, check=True
            )
            
            branches = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    branch = line.strip().replace('* ', '')
                    # Get commit count and last commit info
                    try:
                        commit_count = subprocess.run(
                            ['git', '-C', str(directory), 'rev-list', '--count', branch],
                            capture_output=True, text=True, check=True
                        ).stdout.strip()
                        
                        last_commit = subprocess.run(
                            ['git', '-C', str(directory), 'log', '-1', '--format=%cr', branch],
                            capture_output=True, text=True, check=True
                        ).stdout.strip()
                        
                        branches.append({
                            'name': branch,
                            'commit_count': int(commit_count),
                            'last_commit': last_commit
                        })
                    except subprocess.CalledProcessError:
                        branches.append({
                            'name': branch,
                            'commit_count': 0,
                            'last_commit': 'unknown'
                        })
            
            return branches
            
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def squash_temp_commits(directory: Path, target_branch: str, commit_message: str, temp_branch: Optional[str] = None) -> bool:
        """Squash temp branch commits into target branch with a proper commit message"""
        try:
            if not temp_branch:
                # Find the current temp branch
                current_branch = subprocess.run(
                    ['git', '-C', str(directory), 'branch', '--show-current'],
                    capture_output=True, text=True, check=True
                ).stdout.strip()
                
                if not current_branch.startswith("doh-auto-commits"):
                    return False
                temp_branch = current_branch
            
            # Switch to target branch
            subprocess.run(
                ['git', '-C', str(directory), 'checkout', target_branch],
                capture_output=True, check=True
            )
            
            # Squash merge the temp branch
            subprocess.run(
                ['git', '-C', str(directory), 'merge', '--squash', temp_branch],
                capture_output=True, check=True
            )
            
            # Commit with the provided message
            subprocess.run(
                ['git', '-C', str(directory), 'commit', '-m', commit_message],
                capture_output=True, check=True
            )
            
            # Delete the temp branch
            subprocess.run(
                ['git', '-C', str(directory), 'branch', '-D', temp_branch],
                capture_output=True, check=True
            )
            
            return True
            
        except subprocess.CalledProcessError:
            return False
