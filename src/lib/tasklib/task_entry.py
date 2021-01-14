import strawberry

from typing import List

from lib.note_data import NoteData

@strawberry.type
class TaskEntry:
    name: str
    progress_supported: bool
    last_progress: float
    return_code: int
    notes: List[NoteData]
    time_started: str
    time_ended: str

    @staticmethod
    def FromTask(task):
        notes = []
        for n in task.notes.entries:
            notes.append(NoteData.FromNote(n))
        return TaskEntry(task.name, (task.Progress != -1), task.Progress, task.ProgressString, task.returncode, notes, (task.time_started.isoformat() if task.time_started != None else None), (task.time_ended.isoformat() if task.time_ended != None else None))
