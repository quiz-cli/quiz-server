from dataclasses import dataclass
from fastapi import WebSocket
import logging
from quiz_common.models import Question

@dataclass
class Player:
    _websocket: WebSocket
    name: str
    accepting_answer: bool = False

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


class Players:
    _players: list[Player] = []

    def find(self, player_id: str): ...

    def add(self, player: Player):
        self._players.append(player)

    def remove(self, player: Player):
        self._players.remove(player)

    def unblock_players(self):
        for player in self._players:
            player.accepting_answer = True

    async def send(self, data: dict):
        for player in self._players:
            await player.send(data)

    async def close_connection(self, msg: str):
        """Print results of the quiz and disconnect the clients"""

        for player in self._players:
            await player.close_connection(msg)


class Results:
    _results: dict[tuple[str, int], dict] = {}

    def check_answer(
        self, player: Player, question: Question, question_number: int, answer: str
    ):
        self._results[(player.name, question_number)] = {
            "answer": answer,
            "correct": True
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
