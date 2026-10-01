"""Unit tests for per-question server results."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from models import Player, Players, Results


@dataclass
class FakeWebSocket:
    """Record JSON messages sent by a player model."""

    messages: list[dict[str, Any]] = field(default_factory=list)

    async def send_json(self, data: dict[str, Any]) -> None:
        """Store a sent JSON message for later assertions."""
        self.messages.append(data)


@pytest.fixture(autouse=True)
def reset_shared_state() -> None:
    """Clear class-level player and result state before every test."""
    Players._players.clear()  # noqa: SLF001
    Results._results.clear()  # noqa: SLF001


def create_player(name: str) -> tuple[Player, FakeWebSocket]:
    """Create a player with an in-memory websocket for unit testing."""
    websocket = FakeWebSocket()
    player = Player.model_construct(websocket=websocket, name=name)
    return player, websocket


def test_for_player_question_returns_matching_result() -> None:
    """Return the result belonging to the requested player and question."""
    results = Results()
    alice, _ = create_player("alice")
    bob, _ = create_player("bob")
    results.check_answer(alice, "a", 0, "a")
    results.check_answer(alice, "b", 1, "a")
    results.check_answer(bob, "a", 0, "a")

    assert results.for_player_question("alice", 0) is True
    assert results.for_player_question("alice", 1) is False
    assert results.for_player_question("bob", 0) is True
    assert results.for_player_question("bob", 1) is None


def test_block_players_disallows_answers_for_all_players() -> None:
    """Block every connected player when a question is closed."""
    players = Players()
    alice, _ = create_player("alice")
    bob, _ = create_player("bob")
    players.add(alice)
    players.add(bob)
    players.unblock_players()

    players.block_players()

    assert not alice.is_allowed_answer
    assert not bob.is_allowed_answer


def test_send_question_results_sends_personal_result() -> None:
    """Send each player the correct answer with their own correctness."""
    players = Players()
    results = Results()
    alice, alice_socket = create_player("alice")
    bob, bob_socket = create_player("bob")
    carol, carol_socket = create_player("carol")
    players.add(alice)
    players.add(bob)
    players.add(carol)
    results.check_answer(alice, "a", 0, "a")
    results.check_answer(bob, "b", 0, "a")

    asyncio.run(players.send_question_results(results, 0, "a"))

    assert alice_socket.messages == [
        {"type": "question_result", "correct_answer": "a", "correct": True}
    ]
    assert bob_socket.messages == [
        {"type": "question_result", "correct_answer": "a", "correct": False}
    ]
    assert carol_socket.messages == [
        {"type": "question_result", "correct_answer": "a", "correct": None}
    ]
