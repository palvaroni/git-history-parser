from enum import Enum
from typing import List, Optional

class CommitType(Enum):
    ADDITION = "ADDITION"
    DELETION = "DELETION"
    MODIFICATION = "MODIFICATION"

class Modification:
    def __init__(self, type: CommitType, file_paths: List[str]):
        self.type = type
        self.file_paths = file_paths
        self.loc_count: int = 0
        self.nloc_count: int = 0

    def __repr__(self):
        return f"Modification(type={self.type}, file_paths={self.file_paths}, loc_count={self.loc_count}, nloc_count={self.nloc_count})"
