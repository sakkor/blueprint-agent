"""Tests for the desktop UI helper logic (SF-HELP, EMAIL-DESKTOP).

These exercise pure helpers without instantiating Tk (which requires a display).
The Help screen content is a controller-level helper so it is testable headless.
"""

from spacefractions.ui import GameController, HELP_TEXT


def test_help_text_present():
    # Help instructions are exposed as a stable, testable constant (SF-HELP).
    assert "Read each fraction question" in HELP_TEXT
    assert "Pause anytime" in HELP_TEXT
    assert "final score" in HELP_TEXT


def test_controller_exposes_help():
    # The controller/UI provides a help view via the app; here we assert the
    # help text does not crash and is non-empty (SF-HELP).
    from spacefractions.model import Question
    from spacefractions.services import (
        QuestionService, AdminService, GameService, UserService)
    qs = QuestionService()
    qs.add_question(Question(id="q1", prompt="p",
                             options=["1/2"], correct_answer="1/2"))
    c = GameController(GameService(qs), AdminService(qs), UserService())
    assert HELP_TEXT.strip() != ""
    assert isinstance(c, GameController)
