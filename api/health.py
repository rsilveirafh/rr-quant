"""Sonda minima para confirmar que o runtime Python da Vercel iniciou."""


def app(environ, start_response):
    """Aplicacao WSGI sem dependencias nem imports do projeto."""
    start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
    return [b'{"ok":true}']
