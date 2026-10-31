"""Tests for persistence adapters (SF-PERSIST). SQLite offline adapter only."""

import os
import tempfile

from spacefractions.model import Question
from spacefractions.storage import SQLiteQuestionRepository


def test_sqlite_roundtrip():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        repo = SQLiteQuestionRepository(path)
        q = Question(id="q1", prompt="p", options=["1/2", "1/4"],
                     correct_answer="1/2")
        repo.save_question(q)
        loaded = repo.load_questions()
        assert len(loaded) == 1
        assert loaded[0].id == "q1"
        assert loaded[0].check_answer("2/4") is True
        repo.delete_question("q1")
        assert repo.load_questions() == []
        repo.close()
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_sqlite_idempotent_save():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        repo = SQLiteQuestionRepository(path)
        q = Question(id="q2", prompt="p", options=["1/3"], correct_answer="1/3")
        repo.save_question(q)
        repo.save_question(q)
        assert len(repo.load_questions()) == 1
        repo.close()
    finally:
        if os.path.exists(path):
            os.remove(path)
