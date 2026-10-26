"""Servidor MCP de JKanban para el proyecto SF.

Expone los planes y actividades de cada proyecto sobre la API REST de JKanban:

    Proyecto SF -> Project
      Plan      -> Group (columna del tablero)
        Actividad -> Task
          Paso      -> TodoItem

Capas:
    client.py   cliente HTTP de la API (login JWT, reintento ante 401)
    service.py  operaciones en vocabulario SF (no depende del SDK de MCP)
    server.py   registro de las tools MCP y arranque por stdio
"""
