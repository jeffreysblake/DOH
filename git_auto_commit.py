#!/usr/bin/env python3
"""
Git Auto-Commit Monitor
A lightweight script to check git diffs and auto-commit when threshold is exceeded.
Designed to be run periodically via cron for minimal resource usage.
"""

import os
import sys
import subprocess
import argparse
import datetime
import json
import logging
from pathlib import Path

class GitAutoCommitMonitor:
    def __init__(self, repo_path, threshold=50, config_file=None):
        self.repo_path = Path(repo_path).resolve()
        self.threshold = threshold
        self.config_file = config_file or self.repo_path / '.auto_commit_config.json'
        
        # Set up logging
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f'auto_commit_{datetime.date.today().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def is_git_repo(self):
        """Check if the directory is a git repository."""
        try:
            subprocess.run(['git', '-C', str(self.repo_path), 'rev-parse', '--git-dir'], 
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_git_diff_stats(self):
        """Get git diff statistics."""
        try:
            # Check if there are any changes
            result = subprocess.run(['git', '-C', str(self.repo_path), 'diff', '--quiet', 'HEAD'], 
                                  capture_output=True)
            
            if result.returncode == 0:
                # No changes
                return {
                    'total_changes': 0,
                    'added': 0,
                    'deleted': 0,
                    'files_changed': 0,
                    'has_changes': False
                }
            
            # Get numstat for detailed changes
            result = subprocess.run(['git', '-C', str(self.repo_path), 'diff', '--numstat', 'HEAD'], 
                                  capture_output=True, text=True, check=True)
            
            added = deleted = files_changed = 0
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        line_added = int(parts[0]) if parts[0] != '-' else 0
                        line_deleted = int(parts[1]) if parts[1] != '-' else 0
                        added += line_added
                        deleted += line_deleted
                        files_changed += 1
                    except ValueError:
                        # Binary files show as '-', skip them
                        files_changed += 1
            
            total_changes = added + deleted
            
            return {
                'total_changes': total_changes,
                'added': added,
                'deleted': deleted,
                'files_changed': files_changed,
                'has_changes': True
            }
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error getting git diff stats: {e}")
            return None

    def get_untracked_files(self):
        """Get count of untracked files."""
        try:
            result = subprocess.run(['git', '-C', str(self.repo_path), 'ls-files', '--others', '--exclude-standard'], 
                                  capture_output=True, text=True, check=True)
            untracked = [f for f in result.stdout.strip().split('\n') if f]
            return len(untracked)
        except subprocess.CalledProcessError:
            return 0

    def create_commit_message(self, stats):
        """Create a detailed commit message."""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"Auto-commit: Snapshot at {timestamp}\n\n"
        message += f"Changes detected:\n"
        message += f"- Lines added: {stats['added']}\n"
        message += f"- Lines deleted: {stats['deleted']}\n"
        message += f"- Total changes: {stats['total_changes']}\n"
        message += f"- Files modified: {stats['files_changed']}\n\n"
        message += f"Threshold exceeded ({stats['total_changes']} > {self.threshold} lines)"
        
        return message

    def perform_commit(self, stats):
        """Perform the actual git commit."""
        try:
            # Stage all changes
            subprocess.run(['git', '-C', str(self.repo_path), 'add', '.'], 
                         check=True, capture_output=True)
            
            # Create commit message
            commit_msg = self.create_commit_message(stats)
            
            # Commit
            subprocess.run(['git', '-C', str(self.repo_path), 'commit', '-m', commit_msg], 
                         check=True, capture_output=True)
            
            self.logger.info(f"✓ Auto-commit successful: +{stats['added']}/-{stats['deleted']} lines across {stats['files_changed']} files")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"✗ Failed to commit changes: {e}")
            return False

    def load_config(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def save_config(self, config):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            self.logger.warning(f"Could not save config: {e}")

    def check_and_commit(self):
        """Main method to check changes and commit if threshold exceeded."""
        if not self.is_git_repo():
            self.logger.error(f"Directory {self.repo_path} is not a git repository")
            return False

        # Get current stats
        stats = self.get_git_diff_stats()
        if stats is None:
            return False

        untracked_count = self.get_untracked_files()
        
        if not stats['has_changes'] and untracked_count == 0:
            self.logger.info("No changes detected")
            return True

        total_changes = stats['total_changes']
        
        if total_changes >= self.threshold:
            self.logger.info(f"Threshold exceeded: {total_changes} changes (threshold: {self.threshold})")
            return self.perform_commit(stats)
        else:
            self.logger.info(f"Changes detected: {total_changes} lines (+{stats['added']}/-{stats['deleted']}) "
                           f"in {stats['files_changed']} files, {untracked_count} untracked (below threshold)")
            return True

def main():
    parser = argparse.ArgumentParser(description='Git Auto-Commit Monitor')
    parser.add_argument('repo_path', nargs='?', default='.', 
                       help='Path to git repository (default: current directory)')
    parser.add_argument('-t', '--threshold', type=int, default=50,
                       help='Lines changed threshold for auto-commit (default: 50)')
    parser.add_argument('-c', '--config', 
                       help='Path to config file (default: .auto_commit_config.json in repo)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    monitor = GitAutoCommitMonitor(args.repo_path, args.threshold, args.config)
    
    try:
        success = monitor.check_and_commit()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        monitor.logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        monitor.logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
