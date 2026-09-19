#!/usr/bin/env python3
"""
Politica de decision v2 de la capa 1, y comparacion contra la v1.

QUE CAMBIA Y POR QUE
--------------------
La v1 usaba dos umbrales globales: confianza 0.60 y margen 0.03. La sonda
mostro que estaban mal fundados.

  1. SE QUITA EL UMBRAL GLOBAL DE CONFIANZA.
     Las similitudes dentro de distribucion tienen p5 = 0.733 y las de textos
     absurdos llegan a 0.727. Un solo numero para las 27 intenciones deja fuera
     ejemplos legitimos de las intenciones con centroide flojo, o deja pasar
     todo. La dispersion entre centroides es real: el p5 propio va de 0.688
     (delivery_options) a 0.844 (payment_issue).

  2. ENTRA UN UMBRAL POR INTENCION.
     Para cada intencion se usa el percentil 5 de la similitud de sus propios
     ejemplos de entrenamiento con su centroide. Un mensaje que no alcanza ese
     piso no se parece a esa intencion ni al nivel de sus casos mas atipicos.
     El numero sale de los datos y no de una eleccion a ojo.

  3. EL CARRIL AUTOMATICO EXIGE COINCIDENCIA POSITIVA.
     Este es el cambio de fondo. En la v1, `automatico` era el destino de
     cualquier mensaje que cayera cerca de un centroide automatico, incluso por
     descarte. Es el carril sin supervision humana, asi que llegar ahi deberia
     costar mas que llegar a copiloto, no menos. En la v2 un mensaje va a
     `automatico` solo si supera el umbral de su intencion Y separa del segundo
     candidato por un margen mayor. Si no, baja a copiloto.

     La asimetria es deliberada y es la misma de la Fase 2 (3.6): un caso facil
     enviado a copiloto cuesta minutos de un agente.

LO QUE ESTA POLITICA NO ARREGLA
-------------------------------
El nucleo duro parafraseado. Esos mensajes son texto de atencion al cliente
legitimo —una queja sobre un producto— y puntuan alto porque el TEMA es
correcto. Lo que los distingue es que hubo dano a una persona, y eso es un
detalle del contenido, no el tema. Ninguna politica sobre similitud temantica lo
va a capturar. Se mide para dejar constancia, no porque se espere que cambie.

TAMBIEN DIAGNOSTICA LOS RuntimeWarning DE NUMPY
-----------------------------------------------
matmul emitio 'divide by zero', 'overflow' e 'invalid value' en macOS. Los
valores resultantes se ven correctos, lo que apunta a un aviso espurio del BLAS
de Accelerate. No se da por sentado: se comprueba si hay NaN o infinitos y se
contrasta el producto de matrices contra una suma hecha a mano.

LA v3
------
Anadida despues de probar la consola en vivo: el margen se mide entre CARRILES y
no entre intenciones. Ver `margen_entre_carriles()`.

USO
    python politica_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import capa0_reglas
from capa1_semantica import RUTA_CACHE, Clasificador, embed_lote
from evaluar_clasificador import SUPERVISION, cargar_prueba

AQUI = Path(__file__).parent
RUTA_UMBRALES = AQUI / "modelo" / "umbrales_por_intencion.json"

# Margen exigido para entrar al carril sin supervision. Mas alto que el general
# porque el error ahi no lo corrige nadie.
MARGEN_AUTOMATICO = 0.05
# Se mantiene en 0.03, igual que la v1. Bajarlo a 0.02 fue un error de la primera
# version de este archivo: aflojaba el criterio general mientras se endurecia el
# del carril automatico, y dejo escapar un caso de copiloto hacia derivacion.
MARGEN_GENERAL = 0.03


# --------------------------------------------------------------------------------------

def diagnosticar_numpy(V: np.ndarray, C: np.ndarray) -> None:
    print("=" * 74)
    print("DIAGNOSTICO DE LOS AVISOS DE NUMPY")
    print("=" * 74)
    for nombre, M in (("vectores", V), ("centroides", C)):
        print(f"  {nombre:12s} dtype={M.dtype}  NaN={np.isnan(M).sum()}  "
              f"inf={np.isinf(M).sum()}  |min|={np.abs(M).min():.2e}  "
              f"max={np.abs(M).max():.3f}")
    with np.errstate(all="ignore"):
        S = V @ C.T
    # Suma explicita en float64 para la primera fila: si coincide con matmul, el
    # aviso no afecto el resultado.
    manual = np.array([float(np.sum(V[0].astype(np.float64) * c.astype(np.float64)))
                       for c in C])
    dif = float(np.abs(S[0] - manual).max())
    print(f"  resultado: NaN={np.isnan(S).sum()}  inf={np.isinf(S).sum()}  "
          f"rango [{np.nanmin(S):.3f}, {np.nanmax(S):.3f}]")
    print(f"  maxima diferencia contra la suma manual en float64: {dif:.2e}")
    print("  -> " + ("aviso espurio: los valores coinciden y estan en rango valido"
                     if dif < 1e-4 and not np.isnan(S).any()
                     else "ATENCION: el resultado SI esta afectado, no usar estas cifras"))


# --------------------------------------------------------------------------------------

def decidir_v1(clf, i1, i2, conf, margen):
    if conf < 0.60:
        return "copiloto", f"confianza global baja ({conf:.3f})"
    if margen < 0.03:
        return "copiloto", f"margen bajo ({margen:.3f})"
    return clf.carriles[i1], None


def decidir_v2(clf, umbrales, i1, i2, conf, margen):
    intencion = clf.intenciones[i1]
    carril = clf.carriles[i1]
    piso = umbrales[intencion]

    if conf < piso:
        return "copiloto", f"por debajo del piso de {intencion} ({conf:.3f} < {piso:.3f})"
    if carril == "automatico" and margen < MARGEN_AUTOMATICO:
        return "copiloto", (f"el carril automatico exige margen >= {MARGEN_AUTOMATICO} "
                            f"y hay {margen:.3f} contra {clf.intenciones[i2]}")
    if margen < MARGEN_GENERAL:
        return "copiloto", f"margen bajo ({margen:.3f})"
    return carril, None


def margen_entre_carriles(clf, fila, orden) -> tuple[float, str | None]:
    """Distancia del mejor candidato al mejor candidato de OTRO carril.

    POR QUE ESTE MARGEN Y NO EL DE LA v2
    ------------------------------------
    La v2 mide la distancia entre las dos intenciones mas cercanas. Pero la
    decision que se esta tomando no es sobre intenciones, es sobre CARRILES. Si
    las dos primeras candidatas van al mismo sitio, la distancia entre ellas no
    dice nada sobre el riesgo de enrutar mal: solo dice que el modelo duda entre
    dos formas de nombrar lo mismo, y esa duda es inofensiva.

    El caso que lo dejo en evidencia, probado en la consola:

        "hola, cuanto tiempo tengo para hacer una devolucion"
          delivery_period       0.790  automatico   <- elegida (intencion ERRONEA)
          check_refund_policy   0.759  automatico   <- la correcta
          track_refund          0.758  automatico
          get_refund            0.744  copiloto     <- primera de otro carril

    La v2 calcula 0.790 - 0.759 = 0.031 y degrada a copiloto. Pero las tres
    primeras coinciden en el carril: el clasificador se equivoco de intencion y
    aun asi el carril estaba bien. La duda que SI importa es contra get_refund
    —consultar la politica frente a pedir el reembolso—, y esa distancia es
    0.790 - 0.744 = 0.046.

    Devuelve el margen y la intencion contra la que se midio, para el registro.
    """
    carril_top = clf.carriles[orden[0]]
    for i in orden[1:]:
        if clf.carriles[i] != carril_top:
            return float(fila[orden[0]] - fila[i]), clf.intenciones[i]
    # Ningun otro carril entre los 27: no hay ambiguedad de enrutamiento.
    return 1.0, None


def decidir_v3(clf, umbrales, fila, orden):
    """Como la v2, pero el margen se mide entre CARRILES y no entre intenciones."""
    i1 = orden[0]
    intencion = clf.intenciones[i1]
    carril = clf.carriles[i1]
    conf = float(fila[i1])
    piso = umbrales[intencion]

    if conf < piso:
        return "copiloto", f"por debajo del piso de {intencion} ({conf:.3f} < {piso:.3f})"

    margen, rival = margen_entre_carriles(clf, fila, orden)
    contra = f" contra {rival} ({clf.carriles[clf.intenciones.index(rival)]})" if rival else ""

    if carril == "automatico" and margen < MARGEN_AUTOMATICO:
        return "copiloto", (f"el carril automatico exige margen de carril >= "
                            f"{MARGEN_AUTOMATICO} y hay {margen:.3f}{contra}")
    if margen < MARGEN_GENERAL:
        return "copiloto", f"margen de carril bajo ({margen:.3f}{contra})"
    return carril, None



MARGENES_BARRIDO = (0.00, 0.02, 0.03, 0.04, 0.05, 0.07)


def barrer(clf, umbrales, casos, S, orden, idx) -> list[dict]:
    """Recorre varios valores del margen exigido al carril automatico.

    Existe como funcion y no repetida en dos sitios porque la primera version
    tenia el barrido duplicado —uno para imprimir y otro para el JSON—, y al
    introducir la v3 solo se actualizo uno. La tabla impresa quedo rotulada
    'politica v3' mostrando numeros de la v2. Dos copias de un calculo se
    desincronizan en el primer cambio; una funcion no puede.

    ADVERTENCIA METODOLOGICA: barre sobre el mismo conjunto con el que se mide.
    Sirve para ver la FORMA del compromiso, no para fijar el valor definitivo.
    """
    global MARGEN_AUTOMATICO
    guardado = MARGEN_AUTOMATICO
    n_auto = sum(1 for i in idx if casos[i]["carril"] == "automatico")
    salida = []
    try:
        for m in MARGENES_BARRIDO:
            MARGEN_AUTOMATICO = m
            ok = b2 = auto_ok = 0
            for fila, o, i in zip(S, orden, idx):
                carril, _ = decidir_v3(clf, umbrales, fila, o)
                real = casos[i]["carril"]
                if carril == real:
                    ok += 1
                    auto_ok += int(real == "automatico")
                elif SUPERVISION[real] - SUPERVISION[carril] == 2:
                    b2 += 1
            salida.append({"margen": m, "aciertos": ok, "brecha2": b2,
                           "auto_ok": auto_ok, "auto_total": n_auto,
                           "evaluados": len(idx)})
    finally:
        MARGEN_AUTOMATICO = guardado    # se restaura aunque algo falle
    return salida



# --------------------------------------------------------------------------------------

def main() -> None:
    clf = Clasificador()
    if not RUTA_UMBRALES.exists():
        raise SystemExit("Faltan los umbrales. Ejecuta antes:  python sonda_confianza.py")
    umbrales = json.loads(RUTA_UMBRALES.read_text(encoding="utf-8"))

    casos = cargar_prueba()
    # Pipeline real: la capa 0 decide primero y solo lo que pasa llega aqui.
    r0 = [capa0_reglas.evaluar(c["texto"], pedido=c.get("pedido"),
                               devoluciones_60d=c.get("devoluciones_60d", 0))
          for c in casos]
    idx = [i for i, r in enumerate(r0) if not r["escala"]]
    V = embed_lote([casos[i]["texto"] for i in idx])

    diagnosticar_numpy(V, clf.C)

    with np.errstate(all="ignore"):
        S = V @ clf.C.T
    orden = np.argsort(-S, axis=1)

    resultados = {"v1": {}, "v2": {}, "v3": {}}
    for fila, o, i in zip(S, orden, idx):
        i1, i2 = int(o[0]), int(o[1])
        conf = float(fila[i1])
        margen = conf - float(fila[i2])
        base = {"intencion": clf.intenciones[i1], "confianza": conf}
        c1, r1 = decidir_v1(clf, i1, i2, conf, margen)
        c2, r2 = decidir_v2(clf, umbrales, i1, i2, conf, margen)
        c3, r3 = decidir_v3(clf, umbrales, fila, o)
        resultados["v1"][i] = {**base, "carril": c1, "razon": r1}
        resultados["v2"][i] = {**base, "carril": c2, "razon": r2}
        resultados["v3"][i] = {**base, "carril": c3, "razon": r3}

    print("\n" + "=" * 74)
    print("COMPARACION v1 / v2 / v3   (solo los casos que pasan la capa 0)")
    print("=" * 74)
    # El conteo binario de 'inseguro' trata igual dos errores que no son iguales.
    # Mandar un caso de salud al carril automatico salta DOS niveles de
    # supervision; mandarlo a copiloto salta uno y todavia lo ve una persona. Se
    # reporta la brecha, que es lo que distingue un error de un incidente.
    print(f"  {'':4s} {'exactitud':>12s} {'brecha 1':>9s} {'brecha 2':>9s} "
          f"{'total ins.':>11s} {'a copiloto':>11s}")
    for version, preds in resultados.items():
        ok = cop = 0
        brecha = {1: 0, 2: 0}
        for i, p in preds.items():
            real = casos[i]["carril"]
            d = SUPERVISION[real] - SUPERVISION[p["carril"]]
            if p["carril"] == real:
                ok += 1
            elif d > 0:
                brecha[d] += 1
            if p["carril"] == "copiloto":
                cop += 1
        n0 = len(casos) - len(preds)   # los que resolvio la capa 0, todos correctos
        ins = brecha[1] + brecha[2]
        print(f"  {version:4s} {(ok + n0)}/{len(casos)} = {(ok + n0) / len(casos):5.1%} "
              f"{brecha[1]:>9d} {brecha[2]:>9d} {ins:>11d} {cop:>7d}/{len(preds)}")
    print("\n  brecha 2 = enviado al carril automatico algo que exigia un humano.")
    print("  Es el unico error que produce un incidente en vez de una demora.")

    print("\nCasos donde v2 y v3 difieren:")
    hay = False
    for i in idx:
        a, b = resultados["v2"][i], resultados["v3"][i]
        if a["carril"] == b["carril"]:
            continue
        hay = True
        real = casos[i]["carril"]
        marca = {True: "mejora ", False: "empeora"}[
            (b["carril"] == real) or (SUPERVISION[b["carril"]] >= SUPERVISION[real]
                                      and a["carril"] != real)]
        print(f"  [{marca}] real={real:16s} v2={a['carril']:11s} v3={b['carril']:11s} "
              f"{casos[i]['texto'][:44]}")
        if b["razon"]:
            print(f"            v3: {b['razon']}")
    if not hay:
        print("  ninguno")

    # Curva de costo del umbral del carril automatico. Se barre sobre el mismo
    # conjunto con el que se mide, asi que sirve para ver la FORMA del
    # compromiso y no para fijar el valor definitivo.
    print("\n" + "=" * 74)
    print("COSTO DEL MARGEN EXIGIDO AL CARRIL AUTOMATICO (politica v3)")
    print("=" * 74)
    barrido = barrer(clf, umbrales, casos, S, orden, idx)
    print(f"  {'margen':>7s} {'aciertos':>9s} {'brecha 2':>9s} {'autom. correctos':>18s}")
    for b in barrido:
        print(f"  {b['margen']:7.2f} {b['aciertos']:>6d}/{b['evaluados']} "
              f"{b['brecha2']:>9d} {b['auto_ok']:>13d}/{b['auto_total']}")

    print("\n" + "=" * 74)
    print("NUCLEO DURO PARAFRASEADO BAJO LA v3")
    print("=" * 74)
    for i in idx:
        if casos[i].get("grupo") != "nucleo_duro_parafraseado":
            continue
        b = resultados["v3"][i]
        print(f"  v3 -> {b['carril']:11s} ({b['intencion']:22s} conf={b['confianza']:.3f})"
              f"  {casos[i]['texto'][:40]}")

    # Volcado para el dashboard: las cifras viven en un solo sitio.
    import datetime as _dt

    def metricas(preds):
        ok = cop = 0
        br = {1: 0, 2: 0}
        for i, p in preds.items():
            real = casos[i]["carril"]
            d = SUPERVISION[real] - SUPERVISION[p["carril"]]
            if p["carril"] == real:
                ok += 1
            elif d > 0:
                br[d] += 1
            cop += int(p["carril"] == "copiloto")
        n0 = len(casos) - len(preds)
        return {"aciertos": ok + n0, "total": len(casos),
                "brecha1": br[1], "brecha2": br[2],
                "copiloto": cop, "evaluados": len(preds)}

    destino = AQUI / "modelo" / "resultados_politica.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps({
        "generado": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "umbrales": {"margen_automatico": MARGEN_AUTOMATICO,
                     "margen_general": MARGEN_GENERAL},
        "v1": metricas(resultados["v1"]),
        "v2": metricas(resultados["v2"]),
        "v3": metricas(resultados["v3"]),
        "barrido": barrido,
        "diferencias": [{"texto": casos[i]["texto"], "real": casos[i]["carril"],
                         "v2": resultados["v2"][i]["carril"],
                         "v3": resultados["v3"][i]["carril"],
                         "razon": resultados["v3"][i]["razon"]}
                        for i in idx
                        if resultados["v2"][i]["carril"] != resultados["v3"][i]["carril"]],
        "nucleo_duro": [{"texto": casos[i]["texto"],
                         "carril": resultados["v3"][i]["carril"],
                         "intencion": resultados["v3"][i]["intencion"],
                         "confianza": round(resultados["v3"][i]["confianza"], 3)}
                        for i in idx
                        if casos[i].get("grupo") == "nucleo_duro_parafraseado"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {destino.name}")

    print("\n  Ninguno puede llegar a humano_exclusivo: la capa 1 no tiene ese")
    print("  carril. Lo unico que la v2 puede lograr es que ninguno acabe en")
    print("  automatico, que es la diferencia entre un error y un incidente.")


if __name__ == "__main__":
    main()
