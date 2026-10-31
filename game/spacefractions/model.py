"""Domain model for Space Fractions.

Mirrors the ClassDiagram (SF-MODEL): Game, Question, User, Admin entities
with consistent associations:
    Game --* Question
    User --* Game
    Admin --* Question
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from fractions import Fraction


class GameState(Enum):
    """States from StateDiagram (SF-STATE): Playing, Paused, GameOver."""

    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"


@dataclass
class Question:
    """A fraction question with a single correct answer (improper/reduced)."""

    id: str
    prompt: str
    options: List[str]
    correct_answer: str

    def get_prompt(self) -> str:
        return self.prompt

    def get_options(self) -> List[str]:
        return list(self.options)

    def check_answer(self, answer: str) -> bool:
        """Normalize fractions before comparing so '2/4' == '1/2'."""
        try:
            return Fraction(answer) == Fraction(self.correct_answer)
        except (ValueError, ZeroDivisionError):
            return answer.strip() == self.correct_answer.strip()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "options": list(self.options),
            "correct_answer": self.correct_answer,
        }

    @staticmethod
    def from_dict(data: dict) -> "Question":
        return Question(
            id=str(data["id"]),
            prompt=str(data["prompt"]),
            options=[str(o) for o in data["options"]],
            correct_answer=str(data["correct_answer"]),
        )


@dataclass
class User:
    """An end user who plays games."""

    id: str
    username: str

    def play_game(self, game: "Game") -> None:
        game.start()

    def view_score(self, game: "Game") -> int:
        return game.view_score()


@dataclass
class Admin:
    """An administrator who can update questions (requires authorization)."""

    id: str
    username: str
    role: str = "admin"

    def is_authorized(self) -> bool:
        return self.role == "admin"


@dataclass
class Game:
    """A single game session: score, state machine, and question references."""

    id: str
    questions: List[Question] = field(default_factory=list)
    score: int = 0
    answered: int = 0
    state: GameState = GameState.PLAYING
    correct_count: int = 0

    def play(self) -> None:
        self.state = GameState.PLAYING

    def start(self) -> None:
        self.play()

    def pause(self) -> None:
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED

    def resume(self) -> None:
        if self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def game_over(self) -> None:
        self.state = GameState.GAME_OVER

    def submit_answer(self, question: Question, answer: str) -> bool:
        if self.state != GameState.PLAYING:
            return False
        correct = question.check_answer(answer)
        self.answered += 1
        if correct:
            self.score += 1
            self.correct_count += 1
        return correct

    def view_score(self) -> int:
        return self.score

    def reset(self) -> None:
        self.score = 0
        self.answered = 0
        self.correct_count = 0
        self.state = GameState.PLAYING

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "score": self.score,
            "answered": self.answered,
            "correct_count": self.correct_count,
            "state": self.state.value,
        }


def fraction_question(template: Question, new_id: str, prompt: str,
                      options: List[str], answer: str) -> Question:
    """Helper to build a question while keeping constructor signatures stable."""
    return Question(id=new_id, prompt=prompt, options=options, correct_answer=answer)
