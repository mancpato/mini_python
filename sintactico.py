"""
Analizador sintáctico descendente recursivo para MiniPy.

Recibe la lista de tokens del analizador léxico y construye un árbol de
sintaxis abstracta (AST). Hay una función por cada regla de la gramática:

  programa   ::= "def" "main" "(" ")" ":" bloque [ "main" "(" ")" NEWLINE ]
  bloque     ::= NEWLINE INDENT sentencia { sentencia } DEDENT
  sentencia  ::= asignacion | si | para | imprimir
  asignacion ::= ID "=" expr NEWLINE
  imprimir   ::= "print" "(" expr ")" NEWLINE
  si         ::= "if" condicion ":" bloque [ "else" ":" bloque ]
  para       ::= "for" ID "in" "range" "(" expr [ "," expr ] ")" ":" bloque
  condicion  ::= expr OPREL expr
  expr       ::= termino { ( "+" | "-" ) termino }
  termino    ::= factor { ( "*" | "//" | "%" ) factor }
  factor     ::= NUM | ID | "(" expr ")" | "-" factor

Uso: python sintactico.py programa.py
"""

import sys
from dataclasses import dataclass, fields
from lexico import analizar, ErrorLexico

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
        for t in ("DEF", "MAIN", "(", ")", ":"):
            self.consumir(t)
        cuerpo = self.bloque()
        if self.ver("MAIN"):                  # llamada final opcional: main()
            for t in ("MAIN", "(", ")", "NEWLINE"):
                self.consumir(t)
        self.consumir("EOF")
        return Programa(cuerpo)

    def bloque(self):
        self.consumir("NEWLINE")
        self.consumir("INDENT")
        sentencias = [self.sentencia()]
        while not self.ver("DEDENT"):
            sentencias.append(self.sentencia())
        self.consumir("DEDENT")
        return sentencias

    def sentencia(self):
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
        nombre = self.consumir("ID").valor
        self.consumir("=")
        valor = self.expr()
        self.consumir("NEWLINE")
        return Asignacion(nombre, valor)

    def imprimir(self):
        self.consumir("PRINT")
        self.consumir("(")
        valor = self.expr()
        self.consumir(")")
        self.consumir("NEWLINE")
        return Imprimir(valor)

    def si(self):
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
        izq = self.expr()
        if not self.ver(*OPREL):
            self.error("un operador relacional")
        op = self.actual().tipo
        self.pos += 1
        der = self.expr()
        return Condicion(op, izq, der)

    def expr(self):
        nodo = self.termino()
        while self.ver("+", "-"):             # el ciclo da asociatividad izquierda
            op = self.actual().tipo
            self.pos += 1
            nodo = BinOp(op, nodo, self.termino())
        return nodo

    def termino(self):
        nodo = self.factor()
        while self.ver("*", "//", "%"):
            op = self.actual().tipo
            self.pos += 1
            nodo = BinOp(op, nodo, self.factor())
        return nodo

    def factor(self):
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
    with open(sys.argv[1], encoding="utf-8") as f:
        fuente = f.read()
    try:
        arbol = Parser(analizar(fuente)).programa()
        mostrar(arbol)
    except ErrorLexico as e:
        sys.exit(f"Error léxico: {e}")
    except ErrorSintactico as e:
        sys.exit(f"Error sintáctico: {e}")
