"""
Intérprete de MiniPy: recorre el AST y lo ejecuta.

Las variables se guardan en un diccionario {nombre: valor}.
Hay dos funciones, una por cada tipo de nodo:
  ejecutar() para sentencias (no devuelven nada)
  evaluar()  para expresiones y condiciones (devuelven un valor)

Uso: python interprete.py programa.py
"""

import sys
from lexico import analizar, ErrorLexico
from sintactico import (Parser, ErrorSintactico, Asignacion, Imprimir, Si, Para,
                        Negativo, Num, Var)

OPERACIONES = {
    "+":  lambda a, b: a + b,
    "-":  lambda a, b: a - b,
    "*":  lambda a, b: a * b,
    "//": lambda a, b: a // b,
    "%":  lambda a, b: a % b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


class ErrorEjecucion(Exception):
    pass


def ejecutar(sentencias, variables):
    for s in sentencias:
        if isinstance(s, Asignacion):
            variables[s.nombre] = evaluar(s.valor, variables)

        elif isinstance(s, Imprimir):
            print(evaluar(s.valor, variables))

        elif isinstance(s, Si):
            if evaluar(s.condicion, variables):
                ejecutar(s.entonces, variables)
            else:
                ejecutar(s.sino, variables)

        elif isinstance(s, Para):
            inicio = evaluar(s.inicio, variables)   # los límites se evalúan
            fin = evaluar(s.fin, variables)         # una sola vez, como en Python
            for i in range(inicio, fin):
                variables[s.variable] = i
                ejecutar(s.cuerpo, variables)


def evaluar(e, variables):
    if isinstance(e, Num):
        return e.valor

    if isinstance(e, Var):
        if e.nombre not in variables:
            raise ErrorEjecucion(f"la variable '{e.nombre}' no tiene valor")
        return variables[e.nombre]

    if isinstance(e, Negativo):
        return -evaluar(e.valor, variables)

    # BinOp y Condicion tienen la misma forma: op, izq, der
    a = evaluar(e.izq, variables)
    b = evaluar(e.der, variables)
    if e.op in ("//", "%") and b == 0:
        raise ErrorEjecucion("división entre cero")
    return OPERACIONES[e.op](a, b)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python interprete.py programa.py")
    with open(sys.argv[1], encoding="utf-8") as f:
        fuente = f.read()
    try:
        arbol = Parser(analizar(fuente)).programa()
        ejecutar(arbol.cuerpo, {})
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
    except ErrorSintactico as e:
        sys.exit(f"Error sintáctico: {e}")
    except ErrorEjecucion as e:
        sys.exit(f"Error de ejecución: {e}")
