import json

import pytest

from zombie.api import PeticionInvalida, atender, lambda_handler, leer_peticion

PEQUENO = {"escenario": {"n_personas": 1000, "dias": 60}, "repeticiones": 5}


def test_lo_que_falta_toma_el_valor_por_defecto():
    esc, repeticiones = leer_peticion({})
    assert esc.plaga.r0 == 2.5
    assert repeticiones == 50


def test_lee_parametros_anidados():
    esc, _ = leer_peticion({"escenario": {"inicio": "mercado", "plaga": {"r0": 5},
                                          "recursos": {"vacunas_disponibles": 500}}})
    assert (esc.inicio, esc.plaga.r0, esc.recursos.vacunas_disponibles) == ("mercado", 5.0, 500)


@pytest.mark.parametrize("cuerpo", [
    {"escenario": {"plaga": {"r0": 99}}},
    {"escenario": {"n_personas": 10_000_000}},
    {"escenario": {"inicio": "Quito"}},
    {"escenario": {"plaga": {"virulencia": 3}}},
    {"escenario": {"recursos": {"eficacia": "mucha"}}},
    {"repeticiones": 100_000},
])
def test_rechaza_valores_fuera_de_rango(cuerpo):
    with pytest.raises(PeticionInvalida):
        leer_peticion(cuerpo)


def test_simular_devuelve_planes_y_recomendacion():
    codigo, res = atender("POST", "/api/simular", json.dumps(PEQUENO))
    assert codigo == 200
    assert {p["id"] for p in res["planes"]} >= {"ninguna", "azar", "anillo", "centralidad"}
    assert res["recomendado"] in {p["id"] for p in res["planes"]}


def test_errores_devuelven_400_y_404():
    assert atender("POST", "/api/simular", "{no es json")[0] == 400
    assert atender("GET", "/api/otra", None)[0] == 404


def test_lambda_handler_con_evento_de_function_url():
    evento = {
        "rawPath": "/api/simular",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps(PEQUENO),
        "isBase64Encoded": False,
    }
    respuesta = lambda_handler(evento, None)
    assert respuesta["statusCode"] == 200
    assert json.loads(respuesta["body"])["recomendado"]
