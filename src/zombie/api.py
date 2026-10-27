"""API HTTP: valida la petición, corre la comparación y devuelve JSON.

La misma función sirve en AWS Lambda (`lambda_handler`, detrás de una Function URL
o API Gateway) y en el servidor local de desarrollo (servidor.py).
Ver docs/api.md.
"""
import base64
import json
from dataclasses import fields, replace

from .config import Escenario, Plaga, Recursos
from .montecarlo import comparar
from .poblacion import BARRIOS

INICIOS = ("aleatorio", "mercado", "colegio", *BARRIOS)

# Límites de cada parámetro: protegen el costo y el tiempo de cómputo.
LIMITES = {
    "escenario": {
        "n_personas": (1000, 20_000),
        "dias": (30, 365),
        "semilla": (0, 2**31 - 1),
        "casos_iniciales": (1, 100),
    },
    "plaga": {
        "r0": (0.5, 10.0),
        "dias_latencia": (1.0, 21.0),
        "dias_infeccioso": (1.0, 21.0),
        "deteccion": (0.0, 1.0),
    },
    "recursos": {
        "presupuesto": (0.0, 1_000_000.0),
        "costo_vacuna": (0.01, 10_000.0),
        "vacunas_disponibles": (0, 20_000),
        "vacunas_por_dia": (1, 20_000),
        "dia_inicio": (0, 365),
        "eficacia": (0.0, 1.0),
        "dias_cierre": (0, 365),
        "cumplimiento_cierre": (0.0, 1.0),
        "costo_cierre_mercado": (0.0, 1_000_000.0),
        "costo_cierre_colegio": (0.0, 1_000_000.0),
    },
}
REPETICIONES = (5, 200)
REPETICIONES_POR_DEFECTO = 50


class PeticionInvalida(ValueError):
    pass


def _numero(grupo: str, nombre: str, valor, tipo):
    minimo, maximo = LIMITES[grupo][nombre]
    try:
        numero = tipo(valor)
    except (TypeError, ValueError):
        raise PeticionInvalida(f"{nombre} debe ser un número") from None
    if not minimo <= numero <= maximo:
        raise PeticionInvalida(f"{nombre} debe estar entre {minimo} y {maximo}")
    return numero


def _grupo(objeto, grupo: str, datos: dict):
    if not isinstance(datos, dict):
        raise PeticionInvalida(f"{grupo} debe ser un objeto")
    cambios = {}
    for campo in fields(objeto):
        if campo.name in datos and campo.name in LIMITES[grupo]:
            cambios[campo.name] = _numero(grupo, campo.name, datos[campo.name], campo.type)
    desconocidos = set(datos) - {c.name for c in fields(objeto)}
    if desconocidos:
        raise PeticionInvalida(f"Campos desconocidos en {grupo}: {', '.join(sorted(desconocidos))}")
    return replace(objeto, **cambios)


def leer_peticion(cuerpo: dict) -> tuple[Escenario, int]:
    """Convierte el JSON de la petición en un Escenario validado (lo que falta toma el valor por defecto)."""
    if not isinstance(cuerpo, dict):
        raise PeticionInvalida("El cuerpo debe ser un objeto JSON")
    datos = dict(cuerpo.get("escenario", {}))
    plaga = _grupo(Plaga(), "plaga", datos.pop("plaga", {}))
    recursos = _grupo(Recursos(), "recursos", datos.pop("recursos", {}))

    inicio = datos.pop("inicio", Escenario.inicio)
    if inicio not in INICIOS:
        raise PeticionInvalida(f"inicio debe ser uno de: {', '.join(INICIOS)}")
    esc = _grupo(Escenario(), "escenario", datos)
    esc = replace(esc, inicio=inicio, plaga=plaga, recursos=recursos)

    if esc.recursos.dia_inicio > esc.dias:
        raise PeticionInvalida("dia_inicio no puede ser mayor que dias")
    repeticiones = cuerpo.get("repeticiones", REPETICIONES_POR_DEFECTO)
    if not isinstance(repeticiones, int) or not REPETICIONES[0] <= repeticiones <= REPETICIONES[1]:
        raise PeticionInvalida(f"repeticiones debe ser un entero entre {REPETICIONES[0]} y {REPETICIONES[1]}")
    return esc, repeticiones


def parametros() -> dict:
    """Valores por defecto y límites, para que la interfaz arme sus controles."""
    return {
        "por_defecto": Escenario().a_dict(),
        "limites": {g: {k: list(v) for k, v in campos.items()} for g, campos in LIMITES.items()},
        "inicios": list(INICIOS),
        "repeticiones": {"por_defecto": REPETICIONES_POR_DEFECTO, "limites": list(REPETICIONES)},
    }


def atender(metodo: str, ruta: str, cuerpo: str | None) -> tuple[int, dict]:
    """Enruta una petición y devuelve (código HTTP, JSON)."""
    ruta = "/" + ruta.strip("/")
    try:
        if metodo == "GET" and ruta in ("/api/parametros", "/parametros"):
            return 200, parametros()
        if metodo == "GET" and ruta in ("/api/salud", "/salud"):
            return 200, {"estado": "ok"}
        if metodo == "POST" and ruta in ("/api/simular", "/simular"):
            try:
                datos = json.loads(cuerpo or "{}")
            except json.JSONDecodeError:
                raise PeticionInvalida("El cuerpo no es JSON válido") from None
            esc, repeticiones = leer_peticion(datos)
            return 200, comparar(esc, repeticiones)
        return 404, {"error": f"No existe {metodo} {ruta}"}
    except PeticionInvalida as e:
        return 400, {"error": str(e)}


def lambda_handler(evento: dict, contexto) -> dict:
    """Entrada de AWS Lambda (formato de evento 2.0 de Function URL / HTTP API)."""
    http = evento.get("requestContext", {}).get("http", {})
    cuerpo = evento.get("body")
    if cuerpo and evento.get("isBase64Encoded"):
        cuerpo = base64.b64decode(cuerpo).decode("utf-8")
    codigo, respuesta = atender(http.get("method", "GET"), evento.get("rawPath", "/"), cuerpo)
    return {
        "statusCode": codigo,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(respuesta, ensure_ascii=False),
    }
