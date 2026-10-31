"""Persistence adapters for Space Fractions.

The primary, production path is PostgreSQL (SF-PERSIST). A clearly documented
SQLite offline adapter is provided for the local desktop demo only; it does NOT
satisfy the PostgreSQL deployment, HA, or production requirements.
"""

import abc
import json
from typing import List, Optional

from .model import Game, Question
from .errors import StorageError


class QuestionRepository(abc.ABC):
    @abc.abstractmethod
    def load_questions(self) -> List[Question]:
        raise NotImplementedError

    @abc.abstractmethod
    def save_question(self, question: Question) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete_question(self, question_id: str) -> None:
        raise NotImplementedError


class GameRepository(abc.ABC):
    @abc.abstractmethod
    def save_game(self, game: Game) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def load_game(self, game_id: str) -> Optional[Game]:
        raise NotImplementedError


class InMemoryQuestionRepository(QuestionRepository):
    """In-memory fallback used when no database is configured."""

    def __init__(self, questions: Optional[List[Question]] = None):
        self._questions = {q.id: q for q in (questions or [])}

    def load_questions(self) -> List[Question]:
        return list(self._questions.values())

    def save_question(self, question: Question) -> None:
        self._questions[question.id] = question

    def delete_question(self, question_id: str) -> None:
        self._questions.pop(question_id, None)


class SQLiteQuestionRepository(QuestionRepository):
    """SQLite adapter for offline/local desktop use only (see ASSUMPTIONS.md)."""

    def __init__(self, path: str = "spacefractions.db"):
        import sqlite3
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS questions ("
            "id TEXT PRIMARY KEY, prompt TEXT NOT NULL, "
            "options_json TEXT NOT NULL, correct_answer TEXT NOT NULL)"
        )
        self._conn.commit()

    def load_questions(self) -> List[Question]:
        import sqlite3
        rows = self._conn.execute("SELECT * FROM questions").fetchall()
        out = []
        for row in rows:
            out.append(Question(
                id=row[0], prompt=row[1],
                options=json.loads(row[2]), correct_answer=row[3]))
        return out

    def save_question(self, question: Question) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO questions "
            "(id, prompt, options_json, correct_answer) VALUES (?,?,?,?)",
            (question.id, question.prompt,
             json.dumps(question.options), question.correct_answer))
        self._conn.commit()

    def delete_question(self, question_id: str) -> None:
        self._conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class PostgresQuestionRepository(QuestionRepository):
    """PostgreSQL adapter (the production persistence path, SF-PERSIST).

    Connects lazily so the desktop demo can run without a live database.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = None

    def _connect(self):
        if self._conn is None:
            try:
                import psycopg2  # type: ignore
                self._conn = psycopg2.connect(self.dsn)
            except ImportError as exc:
                raise StorageError(
                    "psycopg2 not installed; run 'pip install -r requirements.txt'"
                ) from exc
        return self._conn

    def load_questions(self) -> List[Question]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, prompt, options, correct_answer FROM questions ORDER BY id"
        )
        rows = cur.fetchall()
        cur.close()
        return [
            Question(id=r[0], prompt=r[1], options=r[2], correct_answer=r[3])
            for r in rows
        ]

    def save_question(self, question: Question) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO questions (id, prompt, options, correct_answer) "
            "VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (id) DO UPDATE SET prompt=EXCLUDED.prompt, "
            "options=EXCLUDED.options, correct_answer=EXCLUDED.correct_answer",
            (question.id, question.prompt, question.options,
             question.correct_answer))
        conn.commit()
        cur.close()

    def delete_question(self, question_id: str) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM questions WHERE id=%s", (question_id,))
        conn.commit()
        cur.close()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class PostgresGameRepository(GameRepository):
    """PostgreSQL adapter for game state persistence (SF-PERSIST)."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = None

    def _connect(self):
        if self._conn is None:
            import psycopg2  # type: ignore
            self._conn = psycopg2.connect(self.dsn)
        return self._conn

    def save_game(self, game: Game) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO games (id, game_state) VALUES (%s,%s) "
            "ON CONFLICT (id) DO UPDATE SET game_state=EXCLUDED.game_state",
            (game.id, json.dumps(game.to_dict())))
        conn.commit()
        cur.close()

    def load_game(self, game_id: str) -> Optional[Game]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT game_state FROM games WHERE id=%s", (game_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        data = json.loads(row[0])
        game = Game(id=game_id)
        game.score = data["score"]
        game.answered = data["answered"]
        game.correct_count = data["correct_count"]
        return game
