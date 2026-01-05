"""Domain models for players connected to the quiz server and their results."""

import logging
from typing import ClassVar

from fastapi import WebSocket
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class Player(BaseModel):
    """A connected quiz participant backed by a WebSocket."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    websocket: WebSocket
    name: str
    allowed_answer: bool = False

    async def send(self, data: dict) -> None:
        """Send a JSON-serializable payload to the player."""
        try:
            await self.websocket.send_json(data)
        except RuntimeError:
            logger.info(
                "Player unreachable, cannot send data: %s",
                self.name,
            )

    async def close_connection(self, msg: str) -> None:
        """Close the player's WebSocket connection with a reason."""
        try:
            await self.websocket.close(reason=msg)
        except RuntimeError:
            logger.info(
                "Player unreachable, cannot close the connection: %s",
                self.name,
            )

    @property
    def is_allowed_answer(self) -> bool:
        """Return whether the player is currently allowed to answer."""
        return self.allowed_answer

    def block_answer(self) -> None:
        """Disallow the player from submitting another answer."""
        self.allowed_answer = False

    def allow_answer(self) -> None:
        """Allow the player to submit an answer."""
        self.allowed_answer = True


class Players:
    """A collection of connected players."""

    _players: ClassVar[list[Player]] = []

    def add(self, player: Player) -> None:
        """Register a newly connected player."""
        self._players.append(player)

    def remove(self, player: Player) -> None:
        """Unregister a disconnected player."""
        self._players.remove(player)

    def unblock_players(self) -> None:
        """Allow all players to answer the current question."""
        for player in self._players:
            player.allow_answer()

    async def send(self, data: dict) -> None:
        """Broadcast a message to all connected players."""
        for player in self._players:
            await player.send(data)

    async def close_connection(self, msg: str) -> None:
        """Disconnect all players with the given reason."""
        for player in self._players:
            await player.close_connection(msg)


class Results:
    """Store and expose answers submitted by players."""

    _results: ClassVar[dict[tuple[str, int], dict]] = {}

    def check_answer(
        self,
        player: Player,
        question_number: int,
        answer: str,
    ) -> None:
        """Record a player's answer for a question."""
        self._results[(player.name, question_number)] = {
            "answer": answer,
            "correct": True,  # Temporary placeholder
        }

    def as_list(self) -> list[dict]:
        """Return all recorded results as a list of flat dictionaries."""
        return [
            {
                "player": player,
                "question_number": number,
                **result,
            }
            for (player, number), result in self._results.items()
        ]
