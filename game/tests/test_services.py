"""Tests for the service layer (SF-SERVICES, SF-PLAY, SF-ADMIN, SF-SECURITY)."""

import pytest

from spacefractions.model import Question, Admin
from spacefractions.services import (
    QuestionService, AdminService, GameService, UserService,
)
from spacefractions.errors import AuthorizationError, AuthenticationError
from spacefractions.sample_questions import SAMPLE_QUESTIONS


def make_services():
    qs = QuestionService()
    for d in SAMPLE_QUESTIONS:
        qs.add_question(Question.from_dict(d))
    gs = GameService(qs)
    admin = AdminService(qs)
    us = UserService()
    return qs, gs, admin, us


def test_play_game_and_submit_answer():
    qs, gs, admin, us = make_services()
    g = gs.new_game("g1")
    q = qs.get_questions()[0]
    assert gs.submit_answer("g1", q.id, q.correct_answer) is True
    assert g.score == 1


def test_pause_resume_via_service():
    qs, gs, admin, us = make_services()
    gs.new_game("g1")
    gs.pause("g1")
    assert gs.get_game("g1").state.value == "paused"
    gs.resume("g1")
    assert gs.get_game("g1").state.value == "playing"


def test_game_over_persists_state():
    class FakeRepo:
        def __init__(self):
            self.saved = None
        def save_game(self, game):
            self.saved = game.to_dict()
    qs, gs, admin, us = make_services()
    gs.game_repo = FakeRepo()
    gs.new_game("g1")
    gs.game_over("g1")
    assert gs.game_repo.saved["state"] == "game_over"


def test_user_authentication():
    _, _, _, us = make_services()
    u = us.authenticate("player", "play")
    assert u.username == "player"
    with pytest.raises(AuthenticationError):
        us.authenticate("player", "wrong")


def test_admin_login_and_update():
    qs, gs, admin, us = make_services()
    a = admin.login("admin", "admin")
    admin.update_questions(a, [Question(id="q9", prompt="new",
                                        options=["1/2"], correct_answer="1/2")])
    assert qs.get_question("q9") is not None


def test_admin_negative_authorization():
    qs, gs, admin, us = make_services()
    # non-admin role is rejected
    bad = Admin(id="x", username="x", role="viewer")
    with pytest.raises(AuthorizationError):
        admin.add_question(bad, Question(id="q10", prompt="x",
                                         options=["1/2"], correct_answer="1/2"))
    # not logged in at all
    with pytest.raises(AuthenticationError):
        admin.login("admin", "wrongpass")


def test_user_service_persist_boundary():
    _, _, _, us = make_services()
    us.register("newplayer", "pw")
    assert us.authenticate("newplayer", "pw").username == "newplayer"
