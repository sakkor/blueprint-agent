"""tkinter desktop UI for Space Fractions (EMAIL-DESKTOP).

A native Tk window with mainloop providing intro/menu/help, play/pause/resume/
score/end screens and admin question editing. UI code is kept separate from the
testable service/model layer; a controller abstracts state so tests can run
headless (no Tk required).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from .model import GameState, Question, Admin
from .services import GameService, QuestionService, AdminService, UserService
from .errors import AuthenticationError, AuthorizationError
from .sample_questions import SAMPLE_QUESTIONS


HELP_TEXT = ("1. Read each fraction question.\n"
                 "2. Choose the correct answer.\n"
                 "3. Press Submit. Correct answers earn 1 point.\n"
                 "4. Pause anytime and Resume to continue.\n"
                 "5. Finish all questions to see your final score.")


class GameController:
    """Headless, testable controller that drives the UI state machine."""

    def __init__(self, game_service: GameService,
                 admin_service: AdminService,
                 user_service: UserService):
        self.game_service = game_service
        self.admin_service = admin_service
        self.user_service = user_service
        self.current_game = None
        self.current_admin: Optional[Admin] = None
        self.current_question_index = 0

    def start_game(self, game_id: str = "game-1") -> GameState:
        self.current_game = self.game_service.new_game(game_id)
        self.current_question_index = 0
        return self.current_game.state

    def current_question(self) -> Optional[Question]:
        if self.current_game is None or not self.current_game.questions:
            return None
        idx = min(self.current_question_index,
                  len(self.current_game.questions) - 1)
        return self.current_game.questions[idx]

    def submit_answer(self, answer: str) -> bool:
        q = self.current_question()
        if q is None or self.current_game is None or self.current_game.state != GameState.PLAYING:
            return False
        ok = self.current_game.submit_answer(q, answer)
        if self.current_question_index + 1 < len(self.current_game.questions):
            self.current_question_index += 1
        else:
            self.current_game.game_over()
        return ok

    def pause(self) -> GameState:
        assert self.current_game is not None
        self.game_service.pause(self.current_game.id)
        return self.current_game.state

    def resume(self) -> GameState:
        assert self.current_game is not None
        self.game_service.resume(self.current_game.id)
        return self.current_game.state

    def score(self) -> int:
        return self.current_game.view_score() if self.current_game else 0

    def admin_login(self, username: str, password: str) -> Admin:
        admin = self.admin_service.login(username, password)
        self.current_admin = admin
        return admin

    def admin_add_question(self, question: Question) -> None:
        if self.current_admin is None:
            raise AuthorizationError("Not logged in as admin")
        self.admin_service.add_question(self.current_admin, question)


def seed_services(question_service: QuestionService) -> QuestionService:
    if not question_service.get_questions():
        for data in SAMPLE_QUESTIONS:
            question_service.add_question(Question.from_dict(data))
    return question_service


class SpaceFractionsApp:
    """The Tk desktop application window."""

    def __init__(self, root: tk.Tk, controller: GameController):
        self.root = root
        self.controller = controller
        self.root.title("Space Fractions")
        self.root.geometry("640x480")
        self._build_menu()
        self.show_intro()

    def _clear(self) -> None:
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Menu):
                w.destroy()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Intro", command=self.show_intro)
        file_menu.add_command(label="New Game", command=self.show_play)
        file_menu.add_command(label="Help", command=self.show_help)
        file_menu.add_command(label="Admin", command=self.show_admin)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="Menu", menu=file_menu)
        self.root.config(menu=menubar)

    def show_intro(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Welcome to Space Fractions!",
                  font=("Arial", 20)).pack(pady=10)
        ttk.Label(
            frame,
            text="Blast through asteroid fractions and sharpen your skills.\n"
                 "Answer each question to score points.",
            justify="center").pack(pady=10)
        ttk.Button(frame, text="Main Menu", command=self.show_menu).pack(pady=10)
        ttk.Button(frame, text="Play", command=self.show_play).pack(pady=5)

    def show_menu(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Main Menu", font=("Arial", 18)).pack(pady=10)
        ttk.Button(frame, text="Play Game", command=self.show_play).pack(pady=5)
        ttk.Button(frame, text="Help", command=self.show_help).pack(pady=5)
        ttk.Button(frame, text="View Score",
                   command=self.show_score).pack(pady=5)
        ttk.Button(frame, text="Admin", command=self.show_admin).pack(pady=5)

    def show_help(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="How to Play", font=("Arial", 18)).pack(pady=10)
        ttk.Label(
            frame,
            text=HELP_TEXT,
            justify="left").pack(pady=10)
        ttk.Button(frame, text="Back", command=self.show_menu).pack(pady=10)

    def show_score(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Current Score", font=("Arial", 18)).pack(pady=10)
        ttk.Label(frame, text=str(self.controller.score()),
                  font=("Arial", 24)).pack(pady=10)
        ttk.Button(frame, text="Back", command=self.show_menu).pack(pady=10)

    def show_play(self) -> None:
        self._clear()
        self.controller.start_game()
        self._render_question()

    def _render_question(self) -> None:
        self._clear()
        game = self.controller.current_game
        q = self.controller.current_question()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        if game is None or q is None or game.state == GameState.GAME_OVER:
            self.show_end()
            return

        ttk.Label(frame, text=f"Score: {game.view_score()}",
                  font=("Arial", 14)).pack(anchor="e")
        ttk.Label(frame, text=q.prompt, font=("Arial", 16)).pack(pady=20)

        self.answer_var = tk.StringVar()
        for opt in q.get_options():
            ttk.Radiobutton(frame, text=opt, variable=self.answer_var,
                            value=opt).pack(anchor="w")

        btn_row = ttk.Frame(frame)
        btn_row.pack(pady=20)
        ttk.Button(btn_row, text="Submit",
                   command=self._on_submit).pack(side="left", padx=5)
        ttk.Button(btn_row, text="Pause",
                   command=self._on_pause).pack(side="left", padx=5)

    def _on_submit(self) -> None:
        answer = getattr(self, "answer_var", None)
        if answer is None or not answer.get():
            messagebox.showinfo("Space Fractions", "Choose an answer first.")
            return
        self.controller.submit_answer(answer.get())
        if self.controller.current_game.state == GameState.GAME_OVER:
            self.show_end()
        else:
            self._render_question()

    def _on_pause(self) -> None:
        self.controller.pause()
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Paused", font=("Arial", 18)).pack(pady=20)
        ttk.Button(frame, text="Resume",
                   command=self._on_resume).pack(pady=10)
        ttk.Button(frame, text="Quit to Menu",
                   command=self.show_menu).pack(pady=10)

    def _on_resume(self) -> None:
        self.controller.resume()
        self._render_question()

    def show_end(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Game Over", font=("Arial", 20)).pack(pady=10)
        score = self.controller.score()
        total = (len(self.controller.current_game.questions)
                 if self.controller.current_game else 0)
        ttk.Label(frame, text=f"Final Score: {score} / {total}",
                  font=("Arial", 18)).pack(pady=10)
        ttk.Label(frame, text="Great job, space explorer!").pack(pady=5)
        ttk.Button(frame, text="Play Again",
                   command=self.show_play).pack(pady=5)
        ttk.Button(frame, text="Main Menu",
                   command=self.show_menu).pack(pady=5)

    def show_admin(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Admin Login", font=("Arial", 16)).pack(pady=10)

        ttk.Label(frame, text="Username").pack()
        user_entry = ttk.Entry(frame)
        user_entry.pack()
        ttk.Label(frame, text="Password").pack()
        pass_entry = ttk.Entry(frame, show="*")
        pass_entry.pack()

        def _login():
            try:
                self.controller.admin_login(user_entry.get(), pass_entry.get())
                self._render_admin()
            except AuthenticationError as exc:
                messagebox.showerror("Login failed", str(exc))

        ttk.Button(frame, text="Login", command=_login).pack(pady=10)
        ttk.Button(frame, text="Back", command=self.show_menu).pack(pady=5)

    def _render_admin(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Admin: Update Questions",
                  font=("Arial", 16)).pack(pady=10)

        ttk.Label(frame, text="Prompt").pack()
        prompt = ttk.Entry(frame, width=50)
        prompt.pack()
        ttk.Label(frame, text="Options (comma separated)").pack()
        options = ttk.Entry(frame, width=50)
        options.pack()
        ttk.Label(frame, text="Correct Answer").pack()
        answer = ttk.Entry(frame, width=50)
        answer.pack()

        def _add():
            try:
                opts = [o.strip() for o in options.get().split(",") if o.strip()]
                q = Question(id=f"q-{len(self.controller.game_service.question_service.get_questions()) + 1}",
                             prompt=prompt.get(), options=opts,
                             correct_answer=answer.get())
                self.controller.admin_add_question(q)
                messagebox.showinfo("Space Fractions", "Question added.")
            except AuthorizationError as exc:
                messagebox.showerror("Not authorized", str(exc))

        ttk.Button(frame, text="Add Question", command=_add).pack(pady=10)
        ttk.Button(frame, text="Back", command=self.show_menu).pack(pady=5)


def build_controller() -> GameController:
    """Assemble the service graph and return a ready controller."""
    question_service = QuestionService()
    seed_services(question_service)
    game_service = GameService(question_service)
    admin_service = AdminService(question_service)
    user_service = UserService()
    return GameController(game_service, admin_service, user_service)


def main() -> None:
    root = tk.Tk()
    controller = build_controller()
    SpaceFractionsApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    main()
