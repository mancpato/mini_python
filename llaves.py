"""
Traduce un programa de MiniPy a una versión con llaves.

Usa solo el analizador léxico: cada INDENT se escribe como "{" y cada
DEDENT como "}". El resultado muestra que, después del léxico, la sangría
ya no hace falta: la estructura del programa viaja en esos dos tokens,
como en un lenguaje con llaves.

Como no usa el analizador sintáctico, también traduce programas con
errores sintácticos. Por ejemplo, una línea con sangría de más aparece
como una "{" en un lugar donde la gramática no la permite.

Uso: python llaves.py [--plano | --una-linea] programa.py

  (sin opción)   llaves con sangría según la profundidad, como en C
  --plano        llaves sin sangría: al parser ya no le importan los espacios
  --una-linea    todo en una línea, con cada NEWLINE escrito como ";":
                 la secuencia de tokens tal como la recibe el parser
"""

import sys
from lexico import analizar, leer_o_salir, ErrorLexico

SANGRIA = "    "
MODOS = {"--plano": "plano", "--una-linea": "una-linea"}


def texto_de_linea(tokens):
    """Reconstruye una línea a partir de sus tokens. Las columnas guardadas
    en cada token permiten conservar los espacios originales entre ellos."""
    partes = []
    fin_anterior = None            # columna donde terminó el token anterior
    for t in tokens:
        if fin_anterior is not None:
            partes.append(" " * (t.columna - fin_anterior))
        partes.append(t.valor)
        fin_anterior = t.columna + len(t.valor)
    return "".join(partes)


def a_llaves(tokens, modo="sangria"):
    """Devuelve el programa como texto con llaves en lugar de sangría."""
    prefijo = SANGRIA if modo == "sangria" else ""
    fin = ";" if modo == "una-linea" else ""
    renglones = []
    actual = []                    # tokens de la línea que se está armando
    nivel = 0                      # llaves abiertas en este momento

    for t in tokens:
        if t.tipo == "INDENT":
            renglones.append(prefijo * nivel + "{")
            nivel += 1
        elif t.tipo == "DEDENT":
            nivel -= 1
            renglones.append(prefijo * nivel + "}")
        elif t.tipo == "NEWLINE":
            renglones.append(prefijo * nivel + texto_de_linea(actual) + fin)
            actual = []
        elif t.tipo != "EOF":
            actual.append(t)

    separador = " " if modo == "una-linea" else "\n"
    return separador.join(renglones)


if __name__ == "__main__":
    args = sys.argv[1:]
    modo = "sangria"
    if len(args) == 2 and args[0] in MODOS:
        modo = MODOS[args.pop(0)]
    if len(args) != 1:
        sys.exit("Uso: python llaves.py [--plano | --una-linea] programa.py")

    try:
        print(a_llaves(analizar(leer_o_salir(args[0])), modo))
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
