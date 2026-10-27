"""Servidor local de desarrollo: la misma API que en Lambda, en http://localhost:8000.

    PYTHONPATH=src python -m zombie.servidor
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import atender

PUERTO = 8000


class Manejador(BaseHTTPRequestHandler):
    def _responder(self, codigo: int, datos: dict) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        # Solo para desarrollo: la interfaz corre en otro puerto (Vite).
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self._responder(204, {})

    def do_GET(self):
        self._responder(*atender("GET", self.path, None))

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(largo).decode("utf-8") if largo else None
        self._responder(*atender("POST", self.path, cuerpo))


def main() -> None:
    print(f"API local en http://localhost:{PUERTO}/api/simular")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()


if __name__ == "__main__":
    main()
