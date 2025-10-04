# Git Commit History Parser - PowerShell Script
# This script runs the git parser with the virtual environment

Write-Host "Git Commit History Parser" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment is set up properly." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if git_parser.py exists
if (-not (Test-Path "git_parser.py")) {
    Write-Host "Error: git_parser.py not found!" -ForegroundColor Red
    Write-Host "Please ensure you're running this from the correct directory." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Show usage help if no arguments provided
if ($args.Count -eq 0) {
    Write-Host "`nUsage examples:" -ForegroundColor Cyan
    Write-Host "  .\run_parser.ps1                                   # Parse current directory"
    Write-Host "  .\run_parser.ps1 --repo-path C:\path\to\repo       # Parse specific repo"
    Write-Host "  .\run_parser.ps1 --max-commits 100                 # Limit to 100 commits"
    Write-Host "  .\run_parser.ps1 --skip 10                         # Skip first 10 commits"
    Write-Host "  .\run_parser.ps1 --output results.csv              # Custom output file"
    Write-Host "  .\run_parser.ps1 --append                          # Append output to the end of the file"
    Write-Host "  .\run_parser.ps1 --help                            # Show all options"
    Write-Host ""
}

# Run the parser with the virtual environment
Write-Host "Running git parser..." -ForegroundColor Yellow
try {
    & ".venv\Scripts\python.exe" "git_parser.py" $args
    Write-Host "`nDone! Check the output CSV file." -ForegroundColor Green
} catch {
    Write-Host "Error running parser: $_" -ForegroundColor Red
    exit 1
}

if ($args.Count -eq 0) {
    Read-Host "Press Enter to exit"
}
