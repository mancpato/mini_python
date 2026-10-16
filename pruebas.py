"""
Pruebas de regresión de MiniPy.

Corre cada caso de CASOS con interprete.py, cada caso de CASOS_ARBOL con
sintactico.py y cada caso de CASOS_TOK con lex2tok.py, y compara la salida
(o el mensaje de error, o el archivo .tok) con la esperada.
Los casos incluyen los ejemplos y la tabla «Qué etapa detecta cada error»
de README.md, más algunos que en versiones anteriores producían un
traceback de Python.

Hay además dos verificaciones fijas. Una no ejecuta ningún script: lee
gramatica.ebnf y comprueba que el docstring de cada método de regla de
Parser sea la regla del mismo nombre. Así ningún archivo repite la
gramática sin verificación. La otra le pasa a cada script una carpeta en
lugar de un programa, y espera un mensaje, no un traceback.

En los programas válidos de CASOS también se corre Python, para confirmar
que dan el mismo resultado.

Toda salida con un traceback de Python cuenta como falla, aunque el caso no
lo haya previsto: la especificación (README.md, «Semántica de MiniPy») exige
que toda excepción se traduzca a un error del lenguaje.

Cada caso tiene un límite de tiempo: con while, un ciclo infinito cuenta
como falla en lugar de dejar colgadas las pruebas.

Uso: python pruebas.py      (cada equipo puede agregar sus casos al final
                             de la lista que corresponda)
"""

import os
import re
import subprocess
import sys
import tempfile

from sintactico import Parser

# Al redirigir la salida (python pruebas.py > salida.txt), Windows la escribe
# en su codificación local, que no tiene todos los caracteres (por ejemplo,
# la ligadura 'fi' del caso que la prueba): sin esto, reportar ese caso
# abortaría las pruebas con un UnicodeEncodeError. IDLE reemplaza sys.stdout
# por un objeto sin reconfigure(), que de todos modos acepta Unicode.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

AQUI = os.path.dirname(os.path.abspath(__file__))
TRACEBACK = "Traceback (most recent call last)"
LEXICO = os.path.join(AQUI, "lexico.py")
SINTACTICO = os.path.join(AQUI, "sintactico.py")
INTERPRETE = os.path.join(AQUI, "interprete.py")
LEX2TOK = os.path.join(AQUI, "lex2tok.py")
LLAVES = os.path.join(AQUI, "llaves.py")
GRAMATICA = os.path.join(AQUI, "gramatica.ebnf")

# Reglas sintácticas: cada una tiene un método de Parser con su nombre y con
# la regla de gramatica.ebnf como docstring.
REGLAS = ["programa", "bloque", "sentencia", "asignacion", "imprimir", "si",
          "para", "condicion", "expr", "termino", "factor"]
# Reglas léxicas: lexico.py no tiene una función por regla, así que no hay
# docstring que comparar. Se listan para notar si alguien agrega una regla
# a gramatica.ebnf y nadie la implementa.
REGLAS_LEXICAS = ["ID", "NUM", "OPREL", "letra", "digito", "digito_no_cero"]
LIMITE_SEGUNDOS = 10
# En Windows, un proceso hijo con la salida redirigida escribe en la
# codificación local; así escribe en UTF-8, que es como la lee correr()
ENTORNO = dict(os.environ, PYTHONIOENCODING="utf-8")

# Casos para interprete.py:
# (nombre, programa, salida esperada, ¿comparar también con Python?)
# El programa puede ser str o bytes (para probar codificaciones).
CASOS = [
    # --- Programas de ejemplo ---
    ("ejemplo", "def main():\n    suma = 0\n    for i in range(1, 11):\n"
     "        if i % 2 == 0:\n            suma = suma + i\n        else:\n"
     "            suma = suma - 1\n    print(suma)\n\nmain()\n", "25", True),
    ("primo", "def main():\n    n = 97\n    divisores = 0\n"
     "    for d in range(1, n + 1):\n        if n % d == 0:\n"
     "            divisores = divisores + 1\n    if divisores == 2:\n"
     "        print(1)\n    else:\n        print(0)\n\nmain()\n", "1", True),
    ("mcd", "def main():\n    a = 1071\n    b = 462\n    for k in range(0, b):\n"
     "        if b != 0:\n            r = a % b\n            a = b\n"
     "            b = r\n    print(a)\n\nmain()\n", "21", True),
    ("suma de dígitos", "def main():\n    n = 90817\n    suma = 0\n"
     "    for k in range(0, n + 1):\n        if n > 0:\n"
     "            suma = suma + n % 10\n            n = n // 10\n"
     "    print(suma)\n\nmain()\n", "25", True),
    ("factorial", "def main():\n    f = 1\n    for i in range(1, 31):\n"
     "        f = f * i\n    print(f)\n\nmain()\n",
     "265252859812191058636308480000000", True),

    # --- Cada construcción de la gramática, al menos una vez ---
    # range(b) es range(0, b): el parser agrega un Num(0) que no está en el texto
    ("range con un solo argumento", "def main():\n    s = 0\n    for i in range(4):\n"
     "        s = s + i\n    print(s)\n    print(i)\n\nmain()\n", "6\n3", True),
    # Cada operador suma una cifra distinta de r: 1 (==), 10 (!=), 100 (<),
    # 1000 (<=), 10000 (>) y 100000 (>=). Con a = 4, 5 y 6, cada operador se
    # prueba con un valor menor, uno igual y uno mayor que 5.
    ("los seis operadores relacionales", "def main():\n    for a in range(4, 7):\n"
     "        r = 0\n        if a == 5:\n            r = r + 1\n"
     "        if a != 5:\n            r = r + 10\n        if a < 5:\n"
     "            r = r + 100\n        if a <= 5:\n            r = r + 1000\n"
     "        if a > 5:\n            r = r + 10000\n        if a >= 5:\n"
     "            r = r + 100000\n        print(r)\n\nmain()\n",
     "1110\n101001\n110010", True),
    ("paréntesis y menos unario", "def main():\n    print((1 + 2) * 3)\n"
     "    print(2 * (10 - 4) // 4)\n    print(-(2 + 3))\n    print(2 - -3)\n\nmain()\n",
     "9\n3\n-5\n5", True),
    # La sangría decide de qué if es el else: con INDENT y DEDENT no hay else
    # colgante. Si el else fuera del if interno, imprimiría 2 en lugar de 4.
    ("else del if externo", "def main():\n    a = 1\n    b = 0\n    if a > 0:\n"
     "        if b > 0:\n            print(1)\n    else:\n        print(2)\n"
     "    if a < 0:\n        if b > 0:\n            print(3)\n    else:\n"
     "        print(4)\n\nmain()\n", "4", True),
    # Una línea con solo un comentario no abre ni cierra bloques, tenga la
    # sangría que tenga
    ("comentarios con cualquier sangría", "def main():\n    x = 1\n# en la columna 0\n"
     "            # con sangría de más\n    if x > 0:\n        # dentro del if\n"
     "        x = 2\n  # en un nivel que no existe\n    print(x)\n\nmain()\n",
     "2", True),
    # --- Semántica de MiniPy (README.md): casos que en C o Java darían otra cosa ---
    ("// y % redondean hacia menos infinito",
     "def main():\n    print(-7 // 2)\n    print(-7 % 2)\n    print(7 % -2)\n\nmain()\n",
     "-4\n1\n-1", True),
    # El cuerpo modifica la variable y el límite; no cambia las vueltas. Al
    # terminar, i conserva el último valor; un rango vacío no toca a j.
    ("for: límites evaluados una vez",
     "def main():\n    n = 3\n    j = 7\n    for i in range(0, n):\n"
     "        print(i)\n        i = 100\n        n = 0\n    print(i)\n"
     "    for j in range(5, 2):\n        print(0)\n    print(j)\n\nmain()\n",
     "0\n1\n2\n100\n7", True),
    # Se evalúa primero el operando izquierdo: el error es el de la variable
    ("orden de evaluación", "def main():\n    print(x + 1 // 0)\n\nmain()\n",
     "Error de ejecución: la variable 'x' no tiene valor", False),
    ("BOM al inicio", b"\xef\xbb\xbfdef main():\n    print(1)\n\nmain()\n", "1", True),
    # leer() abre en binario: los \r\n llegan al léxico, que debe convertirlos
    ("fines de línea de Windows (CRLF)", b"def main():\r\n    print(1)\r\n\r\nmain()\r\n",
     "1", True),

    # --- Errores léxicos ---
    ("división con /", "def main():\n    suma = 0\n    for i in range(1, 6):\n"
     "        suma = suma + i\n    promedio = suma / 5\n    print(promedio)\n\nmain()\n",
     "Error léxico: línea 5, columna 21: carácter inesperado '/'", False),
    ("sangría sin nivel", "def main():\n    x = 10\n    if x > 5:\n"
     "        x = x - 1\n      print(x)\n\nmain()\n",
     "Error léxico: línea 5: la sangría no coincide con ningún nivel anterior", False),
    # NUM excluye el cero a la izquierda seguido de otra cifra, pero no el
    # número formado solo por ceros, que Python también acepta
    ("ceros a la izquierda", "def main():\n    x = 007\n    print(x)\n\nmain()\n",
     "Error léxico: línea 2, columna 9: un número no puede empezar con cero: '007'",
     False),
    ("número de solo ceros", "def main():\n    x = 00\n    print(x)\n\nmain()\n",
     "0", True),
    ("archivo en UTF-16 (PowerShell 5)", "def main():\n    print(1)\n\nmain()\n".encode("utf-16"),
     "Error léxico: línea 1: el archivo no está en UTF-8 "
     "(guárdelo como UTF-8 desde el editor)", False),
    ("separador de línea U+2028", "def main():\n    x = 1\u2028    print(x)\n\nmain()\n",
     "Error léxico: línea 2, columna 10: separador de línea Unicode, invisible "
     "(¿copiado de una página web?)", False),
    ("raya en lugar de menos", "def main():\n    x = 5 \u2014 3\n\nmain()\n",
     "Error léxico: línea 2, columna 11: raya '—'; use el signo menos '-'", False),
    ("archivo en Latin-1", "def main():\n    # año\n    print(1)\n\nmain()\n".encode("latin-1"),
     "Error léxico: línea 2: el archivo no está en UTF-8 "
     "(guárdelo como UTF-8 desde el editor)", False),
    ("línea con solo espacios no separables",
     "def main():\n    x = 1\n\u00a0\u00a0\n    print(x)\n\nmain()\n",
     "Error léxico: línea 3, columna 1: espacio no separable "
     "(¿copiado de una presentación o página web?)", False),
    ("comillas simples tipográficas", "def main():\n    x = \u2018a\u2019\n\nmain()\n",
     "Error léxico: línea 2, columna 9: comilla tipográfica; además, "
     "el lenguaje no tiene cadenas", False),
    ("número con punto decimal", "def main():\n    x = 2.5\n    print(x)\n\nmain()\n",
     "Error léxico: línea 2, columna 10: carácter inesperado '.'", False),
    ("tabulador en la sangría", "def main():\n\tprint(1)\n\nmain()\n",
     "Error léxico: línea 2: use espacios, no tabuladores", False),
    ("tabulador antes de comentario", "def main():\n    x = 1\t# uno\n    print(x)\n\nmain()\n",
     "1", True),
    # letra y digito son solo ASCII: estos tres se leían como identificadores
    # válidos cuando el léxico usaba isalpha() e isalnum(). El error cae en el
    # primer carácter que no pertenece al alfabeto, no al inicio del lexema.
    ("identificador con acento", "def main():\n    año = 1\n    print(año)\n\nmain()\n",
     "Error léxico: línea 2, columna 6: carácter inesperado 'ñ' "
     "(U+00F1 LATIN SMALL LETTER N WITH TILDE): "
     "los identificadores solo admiten letras sin acento, dígitos y '_'", False),
    # '²' no es una letra para Unicode, pero isalnum() lo acepta, así que x²
    # pasaba como un identificador que Python rechaza
    ("exponente en el identificador", "def main():\n    x² = 1\n\nmain()\n",
     "Error léxico: línea 2, columna 6: carácter inesperado '²' "
     "(U+00B2 SUPERSCRIPT TWO): "
     "los identificadores solo admiten letras sin acento, dígitos y '_'", False),
    # La ligadura 'ﬁ' (U+FB01) es un solo carácter; suele salir al copiar de un
    # PDF. Antes, 'ﬁn' y 'fin' eran dos variables distintas y el programa decía
    # que 'fin' no tiene valor, mientras que Python imprime 10 (normaliza a NFKC)
    ("ligadura fi (U+FB01) de un PDF",
     "def main():\n    ﬁn = 10\n    print(fin)\n\nmain()\n",
     "Error léxico: línea 2, columna 5: carácter inesperado 'ﬁ' "
     "(U+FB01 LATIN SMALL LIGATURE FI): "
     "los identificadores solo admiten letras sin acento, dígitos y '_'", False),

    # --- Errores sintácticos ---
    ("identificador con dígito", "def main():\n    2x = 4\n    print(2x)\n\nmain()\n",
     "Error sintáctico: línea 2, columna 5: se esperaba una sentencia, se encontró '2'", False),
    ("elif", "def main():\n    x = 7\n    if x < 0:\n        print(-1)\n"
     "    elif x == 0:\n        print(0)\n\nmain()\n",
     "Error sintáctico: línea 5, columna 10: se esperaba '=', se encontró 'x'", False),
    ("sangría de más", "def main():\n    x = 10\n        print(x)\n\nmain()\n",
     "Error sintáctico: línea 3, columna 1: se esperaba una sentencia, se encontró INDENT", False),
    # programa exige la llamada final; sin ella, el parser llega al EOF
    ("sin main() final", "def main():\n    print(7)\n",
     "Error sintáctico: línea 3, columna 1: se esperaba 'main', se encontró EOF",
     False),

    ("paréntesis en la condición", "def main():\n    x = 3\n    if (x > 0):\n"
     "        print(x)\n\nmain()\n",
     "Error sintáctico: línea 3, columna 11: se esperaba ')', se encontró '>'", False),
    ("asignación en la condición", "def main():\n    x = 1\n    if x = 3:\n"
     "        print(x)\n\nmain()\n",
     "Error sintáctico: línea 3, columna 10: se esperaba un operador relacional, "
     "se encontró '='", False),
    # Con 1000 términos ya falla, pero por un margen de solo tres llamadas,
    # que puede cambiar entre versiones de Python; 5000 deja margen amplio.
    ("suma plana de 5000 términos",
     "def main():\n    x = " + " + ".join(["1"] * 5000) + "\n    print(x)\n\nmain()\n",
     "Error: el árbol del programa es demasiado profundo "
     "(mucho anidamiento o una expresión muy larga)", False),

    # --- Enteros grandes (Python, sin set_int_max_str_digits, fallaría) ---
    ("literal de 5000 dígitos", "def main():\n    print(" + "1" * 5000 + ")\n\nmain()\n",
     "1" * 5000, False),

    # --- Errores de ejecución ---
    ("variable sin valor", "def main():\n    print(x)\n\nmain()\n",
     "Error de ejecución: la variable 'x' no tiene valor", False),
    ("residuo entre cero", "def main():\n    x = 0\n    print(5 % x)\n\nmain()\n",
     "Error de ejecución: división entre cero", False),
    ("cociente entre cero", "def main():\n    x = 7\n    print(x // 0)\n\nmain()\n",
     "Error de ejecución: división entre cero", False),
]


# Casos para sintactico.py: (nombre, programa, árbol o error esperado)
CASOS_ARBOL = [
    # La repetición { } de la gramática no fija la asociatividad; el ciclo de
    # expr() arma el árbol de izquierda a derecha: (1 - 2) - 3
    ("asociatividad izquierda", "def main():\n    x = 1 - 2 - 3\n\nmain()\n",
     "Programa\n  cuerpo:\n    Asignacion (nombre='x')\n      valor:\n"
     "        BinOp (op='-')\n          izq:\n            BinOp (op='-')\n"
     "              izq:\n                Num (valor=1)\n              der:\n"
     "                Num (valor=2)\n          der:\n            Num (valor=3)"),
    # El límite de 4300 dígitos afecta a int() en factor() y a la impresión
    ("árbol con literal de 5000 dígitos",
     "def main():\n    print(" + "1" * 5000 + ")\n\nmain()\n",
     "Programa\n  cuerpo:\n    Imprimir\n      valor:\n"
     "        Num (valor=" + "1" * 5000 + ")"),
    # El parser lee la suma de forma iterativa; lo que se agota es mostrar()
    ("árbol de una suma plana de 5000 términos",
     "def main():\n    x = " + " + ".join(["1"] * 5000) + "\n\nmain()\n",
     "Error: el árbol del programa es demasiado profundo "
     "(mucho anidamiento o una expresión muy larga)"),
]


# Casos para lex2tok.py: (nombre, programa, contenido esperado de caso.tok)
# Corren en orden sobre el mismo caso.tok: el caso con error comprueba que
# se sobrescribe el .tok que dejó el caso anterior.
CASOS_TOK = [
    ("tokens por línea", "def main():\n    for i in range(3):\n"
     "        if i > 0:\n            print(i)\n    print(9)\n\nmain()\n",
     "# Tokens de caso.py, generado por lex2tok.py\n"
     "  1  DEF MAIN ( ) : NEWLINE\n"
     "  2  INDENT FOR ID:i IN RANGE ( NUM:3 ) : NEWLINE\n"
     "  3  INDENT IF ID:i > NUM:0 : NEWLINE\n"
     "  4  INDENT PRINT ( ID:i ) NEWLINE\n"
     "  5  DEDENT DEDENT PRINT ( NUM:9 ) NEWLINE\n"
     "  7  DEDENT MAIN ( ) NEWLINE\n"
     "  8  EOF\n"),
    ("error léxico en el .tok", "def main():\n    x = 5 / 2\n\nmain()\n",
     "# Tokens de caso.py, generado por lex2tok.py\n"
     "# Error léxico: línea 2, columna 11: carácter inesperado '/'\n"),
]


def correr(comando):
    try:
        r = subprocess.run(comando, capture_output=True, text=True,
                           encoding="utf-8", env=ENTORNO, timeout=LIMITE_SEGUNDOS)
    except subprocess.TimeoutExpired:
        return f"(sin respuesta después de {LIMITE_SEGUNDOS} s: ¿ciclo infinito?)"
    return (r.stdout + r.stderr).strip()


def probar(carpeta, nombre, programa, esperado, script, con_python=False):
    """Corre un caso y devuelve True si salió lo esperado."""
    ruta = os.path.join(carpeta, "caso.py")
    datos = programa if isinstance(programa, bytes) else programa.encode("utf-8")
    with open(ruta, "wb") as f:
        f.write(datos)

    problemas = []
    obtenido = correr([sys.executable, script, ruta])
    if TRACEBACK in obtenido:
        problemas.append("MiniPy mostró un traceback de Python: toda excepción "
                         "debe traducirse a un error del lenguaje")
    if obtenido != esperado:
        problemas.append(f"MiniPy dio:\n{obtenido}")
    if con_python:
        en_python = correr([sys.executable, ruta])
        if en_python != esperado:
            problemas.append(f"Python dio:\n{en_python}")

    if problemas:
        print(f"FALLA  {nombre}\n  se esperaba:\n{esperado}")
        for p in problemas:
            print("  " + p)
        return False
    print(f"ok     {nombre}")
    return True


def probar_tok(carpeta, nombre, programa, esperado):
    """Corre lex2tok.py y compara el archivo .tok que genera."""
    ruta = os.path.join(carpeta, "caso.py")
    # En bytes, como en probar(): en modo texto, Windows escribiría "\r\n"
    # y el caso no sería el mismo en todos los sistemas
    with open(ruta, "wb") as f:
        f.write(programa.encode("utf-8"))
    salida = correr([sys.executable, LEX2TOK, ruta])
    try:
        with open(os.path.join(carpeta, "caso.tok"), encoding="utf-8") as f:
            obtenido = f.read()
    except FileNotFoundError:
        obtenido = "(no se generó caso.tok)"

    if TRACEBACK in salida or obtenido != esperado:
        print(f"FALLA  {nombre}\n  se esperaba:\n{esperado}\n  caso.tok tiene:\n{obtenido}")
        if TRACEBACK in salida:
            print(f"  lex2tok.py mostró un traceback:\n{salida}")
        return False
    print(f"ok     {nombre}")
    return True


def probar_carpeta(carpeta):
    """Le pasa a cada script una carpeta en lugar de un programa. Abrirla da
    IsADirectoryError en Linux y PermissionError en Windows; ninguno de los
    dos debe llegar al usuario como traceback."""
    nombre = "una carpeta como argumento"
    esperado = (f"No se pudo leer {carpeta} "
                "(¿es una carpeta, o no tiene permiso de lectura?)")
    problemas = []
    for script in (LEXICO, SINTACTICO, INTERPRETE, LEX2TOK, LLAVES):
        obtenido = correr([sys.executable, script, carpeta])
        if obtenido != esperado:
            problemas.append(f"{os.path.basename(script)} dio:\n{obtenido}")

    if problemas:
        print(f"FALLA  {nombre}\n  se esperaba:\n{esperado}")
        for p in problemas:
            print("  " + p)
        return False
    print(f"ok     {nombre}")
    return True


def reglas_de_la_gramatica(texto):
    """Devuelve {nombre: regla} con las reglas de gramatica.ebnf. Quita los
    comentarios (* ... *) y deja un solo espacio entre palabras, para que la
    comparación no dependa de cómo estén alineadas."""
    texto = re.sub(r"\(\*.*?\*\)", " ", texto, flags=re.DOTALL)
    reglas = {}
    nombre = None
    for linea in texto.split("\n"):
        inicio = re.match(r"\s*([A-Za-z_][A-Za-z_0-9]*)\s*::=(.*)", linea)
        if inicio:
            nombre = inicio.group(1)
            reglas[nombre] = inicio.group(2)
        elif not linea.strip():
            nombre = None                      # una línea en blanco corta la regla
        elif nombre is not None:
            reglas[nombre] += " " + linea      # continuación de la regla anterior
    return {n: " ".join(r.split()) for n, r in reglas.items()}


def probar_gramatica():
    """Comprueba que el docstring de cada método de regla de Parser sea la
    regla del mismo nombre de gramatica.ebnf. Es la única prueba que no ejecuta
    ningún script: vigila que el código no repita la gramática sin
    verificación, porque si una cambia y la otra no, esto falla."""
    nombre = "los docstrings de Parser coinciden con gramatica.ebnf"
    try:
        with open(GRAMATICA, encoding="utf-8") as f:
            reglas = reglas_de_la_gramatica(f.read())
    except FileNotFoundError:
        print(f"FALLA  {nombre}\n  no se encontró {GRAMATICA}")
        return False

    problemas = []
    for regla in REGLAS:
        metodo = getattr(Parser, regla, None)
        if metodo is None:
            problemas.append(f"{regla}: Parser no tiene ese método")
        elif regla not in reglas:
            problemas.append(f"{regla}: gramatica.ebnf no define esa regla")
        else:
            esperada = f"{regla} ::= {reglas[regla]}"
            obtenida = " ".join((metodo.__doc__ or "").split())
            if obtenida != esperada:
                problemas.append(
                    f"{regla}: el docstring dice\n"
                    f"    {obtenida or '(no tiene docstring)'}\n"
                    f"  y gramatica.ebnf dice\n"
                    f"    {esperada}")

    sobran = sorted(set(reglas) - set(REGLAS) - set(REGLAS_LEXICAS))
    if sobran:
        problemas.append("gramatica.ebnf tiene reglas que esta prueba no "
                         f"conoce: {', '.join(sobran)}")

    if problemas:
        print(f"FALLA  {nombre}")
        for p in problemas:
            print("  " + p)
        return False
    print(f"ok     {nombre}")
    return True


def main():
    correctos = 0
    total = len(CASOS) + len(CASOS_ARBOL) + len(CASOS_TOK) + 2
    with tempfile.TemporaryDirectory() as carpeta:
        print("--- interprete.py ---")
        for nombre, programa, esperado, con_python in CASOS:
            correctos += probar(carpeta, nombre, programa, esperado,
                                INTERPRETE, con_python)
        print("\n--- sintactico.py ---")
        for nombre, programa, esperado in CASOS_ARBOL:
            correctos += probar(carpeta, nombre, programa, esperado, SINTACTICO)
        print("\n--- lex2tok.py ---")
        for nombre, programa, esperado in CASOS_TOK:
            correctos += probar_tok(carpeta, nombre, programa, esperado)
        print("\n--- todos los scripts ---")
        correctos += probar_carpeta(carpeta)
    print("\n--- gramatica.ebnf ---")
    correctos += probar_gramatica()

    print(f"\n{correctos} de {total} casos correctos")
    sys.exit(0 if correctos == total else 1)


if __name__ == "__main__":
    main()
