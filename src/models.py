from dataclasses import dataclass
from fastapi import WebSocket
import logging
from quiz_common.models import Question

@dataclass
class Player:
    _websocket: WebSocket
    name: str
    _allowed_answer: bool = False

    async def send(self, data: dict):
        try:
            await self._websocket.send_json(data)
        except RuntimeError:
            logging.info(f"Player unreachable, cannot send data: {self.name}")

    async def close_connection(self, msg: str):
        try:
            await self._websocket.close(reason=msg)
        except RuntimeError:
            logging.info(
                f"Player unreachable, cannot close the connection: {self.name}"
            )

    @property
    def is_allowed_answer(self) -> bool:
        return self._allowed_answer

    def block_answer(self):
        self._allowed_answer = False

    def allow_answer(self):
        self._allowed_answer = True


class Players:
    _players: list[Player] = []

    def add(self, player: Player):
        self._players.append(player)

    def remove(self, player: Player):
        self._players.remove(player)

    def unblock_players(self):
        for player in self._players:
            player.allow_answer()

    async def send(self, data: dict):
        for player in self._players:
            await player.send(data)

    async def close_connection(self, msg: str):
        """Disconnect all the players"""

        for player in self._players:
            await player.close_connection(msg)


class Results:
    _results: dict[tuple[str, int], dict] = {}

    def check_answer(
        self, player: Player, question: Question, question_number: int, answer: str
    ):
        self._results[(player.name, question_number)] = {
            "answer": answer,
            "correct": True  # Temporary placeholder
        }

    def as_list(self) -> list[dict]:
        return [
            {
                "player": player,
                "question_number": number,
                **result,
            }
            for (player, number), result in self._results.items()
        ]
