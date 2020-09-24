###
#
# This class aims to provide an easy interface with logging and notes.
#
###
import datetime


class Note:
    def __init__(self, note="", timestamp=datetime.datetime.now(datetime.timezone.utc), note_taker="", tags=None):
        if tags == None:
            tags = []

        self.note = note
        self.timestamp = timestamp
        self.note_taker = note_taker
        self.tags = tags

class Notes:
    def __init__(self):
        self.entries = []
    
    def add_note(self, note: Note):
        self.entries.append(note)

    def del_note(self, note: Note):
        for i in range(len(self.entries)):
            n = self.entries[i]
            if note == n:
                del self.entries[i]
                break
    
    def add(self, note="", timestamp=datetime.datetime.now(datetime.timezone.utc), note_taker="", tags=None):
        n = Note(note, timestamp, note_taker, tags)
        self.entries.append(n)
