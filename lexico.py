"""
Analizador léxico para MiniPy (subconjunto mínimo de Python).

Entrada: el texto del programa.
Salida:  una lista de tokens, terminada en EOF.

La definición de los tokens (ID, NUM, OPREL, letra, digito, las palabras
reservadas y los comentarios) está en gramatica.ebnf, la referencia oficial
del lenguaje; aquí no se repite. Solo ASCII: un identificador no admite
letras acentuadas ni la ñ, y NUM no admite ceros a la izquierda.

La sangría no se pasa como espacios al analizador sintáctico: se convierte
en tokens INDENT y DEDENT usando una pila de niveles. Así la gramática
puede tratarlos como si fueran llaves de apertura y cierre.

Uso: python lexico.py programa.py
"""

import sys
from dataclasses import dataclass

RESERVADAS = {"def", "main", "if", "else", "for", "in", "range", "print"}
OPERADORES_DOBLES = {"//", "==", "!=", "<=", ">="}
OPERADORES_SIMPLES = set("+-*%<>=():,")

# El alfabeto es solo ASCII, como dice gramatica.ebnf. Se escriben los
# caracteres uno por uno y no se usan isalpha() ni isalnum(), que aceptan
# todo Unicode: letras acentuadas, la ñ, la ligadura ﬁ (U+FB01) y dígitos
# como ² o ₁.
LETRAS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITOS = "0123456789"
ALFANUMERICOS = LETRAS + DIGITOS + "_"

# Caracteres que se ven como otros válidos; suelen llegar al copiar
# código desde una presentación, un PDF o una página web.
ENGANOSOS = {
    "\u00a0": "espacio no separable (¿copiado de una presentación o página web?)",
    "\u200b": "espacio invisible de ancho cero",
    "\u2028": "separador de línea Unicode, invisible (¿copiado de una página web?)",
    "\u2013": "semirraya '–'; use el signo menos '-'",
    "\u2014": "raya '—'; use el signo menos '-'",
    "\u2212": "signo menos tipográfico; use '-'",
    "\u201c": "comilla tipográfica; además, el lenguaje no tiene cadenas",
    "\u201d": "comilla tipográfica; además, el lenguaje no tiene cadenas",
    "\u2018": "comilla tipográfica; además, el lenguaje no tiene cadenas",
    "\u2019": "comilla tipográfica; además, el lenguaje no tiene cadenas",
}


@dataclass
class Token:
    tipo: str      # NUM, ID, DEF, IF, ..., "+", "==", NEWLINE, INDENT, DEDENT, EOF
    valor: str     # el lexema tal como aparece en el texto
    linea: int
    columna: int

    def __str__(self):
        return f"{self.linea:>3}:{self.columna:<3} {self.tipo:<8} {self.valor!r}"


class ErrorLexico(Exception):
    pass


def leer(ruta):
    """Lee el programa como UTF-8, aceptando el BOM que agregan algunos
    editores de Windows. Un byte que no es UTF-8 no pertenece al alfabeto,
    así que se reporta como error léxico, con la línea donde aparece."""
    with open(ruta, "rb") as f:
        datos = f.read()
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        linea = datos[:e.start].count(b"\n") + 1
        raise ErrorLexico(f"línea {linea}: el archivo no está en UTF-8 "
                          "(guárdelo como UTF-8 desde el editor)")


def analizar(texto):
    tokens = []
    pila = [0]  # niveles de sangría abiertos; el 0 nunca se saca

    # Se separa solo en "\n". splitlines() también corta en caracteres como
    # el separador de línea Unicode (U+2028), y aceptaría en silencio un
    # programa que Python rechaza. open() ya convierte "\r\n" en "\n", pero
    # analizar() puede recibir texto de otra fuente.
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    lineas = texto.split("\n")
    if lineas[-1] == "":        # el "\n" final no abre una línea nueva
        lineas.pop()

    for n, linea in enumerate(lineas, start=1):
        linea = linea.split("#", 1)[0]          # quitar comentario
        # Líneas vacías no cuentan. Solo se quitan espacios y tabuladores:
        # strip() sin argumentos también quitaría espacios Unicode (U+00A0,
        # U+2028) y una línea con solo esos caracteres pasaría en silencio.
        if linea.strip(" \t") == "":
            continue

        # --- 1. Sangría: contar espacios al inicio ---
        sangria = 0
        while linea[sangria] == " ":
            sangria += 1
        if linea[sangria] == "\t":
            raise ErrorLexico(f"línea {n}: use espacios, no tabuladores")

        if sangria > pila[-1]:
            pila.append(sangria)
            tokens.append(Token("INDENT", "", n, 1))
        else:
            while sangria < pila[-1]:
                pila.pop()
                tokens.append(Token("DEDENT", "", n, 1))
            if sangria != pila[-1]:
                raise ErrorLexico(
                    f"línea {n}: la sangría no coincide con ningún nivel anterior")

        # --- 2. Resto de la línea: reconocer lexemas ---
        i = sangria
        while i < len(linea):
            c = linea[i]
            col = i + 1

            if c in " \t":                      # espacios y tabuladores entre tokens
                i += 1

            elif c in DIGITOS:
                j = i
                while j < len(linea) and linea[j] in DIGITOS:
                    j += 1
                lexema = linea[i:j]
                # NUM admite "0", "00", "000"..., pero no un cero a la
                # izquierda seguido de otra cifra: 007 no es un número
                if lexema[0] == "0" and lexema.strip("0") != "":
                    raise ErrorLexico(
                        f"línea {n}, columna {col}: un número no puede "
                        f"empezar con cero: {lexema!r}")
                tokens.append(Token("NUM", lexema, n, col))
                i = j

            elif c in LETRAS or c == "_":
                j = i
                while j < len(linea) and linea[j] in ALFANUMERICOS:
                    j += 1
                lexema = linea[i:j]
                tipo = lexema.upper() if lexema in RESERVADAS else "ID"
                tokens.append(Token(tipo, lexema, n, col))
                i = j

            elif linea[i:i + 2] in OPERADORES_DOBLES:   # probar primero los de 2
                tokens.append(Token(linea[i:i + 2], linea[i:i + 2], n, col))
                i += 2

            elif c in OPERADORES_SIMPLES:
                tokens.append(Token(c, c, n, col))
                i += 1

            elif c in ENGANOSOS:
                # Va antes de la rama siguiente: un carácter engañoso puede
                # ser alfanumérico (por ejemplo la 'а' cirílica, U+0430) y su
                # mensaje es más preciso que el de aquí abajo.
                raise ErrorLexico(f"línea {n}, columna {col}: {ENGANOSOS[c]}")

            elif c.isalnum():
                # Alfanumérico para Unicode, pero no para el alfabeto del
                # lenguaje: á, ñ, ², ₁, la ligadura ﬁ...
                raise ErrorLexico(
                    f"línea {n}, columna {col}: carácter inesperado {c!r}: "
                    "los identificadores solo admiten letras sin acento, "
                    "dígitos y '_'")

            else:
                raise ErrorLexico(f"línea {n}, columna {col}: carácter inesperado {c!r}")

        tokens.append(Token("NEWLINE", "\n", n, len(linea) + 1))

    # --- 3. Fin de archivo: cerrar los bloques que sigan abiertos ---
    ultima = len(lineas) + 1
    while pila[-1] > 0:
        pila.pop()
        tokens.append(Token("DEDENT", "", ultima, 1))
    tokens.append(Token("EOF", "", ultima, 1))
    return tokens


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python lexico.py programa.py")
    try:
        for tok in analizar(leer(sys.argv[1])):
            print(tok)
    except FileNotFoundError:
        sys.exit(f"No se encontró el archivo {sys.argv[1]}")
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
