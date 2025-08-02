  import time
    import subprocess
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class GitAutoCommitHandler(FileSystemEventHandler):
        def __init__(self, repo_path, commit_message="Auto-commit by watchdog"):
            self.repo_path = repo_path
            self.commit_message = commit_message
            self.last_commit_time = 0

        def on_modified(self, event):
            # Debounce to prevent multiple commits for rapid changes
            current_time = time.time()
            if current_time - self.last_commit_time < 5:  # Adjust debounce time as needed
                return

            if not event.is_directory:
                print(f"File modified: {event.src_path}")
                self.perform_git_commit()
                self.last_commit_time = current_time

        def on_created(self, event):
            if not event.is_directory:
                print(f"File created: {event.src_path}")
                self.perform_git_commit()

        def on_deleted(self, event):
            if not event.is_directory:
                print(f"File deleted: {event.src_path}")
                self.perform_git_commit()

        def perform_git_commit(self):
            try:
                # Add all changes
                subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
                # Commit changes
                subprocess.run(["git", "commit", "-m", self.commit_message], cwd=self.repo_path, check=True)
                print("Git auto-commit successful.")
            except subprocess.CalledProcessError as e:
                print(f"Error during Git auto-commit: {e}")

    if __name__ == "__main__":
        path_to_watch = "./your_git_repo_folder"  # Replace with your Git repository path
        event_handler = GitAutoCommitHandler(repo_path=path_to_watch)
        observer = Observer()
        observer.schedule(event_handler, path_to_watch, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()