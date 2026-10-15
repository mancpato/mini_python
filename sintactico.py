"""
Analizador sintáctico descendente recursivo para MiniPy.

Recibe la lista de tokens del analizador léxico y construye un árbol de
sintaxis abstracta (AST).

La gramática no se repite aquí: está en gramatica.ebnf, la referencia
oficial del lenguaje. Hay un método de Parser por cada regla sintáctica,
con su mismo nombre y con la regla como docstring; pruebas.py comprueba
que esos docstrings coincidan con el archivo.

Uso: python sintactico.py programa.py
"""

import io
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, fields
from lexico import analizar, leer, ErrorLexico

OPREL = {"==", "!=", "<", "<=", ">", ">="}


# ------------------------------------------------------------------
# Nodos del AST
# ------------------------------------------------------------------
@dataclass
class Programa:
    cuerpo: list

@dataclass
class Asignacion:
    nombre: str
    valor: object

@dataclass
class Imprimir:
    valor: object

@dataclass
class Si:
    condicion: object
    entonces: list
    sino: list          # lista vacía si no hay else

@dataclass
class Para:
    variable: str
    inicio: object
    fin: object
    cuerpo: list

@dataclass
class Condicion:
    op: str
    izq: object
    der: object

@dataclass
class BinOp:
    op: str
    izq: object
    der: object

@dataclass
class Negativo:
    valor: object

@dataclass
class Num:
    valor: int

@dataclass
class Var:
    nombre: str


class ErrorSintactico(Exception):
    pass


# ------------------------------------------------------------------
# Analizador
# ------------------------------------------------------------------
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # --- utilidades ---
    def actual(self):
        return self.tokens[self.pos]

    def ver(self, *tipos):
        """¿El token actual es de alguno de estos tipos? (no consume)"""
        return self.actual().tipo in tipos

    def error(self, esperado):
        t = self.actual()
        encontrado = t.tipo if t.valor in ("", "\n") else repr(t.valor)
        raise ErrorSintactico(
            f"línea {t.linea}, columna {t.columna}: "
            f"se esperaba {esperado}, se encontró {encontrado}")

    def consumir(self, tipo):
        """Exige un token del tipo dado, lo consume y lo devuelve."""
        if not self.ver(tipo):
            self.error(tipo)
        tok = self.actual()
        self.pos += 1
        return tok

    # --- una función por regla ---
    def programa(self):
        """programa ::= "def" "main" "(" ")" ":" bloque "main" "(" ")" NEWLINE"""
        for t in ("DEF", "MAIN", "(", ")", ":"):
            self.consumir(t)
        cuerpo = self.bloque()
        for t in ("MAIN", "(", ")", "NEWLINE"):   # la llamada final es obligatoria
            self.consumir(t)
        self.consumir("EOF")
        return Programa(cuerpo)

    def bloque(self):
        """bloque ::= NEWLINE INDENT sentencia { sentencia } DEDENT"""
        self.consumir("NEWLINE")
        self.consumir("INDENT")
        sentencias = [self.sentencia()]
        while not self.ver("DEDENT"):
            sentencias.append(self.sentencia())
        self.consumir("DEDENT")
        return sentencias

    def sentencia(self):
        """sentencia ::= asignacion | si | para | imprimir"""
        # Cada alternativa empieza con un token distinto: basta mirar uno (LL(1))
        if self.ver("ID"):
            return self.asignacion()
        if self.ver("IF"):
            return self.si()
        if self.ver("FOR"):
            return self.para()
        if self.ver("PRINT"):
            return self.imprimir()
        self.error("una sentencia")

    def asignacion(self):
        """asignacion ::= ID "=" expr NEWLINE"""
        nombre = self.consumir("ID").valor
        self.consumir("=")
        valor = self.expr()
        self.consumir("NEWLINE")
        return Asignacion(nombre, valor)

    def imprimir(self):
        """imprimir ::= "print" "(" expr ")" NEWLINE"""
        self.consumir("PRINT")
        self.consumir("(")
        valor = self.expr()
        self.consumir(")")
        self.consumir("NEWLINE")
        return Imprimir(valor)

    def si(self):
        """si ::= "if" condicion ":" bloque [ "else" ":" bloque ]"""
        self.consumir("IF")
        cond = self.condicion()
        self.consumir(":")
        entonces = self.bloque()
        sino = []
        if self.ver("ELSE"):
            self.consumir("ELSE")
            self.consumir(":")
            sino = self.bloque()
        return Si(cond, entonces, sino)

    def para(self):
        """para ::= "for" ID "in" "range" "(" expr [ "," expr ] ")" ":" bloque"""
        self.consumir("FOR")
        var = self.consumir("ID").valor
        self.consumir("IN")
        self.consumir("RANGE")
        self.consumir("(")
        primero = self.expr()
        if self.ver(","):                     # range(a, b)
            self.consumir(",")
            inicio, fin = primero, self.expr()
        else:                                 # range(b) equivale a range(0, b)
            inicio, fin = Num(0), primero
        self.consumir(")")
        self.consumir(":")
        cuerpo = self.bloque()
        return Para(var, inicio, fin, cuerpo)

    def condicion(self):
        """condicion ::= expr OPREL expr"""
        izq = self.expr()
        if not self.ver(*OPREL):
            self.error("un operador relacional")
        op = self.actual().tipo
        self.pos += 1
        der = self.expr()
        return Condicion(op, izq, der)

    def expr(self):
        """expr ::= termino { ( "+" | "-" ) termino }"""
        nodo = self.termino()
        while self.ver("+", "-"):             # el ciclo da asociatividad izquierda
            op = self.actual().tipo
            self.pos += 1
            nodo = BinOp(op, nodo, self.termino())
        return nodo

    def termino(self):
        """termino ::= factor { ( "*" | "//" | "%" ) factor }"""
        nodo = self.factor()
        while self.ver("*", "//", "%"):
            op = self.actual().tipo
            self.pos += 1
            nodo = BinOp(op, nodo, self.factor())
        return nodo

    def factor(self):
        """factor ::= NUM | ID | "(" expr ")" | "-" factor"""
        if self.ver("NUM"):
            return Num(int(self.consumir("NUM").valor))
        if self.ver("ID"):
            return Var(self.consumir("ID").valor)
        if self.ver("("):
            self.consumir("(")
            nodo = self.expr()
            self.consumir(")")
            return nodo
        if self.ver("-"):
            self.consumir("-")
            return Negativo(self.factor())
        self.error("un número, una variable, '(' o '-'")


# ------------------------------------------------------------------
# Mostrar el árbol
# ------------------------------------------------------------------
def mostrar(nodo, nivel=0):
    pre = "  " * nivel
    if isinstance(nodo, list):
        for n in nodo:
            mostrar(n, nivel)
        return
    hojas = [(f.name, getattr(nodo, f.name)) for f in fields(nodo)
             if isinstance(getattr(nodo, f.name), (str, int))]
    hijos = [(f.name, getattr(nodo, f.name)) for f in fields(nodo)
             if not isinstance(getattr(nodo, f.name), (str, int))]
    texto = ", ".join(f"{k}={v!r}" for k, v in hojas)
    print(f"{pre}{type(nodo).__name__}" + (f" ({texto})" if texto else ""))
    for nombre, valor in hijos:
        if valor == []:
            continue
        print(f"{pre}  {nombre}:")
        mostrar(valor, nivel + 2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python sintactico.py programa.py")

    # Desde 2022 (Python 3.11, y las correcciones de seguridad 3.10.7, 3.9.14,
    # 3.8.14 y 3.7.14), convertir entre texto y entero con más de 4300 dígitos
    # lanza ValueError. Aquí afecta a int() en factor() y a la impresión del
    # árbol. Los enteros del lenguaje no tienen límite, así que se quita.
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)

    try:
        arbol = Parser(analizar(leer(sys.argv[1]))).programa()
        # El árbol se arma en memoria y se imprime al final: si la recursión
        # se agota a la mitad, sale solo el mensaje de error.
        texto = io.StringIO()
        with redirect_stdout(texto):
            mostrar(arbol)
        print(texto.getvalue(), end="")
    except FileNotFoundError:
        sys.exit(f"No se encontró el archivo {sys.argv[1]}")
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
    except ErrorSintactico as e:
        sys.exit(f"Error sintáctico: {e}")
    except RecursionError:
        # El parser y mostrar() son recursivos y usan la pila de Python, que es
        # finita. La profundidad del árbol no es la del texto: una suma de 1000
        # términos sin paréntesis da un árbol de profundidad 999, por la
        # asociatividad izquierda.
        sys.exit("Error: el árbol del programa es demasiado profundo "
                 "(mucho anidamiento o una expresión muy larga)")
