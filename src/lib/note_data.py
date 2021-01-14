from datetime import datetime
import strawberry

from typing import List, Optional

@strawberry.type
class NoteData:
    tags: List[str]
    note: str
    note_taker: str
    timestamp: str

    def __init__(self, note: str, note_taker: str, timestamp: str, tags: Optional[List[str]]):
        self.note = note
        self.note_taker = note_taker
        self.timestamp = timestamp
        self.tags = tags if tags is not None else list()

    @staticmethod
    def FromNote(note):
        return NoteData(note.note, note.note_taker, str(note.timestamp.isoformat()))