"""
Escribe los tokens de un programa de MiniPy en un archivo intermedio .tok.

Usa solo el analizador léxico. De programa.py genera programa.tok, con un
renglón por cada línea del programa que produjo tokens, para compararlo
lado a lado con el original:

  # Tokens de ejemplo.py, generado por lex2tok.py
    1  DEF MAIN ( ) : NEWLINE
    2  INDENT ID:suma = NUM:0 NEWLINE
    ...
    8  DEDENT DEDENT PRINT ( ID:suma ) NEWLINE

Las palabras reservadas aparecen con su tipo, los operadores como ellos
mismos, y los identificadores y números con su valor. Las líneas vacías y
los comentarios no producen tokens, así que no aparecen.

Si hay un error léxico, el .tok se sobrescribe con el mensaje de error,
para que nunca quede un .tok viejo que no corresponda al programa actual.

El archivo se escribe siempre en UTF-8. (Redirigir la salida de lexico.py
con ">" no sirve igual: en Windows PowerShell 5 produce UTF-16.)

Uso: python lex2tok.py programa.py
"""

import os
import sys
from lexico import analizar, leer_o_salir, ErrorLexico


def nombre_token(t):
    """ID y NUM llevan su valor; los demás basta con el tipo (en los
    operadores, el tipo es el operador mismo)."""
    if t.tipo in ("ID", "NUM"):
        return f"{t.tipo}:{t.valor}"
    return t.tipo


def a_compacto(tokens):
    """Agrupa los tokens por línea del programa original."""
    renglones = []
    linea_actual = None
    for t in tokens:
        if t.linea != linea_actual:
            renglones.append([t.linea, []])
            linea_actual = t.linea
        renglones[-1][1].append(nombre_token(t))
    return "\n".join(f"{n:>3}  {' '.join(nombres)}" for n, nombres in renglones)


def ruta_tok(ruta_programa):
    base, extension = os.path.splitext(ruta_programa)
    return (base if extension == ".py" else ruta_programa) + ".tok"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python lex2tok.py programa.py")
    entrada = sys.argv[1]
    salida = ruta_tok(entrada)
    encabezado = f"# Tokens de {os.path.basename(entrada)}, generado por lex2tok.py\n"

    try:
        contenido = encabezado + a_compacto(analizar(leer_o_salir(entrada))) + "\n"
        error = None
    except ErrorLexico as e:
        error = f"Error léxico: {e}"
        contenido = encabezado + f"# {error}\n"

    try:
        with open(salida, "w", encoding="utf-8") as f:
            f.write(contenido)
    except OSError:
        sys.exit(f"No se pudo escribir {salida}")

    if error:
        sys.exit(f"{error}\n(se escribió el error en {salida})")
    print(f"Tokens escritos en {salida}")
