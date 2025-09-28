# Git Commit History Parser

A Python script that parses git commit history and creates a CSV file with line-level modification tracking.

## Features

- Extracts detailed commit information (hash, author, date)
- Tracks line-level modifications
- Categorizes changes as ADDITION, DELETION, or MODIFICATION
- Identifies affected previous commits for modification impact analysis
- Outputs modification data to CSV
- Supports limiting the number of commits to process
- Works with any git repository

The modification types are defined as:

1. **ADDITION**: New lines added to a file
2. **DELETION**: Lines removed from a file  
3. **MODIFICATION**: A hunk containing both additions and deletions, indicating changed content

## Setup

### Prerequisites
- Python 3.7 or higher
- Git installed and accessible from command line
- A git repository to analyze

### Installation
No external dependencies are required. The script uses only Python standard library modules.

### PowerShell Script
The PowerShell script (`run_parser.ps1`) handles virtual environment activation and runs the parser.

## Usage

### Basic Usage
```bash
python git_parser.py
```
This will analyze the current directory (if it's a git repository) and create `git_commits.csv`.

### Using PowerShell Script (Windows)
```powershell
.\run_parser.ps1
```
The PowerShell script provides an interactive menu and handles virtual environment setup automatically.

### Usage Examples
```bash
# Analyze a specific repository
python git_parser.py --repo-path /path/to/your/git/repo

# Specify output file
python git_parser.py --output my_analysis.csv

# Limit number of commits
python git_parser.py --max-commits 100

# Combine options
python git_parser.py --repo-path ../my-project --output project_analysis.csv --max-commits 50
```

### Command Line Options
- `--repo-path`, `-r`: Path to the git repository (default: current directory)
- `--output`, `-o`: Output CSV file name (default: git_commits.csv)
- `--max-commits`, `-n`: Maximum number of commits to process (default: all commits)

## Output Format

The generated CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| commit_hash | Full SHA hash of the commit |
| author | Email address of the commit author |
| date | Commit date in ISO format with timezone |
| modified_at | Timestamp when this modification was affected by later commits |
| modification_type | Type of change: ADDITION, DELETION, or MODIFICATION |
| file_path | Path(s) to affected file(s), semicolon-separated for file moves |
| start_line | Starting line number of the modification |
| end_line | Ending line number of the modification |
| line_count | Total number of lines affected by this modification |

## Output Example

```csv
commit_hash,author,date,modified_at,modification_type,file_path,start_line,end_line,line_count
616facde8e3e7015dde4668e024daf425f80f345,author-a@example.com,2025-10-04 09:12:30 +0300,,ADDITION,Deployment/app.bicep,85,85,1
4f3329d606e447ef0c556f3f0a0c87b469a9234d,author-b@example.com,2025-09-10 12:51:39 +0300,,MODIFICATION,frontend/src/app.js,24,24,1
```
