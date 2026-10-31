"""Tests for the domain model (SF-MODEL, SF-STATE, SF-SCORE)."""

import pytest

from spacefractions.model import (
    Game, GameState, Question, User, Admin,
)


def make_q(qid="q1", correct="3/4"):
    return Question(id=qid, prompt="q?", options=["3/4", "1/8"],
                    correct_answer=correct)


def test_question_fraction_normalization():
    q = make_q(correct="1/2")
    assert q.check_answer("2/4") is True
    assert q.check_answer("1/2") is True
    assert q.check_answer("1/3") is False


def test_game_state_transitions():
    g = Game(id="g1")
    assert g.state == GameState.PLAYING
    g.pause()
    assert g.state == GameState.PAUSED
    g.resume()
    assert g.state == GameState.PLAYING
    g.game_over()
    assert g.state == GameState.GAME_OVER


def test_game_ignores_answer_when_paused():
    g = Game(id="g1")
    g.pause()
    assert g.submit_answer(make_q(), "3/4") is False
    assert g.score == 0


def test_game_scoring_and_view_score():
    g = Game(id="g1")
    assert g.submit_answer(make_q(), "3/4") is True
    assert g.submit_answer(make_q("q2", "1/2"), "1/3") is False
    assert g.view_score() == 1
    assert g.answered == 2


def test_user_play_and_view_score():
    g = Game(id="g1", questions=[make_q()])
    u = User(id="u1", username="p")
    u.play_game(g)
    assert g.state == GameState.PLAYING
    g.submit_answer(g.questions[0], "3/4")
    assert u.view_score(g) == 1


def test_admin_authorization():
    a = Admin(id="a1", username="admin", role="admin")
    assert a.is_authorized() is True
    u = Admin(id="a2", username="noadmin", role="viewer")
    assert u.is_authorized() is False


def test_question_to_from_dict_roundtrip():
    q = make_q()
    assert Question.from_dict(q.to_dict()) == q


def test_game_reset():
    g = Game(id="g1")
    g.submit_answer(make_q(), "3/4")
    g.game_over()
    g.reset()
    assert g.score == 0 and g.state == GameState.PLAYING
