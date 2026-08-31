"""FastAPI application exposing WebSocket endpoints for the quiz game."""

import logging
import string

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter
from quiz_common.models import Question, QuestionMessage, Quiz, Message, TextMessage, AnswerMessage

from models import Player, Players, Results

logger = logging.getLogger(__name__)

app = FastAPI()
app.state.players = Players()
app.state.results = Results()
app.state.in_progress = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d|%(message)s",
    datefmt="%H:%M:%S",
)


def correct_answer(question: Question) -> str:
    """Extract the correct answer from a question dictionary."""
    correct_answer_string = ""
    for letter, opt in zip(string.ascii_letters, question.options, strict=False):
        if opt.correct:
            correct_answer_string += letter
    return correct_answer_string


@app.websocket("/connect/{player_name}")
async def connect(ws: WebSocket, player_name: str) -> None:
    """Handle a player's WebSocket connection for participating in the quiz."""
    await ws.accept()

    quiz = getattr(app.state, "quiz", None)
    if quiz is None:
        await ws.close(reason="Quiz not started yet")
        return
    await ws.send_json(TextMessage(text=quiz.name).model_dump())
    await ws.send_json(TextMessage(text="{user_name}, check your name on the screen!", params={"user_name": player_name}).model_dump())

    player = Player(websocket=ws, name=player_name)
    app.state.players.add(player)

    logger.info("Player connects: %s", player_name)
    await app.state.admin.send_text(
        f"{len(app.state.players)}. player {player_name} connected"
    )

    try:
        while True:
            response = await ws.receive_json()
            data = TypeAdapter(Message).validate_python(response)
            logger.info("Client %s sent: %s", player_name, data.answer)

            if player.is_allowed_answer:
                message = TextMessage(text="{user_name}, check your answer: {answer}", 
                                      params={"user_name": data.client_id, "answer": data.answer})
                await player.send(message.model_dump())
                player.block_answer()
                app.state.results.check_answer(
                    player,
                    data.answer,
                    app.state.quiz.current_question,
                    app.state.correct_answer,
                )

    except WebSocketDisconnect:
        logger.info("Player disconnects: %s", player_name)
        app.state.players.remove(player)
        if app.state.in_progress:
            await app.state.admin.send_text(f"Player {player_name} disconnected")


@app.websocket("/admin")
async def admin(ws: WebSocket) -> None:
    """Admin interface to control the quiz flow and proceeding through questions."""
    await ws.accept()
    quiz_data = await ws.receive_json()
    app.state.quiz = Quiz(**quiz_data)
    app.state.in_progress = True

    app.state.admin = ws

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
                app.state.correct_answer = correct_answer(question)
            except StopIteration:
                await ws.send_json(app.state.results.as_list())
                await app.state.players.send_final_results(app.state.results)
                app.state.results.remove_results()

                msg = "Quiz ended"
                app.state.in_progress = False
                await app.state.players.close_connection(msg)
                await ws.close(reason=msg)
                return

            logger.info("Next question")
            question_message = QuestionMessage(question=question)
            app.state.players.unblock_players()
            await app.state.players.send(question_message.model_dump())
            await ws.send_json(question.ask())
    except WebSocketDisconnect:
        logger.info("Admin disconnected")
