"""Service layer for Space Fractions (SF-SERVICES).

Each service mirrors a microservice component boundary from the architecture:
    GameService     -> game logic / session state
    QuestionService -> question management / persistence
    UserService     -> player identity and authentication
    AdminService    -> authorized question editing
"""

from typing import List, Optional

from .model import Game, GameState, Question, User, Admin
from .errors import AuthorizationError, AuthenticationError
from .storage import (
    GameRepository,
    QuestionRepository,
    InMemoryQuestionRepository,
)


class QuestionService:
    """Owns questions and delegates persistence to a QuestionRepository."""

    def __init__(self, repo: Optional[QuestionRepository] = None):
        self.repo = repo if repo is not None else InMemoryQuestionRepository()

    def get_questions(self) -> List[Question]:
        return self.repo.load_questions()

    def add_question(self, question: Question) -> None:
        self.repo.save_question(question)

    def remove_question(self, question_id: str) -> None:
        self.repo.delete_question(question_id)

    def get_question(self, question_id: str) -> Optional[Question]:
        for q in self.repo.load_questions():
            if q.id == question_id:
                return q
        return None


class UserService:
    """Owns player authentication and identity."""

    def __init__(self):
        # Demo credential store; production uses OAuth2/hashed passwords.
        self._users: dict[str, str] = {"player": "play"}

    def authenticate(self, username: str, password: str) -> User:
        if username in self._users and self._users[username] == password:
            return User(id=username, username=username)
        raise AuthenticationError("Invalid username or password")

    def register(self, username: str, password: str) -> User:
        self._users[username] = password
        return User(id=username, username=username)


class AdminService:
    """Owns admin authorization and question editing (SF-ADMIN)."""

    def __init__(self, question_service: QuestionService):
        self.question_service = question_service
        self._admins: dict[str, str] = {"admin": "admin"}

    def login(self, username: str, password: str) -> Admin:
        if username in self._admins and self._admins[username] == password:
            return Admin(id=username, username=username, role="admin")
        raise AuthenticationError("Invalid admin credentials")

    def update_questions(self, admin: Admin, questions: List[Question]) -> None:
        if not admin.is_authorized():
            raise AuthorizationError("Admin not authorized to update questions")
        for q in questions:
            self.question_service.add_question(q)

    def add_question(self, admin: Admin, question: Question) -> None:
        if not admin.is_authorized():
            raise AuthorizationError("Admin not authorized to add questions")
        self.question_service.add_question(question)

    def remove_question(self, admin: Admin, question_id: str) -> None:
        if not admin.is_authorized():
            raise AuthorizationError("Admin not authorized to remove questions")
        self.question_service.remove_question(question_id)


class GameService:
    """Owns game orchestration and state transitions (SF-PLAY, SF-STATE)."""

    def __init__(self, question_service: QuestionService,
                 game_repo: Optional[GameRepository] = None):
        self.question_service = question_service
        self.game_repo = game_repo
        self._games: dict[str, Game] = {}

    def new_game(self, game_id: str = "game-1") -> Game:
        questions = self.question_service.get_questions()
        game = Game(id=game_id, questions=questions,
                    state=GameState.PLAYING)
        self._games[game_id] = game
        return game

    def get_game(self, game_id: str) -> Optional[Game]:
        return self._games.get(game_id)

    def play(self, game_id: str) -> Game:
        game = self._games.get(game_id) or self.new_game(game_id)
        game.play()
        return game

    def pause(self, game_id: str) -> Game:
        game = self._require(game_id)
        game.pause()
        return game

    def resume(self, game_id: str) -> Game:
        game = self._require(game_id)
        game.resume()
        return game

    def game_over(self, game_id: str) -> Game:
        game = self._require(game_id)
        game.game_over()
        if self.game_repo is not None:
            self.game_repo.save_game(game)
        return game

    def submit_answer(self, game_id: str, question_id: str, answer: str) -> bool:
        game = self._require(game_id)
        question = self.question_service.get_question(question_id)
        if question is None:
            return False
        return game.submit_answer(question, answer)

    def _require(self, game_id: str) -> Game:
        game = self._games.get(game_id)
        if game is None:
            game = self.new_game(game_id)
        return game
