# quiz-server

This is the server side of a client–server quiz application. It aims to provide
a quiz experience similar to **Kahoot**, but in a much lighter and more open
form, suitable for terminal/CLI-based clients.

The server is a **FastAPI** application exposing WebSocket endpoints:

- an admin endpoint to start and control a quiz,
- a player endpoint where clients register and submit their answers.

The server-side entity `Player` is implemented as **Pydantic model**.
Shared quiz structure `Quiz` comes from the companion
[`quiz-common`](https://github.com/quiz-cli/quiz-common) package.

## Features

- WebSocket-based real-time quiz flow
- Multiple players connected simultaneously
- Admin-driven progression through questions
- Collection of player answers and simple result aggregation

## Running the server

Get the `uv` tool.

```bash
$ uv tool install . --editable
```

```bash
$ uv run fastapi dev src/main.py
```

## Contribution

The code needs to comply with:

```bash
$ uv run ruff format
```

```bash
$ uv run ruff check
```
