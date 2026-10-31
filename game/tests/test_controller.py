"""Tests for the desktop controller/state behavior (EMAIL-DESKTOP, SF-STATE).

These run headless: they exercise GameController without instantiating Tk.
"""

import pytest

from spacefractions.model import GameState, Question
from spacefractions.services import (
    QuestionService, AdminService, GameService, UserService,
)
from spacefractions.ui import GameController
from spacefractions.errors import AuthorizationError, AuthenticationError
from spacefractions.sample_questions import SAMPLE_QUESTIONS


def make_controller():
    qs = QuestionService()
    for d in SAMPLE_QUESTIONS:
        qs.add_question(Question.from_dict(d))
    return GameController(
        GameService(qs), AdminService(qs), UserService())


def test_controller_start_and_progress():
    c = make_controller()
    assert c.start_game() == GameState.PLAYING
    assert c.current_question() is not None
    # answer all correctly -> game over
    while c.current_game.state != GameState.GAME_OVER:
        c.submit_answer(c.current_question().correct_answer)
    assert c.current_game.state == GameState.GAME_OVER
    assert c.score() == len(SAMPLE_QUESTIONS)


def test_controller_pause_resume():
    c = make_controller()
    c.start_game()
    c.pause()
    assert c.current_game.state == GameState.PAUSED
    c.resume()
    assert c.current_game.state == GameState.PLAYING


def test_controller_admin_login_and_add():
    c = make_controller()
    a = c.admin_login("admin", "admin")
    assert c.current_admin is a
    c.admin_add_question(Question(id="q99", prompt="p",
                                  options=["1/2"], correct_answer="1/2"))
    assert c.game_service.question_service.get_question("q99") is not None


def test_controller_admin_negative():
    c = make_controller()
    with pytest.raises(AuthenticationError):
        c.admin_login("admin", "bad")
    # not logged in -> authorization error
    with pytest.raises(AuthorizationError):
        c.admin_add_question(Question(id="q98", prompt="p",
                                      options=["1/2"], correct_answer="1/2"))


def test_paused_answer_does_not_advance_question():
    c = make_controller()
    c.start_game()
    first = c.current_question()
    c.pause()
    assert c.submit_answer(first.correct_answer) is False
    assert c.current_question().id == first.id
    assert c.current_game.answered == 0
    assert c.current_game.state == GameState.PAUSED


def test_finished_game_does_not_accept_more_answers():
    c = make_controller()
    c.start_game()
    while c.current_game.state != GameState.GAME_OVER:
        c.submit_answer(c.current_question().correct_answer)
    score = c.score()
    answered = c.current_game.answered
    assert c.submit_answer(c.current_question().correct_answer) is False
    assert c.score() == score
    assert c.current_game.answered == answered
