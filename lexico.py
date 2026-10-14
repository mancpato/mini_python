"""
Analizador léxico para MiniPy (subconjunto mínimo de Python).

Entrada: el texto del programa.
Salida:  una lista de tokens, terminada en EOF.

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
DIGITOS = "0123456789"


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


def analizar(texto):
    tokens = []
    pila = [0]  # niveles de sangría abiertos; el 0 nunca se saca

    for n, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.split("#", 1)[0]          # quitar comentario
        if linea.strip() == "":
            continue                             # líneas vacías no cuentan

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

            if c == " ":
                i += 1

            elif c in DIGITOS:
                j = i
                while j < len(linea) and linea[j] in DIGITOS:
                    j += 1
                tokens.append(Token("NUM", linea[i:j], n, col))
                i = j

            elif c.isalpha() or c == "_":
                j = i
                while j < len(linea) and (linea[j].isalnum() or linea[j] == "_"):
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

            else:
                raise ErrorLexico(f"línea {n}, columna {col}: carácter inesperado {c!r}")

        tokens.append(Token("NEWLINE", "\n", n, len(linea) + 1))

    # --- 3. Fin de archivo: cerrar los bloques que sigan abiertos ---
    ultima = len(texto.splitlines()) + 1
    while pila[-1] > 0:
        pila.pop()
        tokens.append(Token("DEDENT", "", ultima, 1))
    tokens.append(Token("EOF", "", ultima, 1))
    return tokens


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python lexico.py programa.py")
    with open(sys.argv[1], encoding="utf-8") as f:
        fuente = f.read()
    try:
        for tok in analizar(fuente):
            print(tok)
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
