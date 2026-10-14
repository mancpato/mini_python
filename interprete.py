"""
Intérprete de MiniPy: recorre el AST y lo ejecuta.

Las variables se guardan en un diccionario {nombre: valor}.
Hay dos funciones, una para cada clase de nodo:
  ejecutar() para sentencias (no devuelven nada)
  evaluar()  para expresiones y condiciones (devuelven un valor)

Uso: python interprete.py programa.py
"""

import sys
from lexico import analizar, ErrorLexico
from sintactico import (Parser, ErrorSintactico, Asignacion, Imprimir, Si, Para,
                        BinOp, Condicion, Negativo, Num, Var)

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

        else:
            # Si se agrega un nodo al parser y se olvida aquí, mejor fallar
            # que ignorar la sentencia en silencio
            raise ErrorEjecucion(f"sentencia desconocida: {type(s).__name__}")


def evaluar(e, variables):
    if isinstance(e, Num):
        return e.valor

    if isinstance(e, Var):
        if e.nombre not in variables:
            raise ErrorEjecucion(f"la variable '{e.nombre}' no tiene valor")
        return variables[e.nombre]

    if isinstance(e, Negativo):
        return -evaluar(e.valor, variables)

    if isinstance(e, (BinOp, Condicion)):   # misma forma: op, izq, der
        a = evaluar(e.izq, variables)
        b = evaluar(e.der, variables)
        if e.op in ("//", "%") and b == 0:
            raise ErrorEjecucion("división entre cero")
        return OPERACIONES[e.op](a, b)

    raise ErrorEjecucion(f"expresión desconocida: {type(e).__name__}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python interprete.py programa.py")

    # Desde Python 3.11, convertir a texto un entero de más de 4300 dígitos
    # lanza ValueError. Los enteros del lenguaje no tienen límite, así que se
    # quita también el de impresión. (Otro ejemplo de semántica heredada.)
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)

    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            fuente = f.read()
        arbol = Parser(analizar(fuente)).programa()
        ejecutar(arbol.cuerpo, {})
    except FileNotFoundError:
        sys.exit(f"No se encontró el archivo {sys.argv[1]}")
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
    except ErrorSintactico as e:
        sys.exit(f"Error sintáctico: {e}")
    except ErrorEjecucion as e:
        sys.exit(f"Error de ejecución: {e}")
    except RecursionError:
        # El parser y el intérprete son recursivos y usan la pila de Python
        sys.exit("Error: el programa está demasiado anidado")
