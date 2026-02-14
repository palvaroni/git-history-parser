#!/usr/bin/env python3
"""
Git Commit History Parser

This script parses git commit history and creates a CSV file with commit statistics.
"""

import subprocess
import csv
import re
import argparse
from typing import List, Dict, Tuple
import os
import json
from datetime import datetime
try:
    import pyodbc
except ImportError:
    pyodbc = None
from modification import Modification, CommitType


class GitCommitParser:
    def __init__(self, repo_path: str = "."):
        """
        Initialize the GitCommitParser.
        
        Args:
            repo_path (str): Path to the git repository
        """
        self.repo_path = repo_path
    
    def _run_git_command(self, command: List[str]) -> str:
        """
        Run a git command and return the output.
        
        Args:
            command (List[str]): Git command as a list of strings
            
        Returns:
            str: Command output
            
        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                encoding='cp850',
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {e}")
            print(f"Error output: {e.stderr}")
            raise
    
    def get_commit_list(self, skip: int = None, max_count: int = None) -> List[str]:
        """
        Get a list of commit hashes.
        
        Args:
            max_count (int, optional): Maximum number of commits to retrieve
            
        Returns:
            List[str]: List of commit hashes
        """
        command = [
            "log",
            "--no-merges",
            "--pretty=format:%H"]
        
        if skip:
            command.extend(["--skip", str(skip)])

        if max_count:
            command.extend(["-n", str(max_count)])
        
        output = self._run_git_command(command)
        return output.split('\n') if output else []
    
    def get_commit_info(self, commit_hash: str) -> Dict[str, str]:
        """
        Get basic commit information.
        
        Args:
            commit_hash (str): The commit hash
            
        Returns:
            Dict[str, str]: Dictionary containing commit info including message
        """
        # Get commit info: hash, author, date, and message
        # To use name for author, use %an; for email, use %ae
        command = ["show", "--pretty=format:%H|%ae|%ad|%s", "--date=iso", "--name-only", commit_hash]
        output = self._run_git_command(command)
        
        lines = output.split('\n')
        if not lines:
            return {}
        
        # Parse the first line which contains hash|author|date|message.
        info_line = lines[0]
        parts = info_line.split('|', 3)  # Split into max 4 parts to preserve | in message
        
        if len(parts) >= 4:
            return {
                'hash': parts[0],
                'author': parts[1],
                'date': parts[2],
                'message': parts[3]
            }
        return {}
    
    def get_commit_diff_stats(self, commit_hash: str) -> Tuple[List[Modification], List[str]]:
        """
        Get diff statistics for a commit and return Modification objects.
        
        Args:
            commit_hash (str): The commit hash
            
        Returns:
            List[Modification]: List of Modification objects for each change
            List[str]: List of affected previous commit hashes
        """
        try:
            # Get the diff with context to identify modifications.
            command = [
                "show",
                "--unified=0",  # No context lines to get exact line numbers
                "--diff-algorithm=histogram",
                commit_hash
            ]
            diff_output = self._run_git_command(command)
            
            modifications = []
            affected_commits = []
            lines = diff_output.split('\n')
            current_prev_commits = None
            current_source_file = None
            current_target_file = None
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Parse file headers
                if line.startswith('diff --git'):
                    # Extract file path from "diff --git a/path b/path"
                    file_match = re.match(r"diff --git a\/(.*) b\/(.*)", line)

                    if file_match and len(file_match.groups()) >= 2:
                        current_source_file = file_match.group(1)
                        current_target_file = file_match.group(2)

                        # Use git blame to get the previous commit hash for each line.
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            # File mode 160000 indicates a submodule
                            if next_line.startswith('index ') and not next_line.endswith(' 160000'):
                                # File exists in previous commit
                                current_prev_commits = self._get_prev_commits_by_line(current_source_file, commit_hash)

                    i += 1
                    continue
                
                # Parse hunk headers like @@ -start,count +start,count @@
                if line.startswith('@@'):
                    hunk_match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                    if hunk_match and current_target_file:
                        old_start = int(hunk_match.group(1))
                        old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                        new_start = int(hunk_match.group(3))
                        new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                        
                        # Process the hunk content
                        hunk_modifications = self._parse_hunk(
                            lines, i + 1,
                            current_source_file, current_target_file,
                            old_start, old_count, 
                            new_start, new_count
                        )
                        modifications.extend(hunk_modifications)

                        # Identify affected previous commits
                        for line in range(old_start, old_start + old_count):
                            if current_prev_commits and line in current_prev_commits:
                                prev_commit = current_prev_commits[line]
                                if prev_commit not in affected_commits:
                                    affected_commits.append(prev_commit)
                        
                        # Skip to next hunk
                        i += 1
                        while i < len(lines) and not lines[i].startswith('@@') and not lines[i].startswith('diff --git'):
                            i += 1
                        continue
                
                i += 1
            
            return (modifications, affected_commits)
            
        except subprocess.CalledProcessError:
            # Return empty list if we can't get diff stats
            return []
        
    def _get_prev_commits_by_line(self, file_path: str, commit_hash: str) -> Dict[int, str]:
        """
        Get previous commit hashes for each line in a file using git blame.
        
        Args:
            file_path (str): Path of the file
            commit_hash (str): The commit hash
            
        Returns:
            Dict[int, str]: Mapping of line numbers to previous commit hashes
        """
        blame_output = self._run_git_command([
            "blame",
            "-l",
            "--porcelain",
            f"{commit_hash}~",
            "--",
            file_path
        ])
        
        prev_commits = {}
        current_line = 0
        
        for line in blame_output.split('\n'):
            if re.match(r'^[0-9a-f]{40} ', line):
                parts = line.split()
                if len(parts) >= 2:
                    commit_id = parts[0]
                    current_line += 1
                    prev_commits[current_line] = commit_id
        
        return prev_commits
    
    def _parse_hunk(self, lines: List[str], start_idx: int,
                    old_file_path: str, new_file_path: str, 
                    old_start: int, old_count: int,
                    new_start: int, new_count: int
                ) -> List[Modification]:
        """
        Parse a diff hunk and return Modification objects.
        
        Args:
            lines: All diff lines
            start_idx: Starting index in lines for this hunk
            file_path: Path of the file being modified
            old_start: Starting line number in old file
            old_count: Number of lines in old file
            new_start: Starting line number in new file  
            new_count: Number of lines in new file
            commit_hash: The commit hash
            author: The author
            date: The commit date
            
        Returns:
            List[Modification]: List of modifications in this hunk
        """
        modifications = []
        i = start_idx
        old_line = old_start
        new_line = new_start
        
        row_deletions = []
        row_additions = []
        
        # Process all lines in the hunk
        while i < len(lines):
            line = lines[i]
            
            # Stop at next hunk or file
            if line.startswith('@@') or line.startswith('diff --git'):
                break
                
            if line.startswith('-') and not line.startswith('---'):
                # A deleted row
                row_deletions.append({
                    'line_num': old_line,
                    'content': line[1:],  # Remove the - prefix
                    'index': i
                })
                old_line += 1
                
            elif line.startswith('+') and not line.startswith('+++'):
                # An added row
                row_additions.append({
                    'line_num': new_line,
                    'content': line[1:],  # Remove the + prefix
                    'index': i
                })
                new_line += 1
                
            else:
                # Context line (unchanged) - advance both counters
                old_line += 1
                new_line += 1
            
            i += 1

        file_paths = [old_file_path, new_file_path] if old_file_path != new_file_path else [new_file_path]
        
        # If hunk contains both additions and deletions, treat as a modification.
        if row_deletions and row_additions:
            start_line = min(row_additions[0]['line_num'], row_deletions[0]['line_num'])
            end_line = max(row_additions[-1]['line_num'], row_deletions[-1]['line_num'])
            
            modifications.append(Modification(
                type=CommitType.MODIFICATION,
                file_paths=file_paths,
                start_line=start_line,
                end_line=end_line,
            ))

        # Pure deletion
        elif row_deletions:
            start_line = row_deletions[0]['line_num']
            end_line = row_deletions[-1]['line_num']
            
            modifications.append(Modification(
                type=CommitType.DELETION,
                file_paths=file_paths,
                start_line=start_line,
                end_line=end_line
            ))
            
        elif row_additions:
            # Pure addition
            start_line = row_additions[0]['line_num']
            end_line = row_additions[-1]['line_num']
            
            modifications.append(Modification(
                type=CommitType.ADDITION,
                file_paths=file_paths,
                start_line=start_line,
                end_line=end_line
            ))
        
        return modifications

    def parse_commits(self, skip: int = None, max_count: int = None) -> Tuple[List[Dict], Dict[str, str]]:
        """
        Parse commits and return detailed modification data along with summary statistics.
        
        Args:
            max_count (int, optional): Maximum number of commits to parse
            
        Returns:
            List[Dict]: List of commit data dictionaries with detailed modifications
        """
        print("Getting commit list...")
        commit_hashes = self.get_commit_list(skip, max_count)
        
        if not commit_hashes:
            print("No commits found in the repository.")
            return []
        
        print(f"Found {len(commit_hashes)} commits. Processing...")
        
        commit_data = []
        for i, commit_hash in enumerate(commit_hashes, 1):
            print(f"Processing commit {i}/{len(commit_hashes)}: {commit_hash[:8]}...")
            
            # Get basic commit info
            commit_info = self.get_commit_info(commit_hash)
            if not commit_info:
                continue
            
            # Get detailed diff statistics
            (modifications, affected_commits) = self.get_commit_diff_stats(commit_hash)
            
            commit_data.append({
                'commit_hash': commit_info['hash'],
                'author': commit_info['author'],
                'date': commit_info['date'],
                'message': commit_info.get('message', ''),
                'modifications': modifications
            })
        
        return (commit_data)

    def write_to_csv(self, commit_data: List[Dict], output_file: str, use_append: bool = False):
        """
        Write aggregated commit data to a CSV file.
        
        Args:
            commit_data (List[Dict]): List of commit data dictionaries with modifications
            output_file (str): Output CSV file path
        """
        print(f"Writing aggregated commit data to {output_file}...")
        
        with open(output_file, 'a' if use_append else 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'commit_hash', 'date', 'message', 'affected_files',
                'additions', 'deletions', 'modifications'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not use_append or os.stat(output_file).st_size == 0:
                writer.writeheader()

            for commit in commit_data:
                # Aggregate modifications per commit
                additions_count = 0
                deletions_count = 0
                modifications_count = 0
                affected_files = set()
                
                if 'modifications' in commit:
                    for mod in commit['modifications']:
                        # Collect affected files
                        affected_files.update(mod.file_paths)
                        
                        # Count line changes by type
                        if mod.type == CommitType.ADDITION:
                            additions_count += mod.line_count
                        elif mod.type == CommitType.DELETION:
                            deletions_count += mod.line_count
                        elif mod.type == CommitType.MODIFICATION:
                            modifications_count += mod.line_count
                
                writer.writerow({
                    'commit_hash': commit['commit_hash'],
                    'date': commit['date'],
                    'message': commit.get('message', ''),
                    'affected_files': ';'.join(sorted(affected_files)),
                    'additions': additions_count,
                    'deletions': deletions_count,
                    'modifications': modifications_count
                })
        
        print(f"Successfully wrote aggregated commit data to {output_file}")
        
    def write_to_database(self, commit_data: List[Dict], config_file: str = 'config.json'):
        """
        Write aggregated commit data to a MSSQL database.
        
        Args:
            commit_data (List[Dict]): List of commit data dictionaries with modifications
            config_file (str): Path to the configuration file with database credentials
        """
        if pyodbc is None:
            print("Error: pyodbc is not installed. Install it with: pip install pyodbc")
            return
        
        # Load configuration
        if not os.path.exists(config_file):
            print(f"Error: Configuration file '{config_file}' not found.")
            print("Please create a config.json file with database credentials.")
            return
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        db_config = config.get('database', {})
        
        # Extract repository name from repo_path (leaf directory name)
        repository_name = os.path.basename(os.path.abspath(self.repo_path))
        
        # Build connection string
        conn_str = (
            f"DRIVER={{{db_config.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
            f"SERVER={db_config.get('server', 'localhost')};"
            f"DATABASE={db_config.get('database', 'GitAnalysis')};"
            f"UID={db_config.get('username')};"
            f"PWD={db_config.get('password')}"
        )
        
        print(f"Connecting to database...")
        
        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            print(f"Writing aggregated commit data to database...")
            
            insert_query = """
                INSERT INTO [dbo].[commits] 
                    (repository, commit_hash, date, message, affected_files, additions, deletions, modifications)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            inserted_count = 0
            skipped_count = 0
            
            for commit in commit_data:
                # Aggregate modifications per commit
                additions_count = 0
                deletions_count = 0
                modifications_count = 0
                affected_files = set()
                
                if 'modifications' in commit:
                    for mod in commit['modifications']:
                        # Collect affected files
                        affected_files.update(mod.file_paths)
                        
                        # Count line changes by type
                        if mod.type == CommitType.ADDITION:
                            additions_count += mod.line_count
                        elif mod.type == CommitType.DELETION:
                            deletions_count += mod.line_count
                        elif mod.type == CommitType.MODIFICATION:
                            modifications_count += mod.line_count
                
                try:
                    # Parse date string to datetime (format: "2024-01-15 10:30:45 +0200")
                    # Take first 19 characters to get "YYYY-MM-DD HH:MM:SS"
                    date_str = commit['date'][:19]
                    commit_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute(insert_query, (
                        repository_name,
                        commit['commit_hash'],
                        commit_date,
                        commit.get('message', ''),
                        ';'.join(sorted(affected_files)),
                        additions_count,
                        deletions_count,
                        modifications_count
                    ))
                    inserted_count += 1
                except pyodbc.IntegrityError:
                    # Skip duplicate commits (based on unique constraint)
                    skipped_count += 1
                except Exception as e:
                    print(f"Warning: Failed to insert commit {commit['commit_hash'][:8]}: {e}")
                    skipped_count += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Successfully wrote {inserted_count} commits to database.")
            if skipped_count > 0:
                print(f"Skipped {skipped_count} commits (duplicates or errors).")
            
        except Exception as e:
            print(f"Database error: {e}")
            raise


def main():
    """Main function to run the git commit parser."""
    parser = argparse.ArgumentParser(
        description="Parse git commit history and create a CSV file with commit statistics"
    )
    parser.add_argument(
        "--repo-path", "-r",
        default=".",
        help="Path to the git repository (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        default="git_commits.csv",
        help="Output CSV file name (default: git_commits.csv)"
    )
    parser.add_argument(
        "--append", "-a",
        action='store_true',
        default=False,
        help="Use append mode when writing to the output file."
    )
    parser.add_argument(
        "--skip", "-s",
        type=int,
        help="Skip n commits to process (default: 0)"
    )
    parser.add_argument(
        "--max-commits", "-n",
        type=int,
        help="Maximum number of commits to process (default: all commits)"
    )
    parser.add_argument(
        "--database", "-d",
        action='store_true',
        default=True,
        help="Write to database instead of CSV"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.json",
        help="Path to configuration file for database credentials (default: config.json)"
    )
    
    args = parser.parse_args()
    
    # Check if the specified path is a git repository
    if not os.path.exists(os.path.join(args.repo_path, '.git')):
        print(f"Error: {args.repo_path} is not a git repository")
        return 1
    
    try:
        # Initialize parser
        git_parser = GitCommitParser(args.repo_path)
        
        # Parse commits
        commit_data = git_parser.parse_commits(args.skip, args.max_commits)
        
        if not commit_data:
            print("No commit data to write.")
            return 1
        
        # Write to database or CSV
        if args.database:
            git_parser.write_to_database(commit_data, args.config)
        else:
            git_parser.write_to_csv(commit_data, args.output, use_append=args.append)
        
        # Print summary
        print(f"\nSummary:")
        print(f"Total commits processed: {len(commit_data)}")

        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
