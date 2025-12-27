import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

# from datetime import datetime
from quiz_common.models import Quiz
from models import Player, Players, Results


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        quiz_file = os.environ["QUIZ"]

        yaml = YAML(typ="safe")
        with open(quiz_file, encoding="utf-8") as file:
            quiz_data = yaml.load(file)

        app.state.quiz = Quiz(**quiz_data)

    except KeyError:
        logging.fatal("Environment variable QUIZ was not set!")
    except (OSError, YAMLError, TypeError):
        logging.fatal(f"Can't load a quiz file: {quiz_file}")

    app.state.players = Players()
    app.state.results = Results()
    logging.info(f"Quiz server started running quiz: {app.state.quiz.name}")

    yield  # Second half of a life span - this is executed once server exits


app = FastAPI(lifespan=lifespan)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d|%(message)s",
    datefmt="%H:%M:%S",
    # filename=f'{datetime.now():quiz-log_%Y-%m-%d_%H:%M:%S.txt}'
    # filename="quiz-log_.txt",
)


@app.websocket("/connect/{player_name}")
async def connect(ws: WebSocket, player_name: str):
    await ws.accept()
    await ws.send_json({"text": app.state.quiz.name})
    await ws.send_json({"text": "Check your name on the screen!"})

    player = Player(ws, player_name)
    app.state.players.add(player)

    msg = f"Player connects: {player_name}"
    logging.info(msg)

    try:
        while True:
            data = await ws.receive_json()
            logging.info(f"Client {player_name} sent: {data}")

            if player.accepting_answer:
                await player.send({"type": "repeat", "text": data["answer"]})
                player.accepting_answer = False
                app.state.results.check_answer(
                    player,
                    app.state.quiz.question,
                    app.state.quiz.current_question,
                    data["answer"],
                )

    except WebSocketDisconnect:
        logging.info(f"Player disconnects: {player_name}")
        # app.state.players.remove(player)


@app.websocket("/admin")
async def admin(ws: WebSocket) -> None:
    """
    Admin interface to control the quiz flow and proceeding through questions
    """
    await ws.accept()
    await ws.send_text(f"Admin for the quiz {app.state.quiz.name}")

    try:
        while True:
            proceed_char = await ws.receive_text()
            logging.info(f"Admin sent: {proceed_char}")
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

            logging.info("Next question")
            app.state.players.unblock_players()
            await app.state.players.send(question.ask())
    except WebSocketDisconnect:
        logging.info("Admin disconnected")
