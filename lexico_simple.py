"""
Esqueleto del analizador léxico de MiniPy, sin protecciones. Solo detecta
el error que es parte del algoritmo de la sangría: regresar a un nivel que
no está en la pila.

Uso: python lexico_simple.py programa.py
"""
import sys

RESERVADAS = {"def", "main", "if", "else", "for", "in", "range", "print"}
DOBLES = {"//", "==", "!=", "<=", ">="}


def analizar(texto):
    tokens = []                # cada token es una pareja (tipo, valor)
    pila = [0]                 # niveles de sangría abiertos

    for linea in texto.split("\n"):
        linea = linea.split("#")[0]            # quitar comentario
        if linea.strip() == "":
            continue                           # las líneas vacías no cuentan

        # 1. Sangría: compararla con la pila
        sangria = len(linea) - len(linea.lstrip(" "))
        if sangria > pila[-1]:
            pila.append(sangria)
            tokens.append(("INDENT", ""))
        while sangria < pila[-1]:
            pila.pop()
            tokens.append(("DEDENT", ""))
        if sangria != pila[-1]:                # regresó a un nivel que no existe
            raise SyntaxError("la sangría no coincide con ningún nivel anterior")

        # 2. Resto de la línea: reconocer lexemas
        i = sangria
        while i < len(linea):
            c = linea[i]
            if c == " ":
                i += 1
            elif c.isdigit():                  # número
                j = i
                while j < len(linea) and linea[j].isdigit():
                    j += 1
                tokens.append(("NUM", linea[i:j]))
                i = j
            elif c.isalpha() or c == "_":      # identificador o reservada
                j = i
                while j < len(linea) and (linea[j].isalnum() or linea[j] == "_"):
                    j += 1
                lexema = linea[i:j]
                tipo = lexema.upper() if lexema in RESERVADAS else "ID"
                tokens.append((tipo, lexema))
                i = j
            elif linea[i:i + 2] in DOBLES:     # operador de dos caracteres
                tokens.append((linea[i:i + 2], linea[i:i + 2]))
                i += 2
            else:                              # operador de un carácter
                tokens.append((c, c))
                i += 1

        tokens.append(("NEWLINE", ""))

    # 3. Fin del archivo: cerrar los bloques abiertos
    while pila[-1] > 0:
        pila.pop()
        tokens.append(("DEDENT", ""))
    tokens.append(("EOF", ""))
    return tokens


if __name__ == "__main__":
    # utf-8-sig acepta el BOM que agregan algunos editores de Windows
    for token in analizar(open(sys.argv[1], encoding="utf-8-sig").read()):
        print(token)
