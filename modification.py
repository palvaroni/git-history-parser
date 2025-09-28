from enum import Enum
from typing import List, Optional

class CommitType(Enum):
    ADDITION = "ADDITION"
    DELETION = "DELETION"
    MODIFICATION = "MODIFICATION"

class Modification:
    def __init__(self, type: CommitType, file_paths: List[str], start_line: int, end_line: int):
        self.type = type
        self.file_paths = file_paths
        self.start_line = start_line
        self.end_line = end_line
    
    @property
    def lines_modified(self) -> List[int]:
        """Return list of line numbers that were modified."""
        return list(range(self.start_line, self.end_line + 1))
    
    @property
    def line_count(self) -> int:
        """Return the number of lines modified."""
        return self.end_line - self.start_line + 1
    
    def __repr__(self):
        return f"Modification(type={self.type}, file_paths={self.file_paths}, start_line={self.start_line}, end_line={self.end_line})"
