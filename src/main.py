"""FastAPI application exposing WebSocket endpoints for the quiz game."""

import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from quiz_common.models import Quiz

from models import Player, Players, Results

logger = logging.getLogger(__name__)

app = FastAPI()
app.state.players = Players()
app.state.results = Results()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d|%(message)s",
    datefmt="%H:%M:%S",
)


@app.websocket("/connect/{player_name}")
async def connect(ws: WebSocket, player_name: str) -> None:
    """Handle a player's WebSocket connection for participating in the quiz."""
    await ws.accept()

    quiz = getattr(app.state, "quiz", None)
    if quiz is None:
        await ws.close(reason="Quiz not started yet")
        return

    await ws.send_json({"text": quiz.name})
    await ws.send_json({"text": "Check your name on the screen!"})

    player = Player(ws, player_name)
    app.state.players.add(player)

    logger.info("Player connects: %s", player_name)

    try:
        while True:
            data = await ws.receive_json()
            logger.info("Client %s sent: %s", player_name, data)

            if player.is_allowed_answer:
                await player.send({"type": "repeat", "text": data["answer"]})
                player.block_answer()
                app.state.results.check_answer(
                    player,
                    app.state.quiz.current_question,
                    data["answer"],
                )

    except WebSocketDisconnect:
        logger.info("Player disconnects: %s", player_name)
        app.state.players.remove(player)


@app.websocket("/admin")
async def admin(ws: WebSocket) -> None:
    """Admin interface to control the quiz flow and proceeding through questions."""
    await ws.accept()
    quiz_data = await ws.receive_json()
    app.state.quiz = Quiz(**quiz_data)

    logger.info(
        "Quiz server started running quiz: %s",
        app.state.quiz.name,
    )
    await ws.send_text(f'Admin for the quiz "{app.state.quiz.name}"')

    try:
        while True:
            proceed_char = await ws.receive_text()
            logger.info("Admin sent: %s", proceed_char)
            if proceed_char.lower() != "y":
                continue

            try:
                question = next(app.state.quiz)
            except StopIteration:
                await ws.send_json(app.state.results.as_list())

                msg = "Quiz ended"
                await app.state.players.close_connection(msg)
                await ws.close(reason=msg)
                return

            logger.info("Next question")
            app.state.players.unblock_players()
            await app.state.players.send(question.ask())
    except WebSocketDisconnect:
        logger.info("Admin disconnected")
