# Gramática para un Python mínimo

## ¿Ya existe algo así?

Hay cosas parecidas, pero ninguna tan pequeña:

- **ChocoPy** (Universidad de Berkeley, curso CS164) es un subconjunto de Python con tipos estáticos, pensado justamente para cursos de compiladores. Está muy bien documentado, pero incluye clases, listas, cadenas y funciones, así que es demasiado grande para revisarlo en una sola clase.
- **Mini-Python** (Jean-Christophe Filliâtre, curso de compilación en Francia) es más pequeño, pero sigue teniendo listas, cadenas y funciones definidas por el usuario.
- La **gramática oficial de Python** (PEG, en la documentación del lenguaje) es la referencia, pero tiene cientos de reglas.

La que se presenta a continuación es muy reducida. Solo escribe código en la función `main` (no llama a funciones) y solo tiene variables enteras. Usa sentencias `for` e `if`.

## Un lenguaje separado, no un subconjunto estricto de Python

La idea inicial era que todo programa aceptado corriera también en Python. Se descartó, porque garantizarlo exige mucho más que la gramática:

- **Palabras reservadas de Python como identificadores** (léxico). El lenguaje solo reserva ocho palabras, así que acepta `while = 3` o `class = 1`, que Python rechaza. Se arreglaría reservando todas las de `keyword.kwlist`.
- **Ceros a la izquierda** (léxico). `007` es inválido en Python 3. Por eso la definición de `NUM` los excluye (ver pendientes: el código aún no lo verifica). Python sí acepta `00` y `000` (solo ceros), que `NUM` también excluye; rechazar de más no hace que un programa aceptado falle en Python.
- **Variables usadas antes de asignarse** (semántico). `print(x)` es sintácticamente correcto pero falla en ejecución. No se puede resolver con una GLC; requiere tabla de símbolos.
- **División entre cero** (ejecución). No se puede detectar en general antes de ejecutar.

La sintaxis se parece a Python y los programas típicamente corren en Python, pero el lenguaje se define por esta gramática, no por Python.

## Gramática (EBNF)

```
programa    ::= "def" "main" "(" ")" ":" bloque "main" "(" ")" NEWLINE
bloque      ::= NEWLINE INDENT sentencia { sentencia } DEDENT
sentencia   ::= asignacion | si | para | imprimir

asignacion  ::= ID "=" expr NEWLINE
imprimir    ::= "print" "(" expr ")" NEWLINE
si          ::= "if" condicion ":" bloque [ "else" ":" bloque ]
para        ::= "for" ID "in" "range" "(" expr [ "," expr ] ")" ":" bloque

condicion   ::= expr OPREL expr
expr        ::= termino { ( "+" | "-" ) termino }
termino     ::= factor { ( "*" | "//" | "%" ) factor }
factor      ::= NUM | ID | "(" expr ")" | "-" factor
```

**Tokens (nivel léxico):**

```
ID      ::= ( letra | "_" ) { letra | digito | "_" }    (excepto palabras reservadas)
NUM     ::= "0" | digito_no_cero { digito }
OPREL   ::= "==" | "!=" | "<" | "<=" | ">" | ">="
Reservadas: def main if else for in range print
NEWLINE, INDENT, DEDENT  (los genera el analizador léxico)
Comentarios: desde "#" hasta el fin de línea (el léxico los descarta)
```

Son 11 reglas sintácticas y un puñado de tokens.

## Programa de ejemplo válido

```python
def main():
    suma = 0
    for i in range(1, 11):
        if i % 2 == 0:
            suma = suma + i
        else:
            suma = suma - 1
    print(suma)

main()
```

Imprime `25`.

## Decisiones de diseño que vale la pena comentar en clase

**Sangría como tokens.** Es lo más interesante pedagógicamente. La gramática no menciona espacios: el analizador léxico lleva una pila de niveles de sangría y emite `INDENT` o `DEDENT` cuando cambia. Así la gramática queda libre de contexto y parece la de un lenguaje con llaves, donde `INDENT` equivale a `{` y `DEDENT` a `}`. De paso desaparece el problema del *else colgante*, porque la sangría deja claro a qué `if` pertenece cada `else`.

**Condiciones solo relacionales.** Al exigir `expr OPREL expr` se evita introducir un tipo booleano, así que todo el lenguaje sigue siendo solo de enteros. Por eso no hay `and`, `or` ni `not`; si se quieren después, son una ampliación como ejercicio.

**División entera `//`.** Originalmente se eligió porque en Python `/` devuelve flotante. Aunque ahora el lenguaje es independiente y podría usar `/` como C, conviene mantener `//`:
- Con `/` entera, `print(7 / 2)` daría `3` aquí y `3.5` en Python, sin aviso. Una diferencia silenciosa de resultado es peor que un error de sintaxis.
- Deja `/` libre para el equipo de flotantes. Si `/` ya fuera entera, su significado dependería del tipo de los operandos, como en C (`7 / 2` da `3`, `7.0 / 2` da `3.5`). Python eliminó justamente esa ambigüedad al pasar a la versión 3 separando `/` de `//`: un lenguaje real cambió su sintaxis para resolver un problema de semántica.
- Produce el ejemplo de error léxico con `/` sola.

**Precedencia codificada en la gramática.** La cascada `expr → termino → factor` hace que `*` gane sobre `+` sin reglas adicionales, y el `-` unario en `factor` permite escribir `-x`. La asociatividad, en cambio, no la fija la gramática: la repetición `{ }` produce una lista plana de términos, y es el ciclo del parser el que arma el árbol de izquierda a derecha (`a - b - c` queda como `(a - b) - c`). Ojo al dibujar árboles de derivación: si se reescribe `{ }` en BNF como `expr ::= termino expr'` y `expr' ::= ( "+" | "-" ) termino expr' | ε` (donde `expr'` es un no terminal auxiliar y `ε` la cadena vacía), el árbol de derivación se inclina a la derecha, al revés que el AST. Es una confusión clásica.

**Es LL(1).** No tiene recursión por la izquierda (usa repeticiones `{ }`), las cuatro alternativas de `sentencia` empiezan con tokens distintos (`ID`, `if`, `for` y `print`) y ninguna parte opcional choca con lo que puede venir después de ella. Por ejemplo, ninguna sentencia empieza con `else`, así que al terminar un `if` basta mirar un token para saber si sigue su `else`. Se puede implementar directamente como analizador descendente recursivo, con una función por regla.

**`print` incluido.** Técnicamente no hace falta, pero sin él los programas no producen salida observable, y eso dificulta probar un intérprete.

## Semántica de MiniPy

La gramática dice qué programas son válidos; esta sección dice qué hacen. Es la definición del lenguaje: el intérprete debe cumplirla, y cualquier otra implementación (por ejemplo, en C) se compara contra ella, no contra Python.

**Valores.** Solo hay enteros, positivos o negativos, sin límite de tamaño.

**Variables.** Hay un solo espacio de nombres, el de `main`. Una variable existe a partir de su primera asignación. Usar una variable que no tiene valor es error de ejecución.

**Expresiones.** En una operación binaria se evalúa primero el operando izquierdo y después el derecho; esto decide qué error aparece si ambos fallan. Los operadores:
- `+`, `-`, `*` y el menos unario tienen su significado aritmético usual.
- `a // b` es el cociente redondeado hacia menos infinito: `7 // 2` es `3` y `-7 // 2` es `-4`.
- `a % b` es el residuo que cumple `a == (a // b) * b + a % b`; su signo es el del divisor: `-7 % 2` es `1` y `7 % -2` es `-1`.
- `//` y `%` con divisor cero son error de ejecución.

**Condiciones.** Comparan dos enteros. No son valores: no se pueden asignar ni imprimir.

**Sentencias.**
- `x = expr`: evalúa la expresión y la asigna a `x`.
- `print(expr)`: imprime el entero en decimal, seguido de un salto de línea.
- `if`: evalúa la condición y ejecuta el bloque que corresponde; sin `else`, si la condición es falsa no hace nada.
- `for v in range(a, b)`: evalúa `a` y luego `b`, una sola vez. Si `a >= b`, no ejecuta el cuerpo. Si no, antes de cada vuelta asigna a `v` los valores `a`, `a + 1`, …, `b - 1`. Asignar a `v` o a las variables de los límites dentro del cuerpo no cambia el número de vueltas ni el siguiente valor de `v`. Al terminar, `v` conserva el último valor asignado; si no hubo vueltas, `v` no se modifica. `range(b)` equivale a `range(0, b)`.

**Errores de ejecución.** Detienen el programa con un mensaje del lenguaje. Ningún programa, válido o no, debe producir un traceback de Python.

**Terminación.** Todo programa termina (ver «El `for` decide el poder del lenguaje»).

## Implementación

Tres etapas separadas, cada una ejecutable por sí misma:

```
python lexico.py ejemplo.py       # lista de tokens
python sintactico.py ejemplo.py   # árbol de sintaxis abstracta (AST)
python interprete.py ejemplo.py   # ejecuta el programa
python pruebas.py                 # pruebas de regresión
```

### `lexico.py` (~165 líneas)

Trabaja línea por línea en tres pasos:

1. Mide la sangría y emite `INDENT`/`DEDENT` comparando con una pila de niveles. Si la sangría baja a un nivel que no está en la pila, es error léxico. Rechaza tabuladores.
2. Reconoce los lexemas del resto de la línea. Las palabras reservadas se distinguen de los identificadores con una búsqueda en un conjunto. Los operadores de dos caracteres se prueban antes que los de uno (si no, `//` se leería como dos `/`).
3. Al terminar el archivo, cierra con `DEDENT` los bloques abiertos y emite `EOF`.

Quita los comentarios cortando cada línea en el primer `#`. Acepta tabuladores entre tokens (no en la sangría). Separa las líneas solo en `\n` y no con `splitlines()`, que también corta en el separador de línea Unicode (U+2028) y aceptaría en silencio un programa que Python rechaza. Por la misma razón, para reconocer una línea vacía quita solo espacios y tabuladores (`strip(" \t")`): `strip()` sin argumentos también quita espacios Unicode, y una línea con solo espacios no separables pasaría en silencio.

Tiene una tabla de **caracteres engañosos** con mensajes específicos: espacio no separable, espacio de ancho cero, separador de línea Unicode, semirraya (–), raya (—), signo menos tipográfico y comillas tipográficas dobles y simples. Llegan al copiar código desde PowerPoint, PDF o páginas web (la autocorrección de PowerPoint produce rayas y comillas tipográficas), y se ven idénticos o casi idénticos a los válidos. Sirve como ejemplo en clase: el error es léxico porque el alfabeto no incluye ese carácter, aunque se vea igual que uno que sí.

### `sintactico.py` (~290 líneas)

Analizador descendente recursivo con la gramática en el encabezado y una función por regla con el mismo nombre, para leerlas lado a lado. Todo descansa en dos utilidades: `ver()` mira el token actual sin consumirlo y `consumir()` lo exige o lanza el error. Construye un AST con `dataclasses` y lo imprime con sangría.

Decisiones del código:
- `range(n)` se normaliza a `range(0, n)` en el árbol.
- La llamada final `main()` es **opcional** en el código (ver pendientes).
- El árbol se imprime solo cuando se terminó de armar: si la recursión se agota a la mitad, sale únicamente el mensaje de error.

### `interprete.py` (~120 líneas con comentarios)

Recorre el AST. `ejecutar()` procesa listas de sentencias y no devuelve nada; `evaluar()` calcula el valor de expresiones y condiciones. Las variables viven en un diccionario. `BinOp` y `Condicion` tienen la misma forma (operador, izquierda, derecha), así que se resuelven con una sola tabla de operaciones; las condiciones devuelven `True` o `False`. Reporta dos errores de ejecución: variable sin valor y división entre cero.

Si encuentra un nodo que no conoce, lanza "sentencia desconocida" o "expresión desconocida" con el nombre del nodo. Así, si un equipo agrega un nodo al parser y olvida el intérprete, el error lo dice claramente en lugar de ignorar la sentencia en silencio (lo peor posible) o fallar con un `AttributeError` confuso. El `isinstance` explícito para `BinOp` y `Condicion` también evita advertencias del análisis de tipos de PyCharm.

**Semántica apoyada en Python.** El intérprete cumple la sección «Semántica de MiniPy» usando directamente operaciones de Python, que coinciden con ella en tres puntos que en otros lenguajes son distintos. Originalmente fueron semántica prestada, que nadie había decidido; la sección de semántica los convirtió en definición:
- `//` y `%` de Python redondean hacia menos infinito, como pide la especificación. En C y Java truncan hacia cero: `-7 / 2` da `-3` y `-7 % 2` da `-1`.
- El `range` de Python evalúa los límites una vez, y modificar la variable o el límite dentro del cuerpo no altera las iteraciones. El `for` de C vuelve a evaluar la condición en cada vuelta.
- Los enteros de Python no tienen límite de tamaño. Pero desde 2022 sí hay límite para **convertirlos entre texto y entero**: con más de 4300 dígitos se lanza `ValueError`, tanto al imprimir (el factorial de 2000 lo provoca) como al leer un literal muy largo. Llegó con Python 3.11 y también con las correcciones de seguridad 3.10.7, 3.9.14, 3.8.14 y 3.7.14, así que el Python 3.10 de Ubuntu 22.04 ya lo tiene. El sintáctico y el intérprete lo desactivan con `sys.set_int_max_str_digits(0)`, por coherencia con que el lenguaje no limita los enteros.

Si un equipo escribe el intérprete en C o Java, no puede apoyarse en el lenguaje anfitrión para estos tres puntos: tiene que implementarlos para cumplir la especificación. Es buena discusión sobre dónde está definido el significado de un lenguaje: en un documento, no en la implementación que se tenga a mano.

**El `for` decide el poder del lenguaje.** Como `range` evalúa sus límites una sola vez, MiniPy es en esencia el lenguaje LOOP de Meyer y Ritchie (1967), que calcula exactamente las funciones recursivas primitivas. Todo programa termina (aunque puede tardar muchísimo) y ninguno calcula la función de Ackermann. Por eso funciona el rodeo del MCD: un `while` se simula con un `for` cuando el número de vueltas está acotado por una función recursiva primitiva de la entrada. Dos consecuencias para los proyectos: `while` es ★ por su gramática, pero semánticamente es el salto más grande de la tabla, porque vuelve al lenguaje Turing-completo y aparecen los ciclos infinitos; y un intérprete en C con el `for` de C (que vuelve a evaluar la cota en cada vuelta y deja modificar el contador) también lo vuelve Turing-completo sin cambiar una sola regla de la gramática.

Un matiz: la completitud de Turing con `while` depende de que los enteros no tengan límite. Un intérprete en C con enteros de 64 bits tendría `while` pero un número finito de estados posibles (un número fijo de variables, cada una con 2⁶⁴ valores), así que en sentido estricto sería un autómata finito enorme, como cualquier computadora real. Conecta el proyecto del intérprete en otro lenguaje con la jerarquía de autómatas.

**Limitación.** Los errores de ejecución no reportan línea, porque el AST no guarda posiciones.

### `pruebas.py` (~215 líneas)

Corre los casos de `CASOS` con `interprete.py` y los de `CASOS_ARBOL` con `sintactico.py`, y compara la salida o el mensaje de error con el esperado. En los programas válidos de `CASOS` también corre Python, para confirmar que dan el mismo resultado. Incluye los ejemplos de este documento, casos que comprueban los puntos de «Semántica de MiniPy» que en C o Java darían otro resultado (redondeo de `//` y `%`, límites del `for`, orden de evaluación) y casos que en versiones anteriores producían un traceback. Los dos pendientes (`main()` final y ceros a la izquierda) tienen su caso con el comportamiento actual y una nota de qué esperar si se deciden.

`CASOS_ARBOL` comprueba lo que solo se ve en el árbol: la asociatividad izquierda de `1 - 2 - 3` (útil junto a la derivación a mano), un literal de 5000 dígitos y la suma plana que agota la recursión al imprimir el árbol, aunque el parser la lea sin problema.

Además de comparar con lo esperado, toda salida que contenga un traceback de Python cuenta como falla, aunque el caso no lo haya previsto: la especificación exige que toda excepción se traduzca a un error del lenguaje. Así, el equipo que agregue potencia y escriba un caso con `0 ** -1` se entera de que olvidó atrapar el `ZeroDivisionError`.

Cada caso tiene un límite de 10 segundos. Con el lenguaje base sobra, pero cuando un equipo agregue `while`, un ciclo infinito cuenta como falla en lugar de dejar colgadas las pruebas.

Las pruebas que dependen del límite de recursión usan 5000 términos y no 1000: con 1000 ya fallan, pero por un margen de solo tres llamadas, que puede cambiar entre versiones de Python.

Cada equipo puede agregar sus casos al final de la lista que corresponda, y sirve como base para las pruebas cruzadas.

### Manejo de errores común

- Archivo inexistente: "No se encontró el archivo …" en lugar de un traceback (los tres programas).
- Archivo que no está en UTF-8, por ejemplo guardado en cp1252 o creado con `>` en PowerShell 5, que escribe UTF-16: "Error léxico: línea 2: el archivo no está en UTF-8 (guárdelo como UTF-8 desde el editor)" (los tres). Es léxico porque un byte que no es UTF-8 no pertenece al alfabeto, y el mensaje da la línea donde aparece. El BOM que agregan algunos editores de Windows se acepta. Los tres programas leen con la función `leer()` de `lexico.py`.
- Árbol demasiado profundo: "el árbol del programa es demasiado profundo (mucho anidamiento o una expresión muy larga)" (sintáctico e intérprete). El parser descendente recursivo, la impresión del árbol y el intérprete usan la pila de Python, que es finita; es un límite que la gramática no menciona. Con el límite de recursión por omisión de Python (1000 llamadas), lo provocan unos 330 paréntesis anidados, pero también una suma plana de unos mil términos: el texto no tiene anidamiento, pero la asociatividad izquierda produce un árbol de profundidad casi igual al número de términos. El parser lee la suma sin problema porque `expr()` es un ciclo; lo que se agota es recorrer el árbol (`mostrar()` o `evaluar()`). Buen ejemplo de que la profundidad del AST no es la del texto, y buena pregunta para el equipo de recuperación de errores.
- Ctrl+C (intérprete): "Ejecución interrumpida" en lugar de un traceback. Todo programa del lenguaje base termina, pero puede tardar muchísimo, y con `while` aparecen los ciclos infinitos.

## Programas de ejemplo

Aunque el lenguaje es mínimo, alcanza para ejemplos clásicos. Cada uno obliga a un rodeo, y cada rodeo motiva un proyecto. Todos dan el mismo resultado que en Python.

**Primo** (contando divisores):

```python
def main():
    n = 97
    divisores = 0
    for d in range(1, n + 1):
        if n % d == 0:
            divisores = divisores + 1
    if divisores == 2:
        print(1)
    else:
        print(0)

main()
```

Sin `break` no puede detenerse en el primer divisor; sin cadenas responde 1 o 0 en lugar de "sí" o "no".

**MCD** (Euclides):

```python
def main():
    a = 1071
    b = 462
    for k in range(0, b):
        if b != 0:
            r = a % b
            a = b
            b = r
    print(a)

main()
```

Imprime 21. Euclides se escribe naturalmente con `while b != 0`. El rodeo es un `for` con una cota que seguro alcanza (nunca necesita más de `b` pasos) y un `if` que lo vuelve inofensivo al terminar. Casi demuestra que `while` se simula con `for` acotado cuando se conoce una cota. Pregunta para el grupo: ¿y cuando no se conoce, como en la conjetura de Collatz?

**Suma de dígitos** (mismo truco):

```python
def main():
    n = 90817
    suma = 0
    for k in range(0, n + 1):
        if n > 0:
            suma = suma + n % 10
            n = n // 10
    print(suma)

main()
```

La cota `n + 1` es muy holgada, lo que hace evidente lo ineficiente del rodeo. Además `n` cambia dentro del ciclo, pero el rango ya se evaluó: semántica heredada del `for`.

**Factorial**:

```python
def main():
    f = 1
    for i in range(1, 31):
        f = f * i
    print(f)

main()
```

Imprime 265252859812191058636308480000000. Hace visible que el límite numérico se hereda de Python: en C, con enteros de 64 bits, se desborda a partir de 21. Es la prueba que revela si un intérprete escrito en otro lenguaje tomó una decisión sobre el tamaño de los enteros.

Otros que caben sin modificaciones: Fibonacci, números perfectos, potencia por multiplicación repetida, contar primos menores que n con ciclos anidados, Collatz acotado.

## Ejemplos de error

Elegidos porque parecen de una etapa pero son de otra. Los mensajes son la salida real de los analizadores.

### Léxicos

**1. División con una sola barra**

```python
def main():
    suma = 0
    for i in range(1, 6):
        suma = suma + i
    promedio = suma / 5
    print(promedio)
```

```
Error léxico: línea 5, columna 21: carácter inesperado '/'
```

El error más natural de un alumno. El léxico conoce `//`, pero `/` sola no pertenece al alfabeto. Sirve para explicar por qué se prueban primero los operadores de dos caracteres.

**2. Sangría que no coincide con ningún nivel**

```python
def main():
    x = 10
    if x > 5:
        x = x - 1
      print(x)
```

```
Error léxico: línea 5: la sangría no coincide con ningún nivel anterior
```

La línea 5 tiene 6 espacios y la pila contiene 0, 4 y 8. El léxico saca el 8, ve que 6 no es 4 y no sabe a qué bloque pertenece `print`. Sorprende que un problema de espacios sea léxico, pero la sangría se convierte en tokens antes de llegar al sintáctico.

Otros posibles: `x = 2.5` (el punto no es del alfabeto), `print("hola")` (las comillas tampoco).

### Sintácticos

**3. Identificador que empieza con dígito**

```python
def main():
    2x = 4
    print(2x)
```

```
Error sintáctico: línea 2, columna 5: se esperaba una sentencia, se encontró '2'
```

Casi todos esperan un error léxico, pero el léxico parte `2x` sin protestar en `NUM '2'` e `ID 'x'`. Es el sintáctico quien descubre que ninguna sentencia empieza con un número. Conviene mostrar la salida de `lexico.py` junto al error.

**4. Usar `elif`**

```python
def main():
    x = 7
    if x < 0:
        print(-1)
    elif x == 0:
        print(0)
```

```
Error sintáctico: línea 5, columna 10: se esperaba =, se encontró 'x'
```

`elif` no es reservada, así que llega como `ID`. El parser supone una asignación y espera `=`. El mensaje es correcto pero confuso: el analizador reporta dónde falló su predicción, no lo que el programador quiso escribir. Da pie a discutir la calidad de los mensajes de error.

Otro posible: `if x = 3:` (tokens válidos, orden incorrecto; confundir `=` con `==` es sintáctico).

**5. Paréntesis alrededor de la condición**

```python
def main():
    x = 3
    if (x > 0):
        print(x)
```

```
Error sintáctico: línea 3, columna 11: se esperaba ), se encontró '>'
```

Es Python válido y una costumbre que viene de C. Aquí los paréntesis solo pueden encerrar una `expr`, y `x > 0` es una `condicion`: el parser entra a `factor` por el `(`, lee `x` como expresión y espera el `)`. Anticipa el conflicto del proyecto `and`/`or`: al ver `(`, el parser no sabe si abre una expresión o una condición.

### Contraste de sangría

```python
def main():
    x = 10
        print(x)
```

```
Error sintáctico: línea 3, columna 1: se esperaba una sentencia, se encontró INDENT
```

Asimetría con el ejemplo 2: sangrar de más siempre es léxicamente válido (abre un nivel nuevo), y el error lo detecta el sintáctico porque la gramática solo permite `INDENT` después de `:`. Sangrar de menos a un nivel inexistente lo detecta el léxico, porque no tiene ningún token que emitir.

## Proyectos de modificación

Cada equipo expone qué cambia en la gramática y en los analizadores.

Niveles según cuánto tocan del código y qué tan lejos llevan de lo visto en clase: **★** cambia solo el léxico o agrega una regla independiente; **★★** varias reglas, alguna decisión de diseño o un conflicto que resolver; **★★★** cambia la estructura de una etapa o requiere conceptos más allá de las GLC.

La columna **Intérprete** indica si la mejora obliga a modificar `interprete.py` (ver la sección sobre azúcar sintáctica).

### Nivel ★

| Mejora | Qué cambia | Por qué es interesante | Intérprete |
|---|---|---|---|
| `range(a, b, paso)` | Una alternativa en `para` | Buen calentamiento para entender el código. Semántica heredada: `range(0, 10, 0)` lanza un `ValueError` de Python que nadie atrapa | Sí (campo `paso`) |
| `while` | Una regla nueva | Muestra lo fácil que es crecer cuando la gramática es LL(1). Semánticamente es el salto más grande: el lenguaje se vuelve Turing-completo (ver «El `for` decide el poder del lenguaje») | Sí |
| `elif` | Una regla y una palabra reservada | Corrige el mensaje confuso del ejemplo de error 4 | Depende |
| `+=`, `-=`, `*=` | Tokens nuevos y una alternativa en `asignacion` | El léxico debe probar `+=` antes que `+` | Depende |
| `print` con varios argumentos | Lista separada por comas | Patrón de lista que se reutiliza en funciones | Sí |

### Nivel ★★

| Mejora | Qué cambia | Por qué es interesante | Intérprete |
|---|---|---|---|
| **Potencia** (`**`) | Nuevo nivel de precedencia | Es asociativa por la derecha (`2**3**2` = `2**9`) y además `-2**2` vale `-4`, así que hay que reacomodar el menos unario. Excelente para precedencia y asociatividad. Semántica heredada: `2 ** -1` da `0.5`, un flotante en un lenguaje de enteros, y `0 ** -1` lanza `ZeroDivisionError`, que el intérprete no atrapa (solo revisa `//` y `%`) | Sí (una línea, más esos dos casos) |
| **Flotantes** | Léxico: `3.14`, `.5`, `2.`, `1e-3`; gramática: casi nada | El autómata del léxico es lo valioso. La gramática apenas cambia, y descubren que mezclar enteros y flotantes es un problema semántico, no sintáctico | Casi nada (hereda Python, incluidos sus errores: `range(2.5)` lanza `TypeError` y el factorial de 200 por `1.0` lanza `OverflowError`) |
| **Cadenas** | Léxico: comillas, escapes, cadena sin cerrar | Rompe los comentarios: hoy `print("a#b")` se corta en el `#`. **Especificar el alcance:** solo en `print` es ★★; si se permite `"a" + "b"` aparecen los tipos y se vuelve semántico | Sí (`"a" + 1` produce un traceback de Python) |
| **Funciones predefinidas** (`abs`, `max`, `sqrt`) | `factor ::= ID [ "(" args ")" ]` | Si la escriben como dos alternativas que empiezan con `ID`, deja de ser LL(1). Ejemplo perfecto de factorización por la izquierda. `sqrt` con solo enteros debe ser raíz entera (como `math.isqrt`); la raíz real requiere flotantes | Sí |
| **`and`, `or`, `not`** (limítrofe con ★★★) | Varios niveles de precedencia en condiciones | Conflicto real: al ver `(`, el parser no sabe si abre una expresión o una condición. Se resuelve unificando expresiones y condiciones en una sola jerarquía, como Python; es un cambio grande | Sí (cortocircuito) |
| Arreglos de una dimensión, creados con literal (`[1, 2, 3]`) | Asignación y factor con índice | Otra vez factorización: `ID` puede ir seguido de `=` o de `[`. Primer tipo distinto de entero. **Especificar el alcance:** si se pide `[0] * n`, ya es un problema de tipos | Sí |
| Arreglos de dos dimensiones `m[i][j]` (★★ en gramática, ★★★ con intérprete) | Repetición `{ "[" expr "]" }` | La gramática se generaliza a n dimensiones con una repetición; el aliasing obliga a decidir entre copiar y compartir. Ver sección de arreglos | Sí |
| Árbol visual con Graphviz | Genera un `.dot` desde el AST | Útil para todo el grupo: las demás mejoras se ven mejor en el árbol | No |
| Tipos explícitos (`x: int = 3`) | Una alternativa en `asignacion` | Prepara el terreno para verificación de tipos | Depende |
| Errores de ejecución con línea | Los nodos del AST guardan la línea de su token | Muestra qué información debe pasar de una etapa a otra | Sí |

### Nivel ★★★

| Mejora | Qué cambia | Por qué es interesante | Intérprete |
|---|---|---|---|
| **Comentarios multilínea** | El léxico trabaja línea por línea y hay que reestructurarlo | Una línea dentro del comentario no debe generar `INDENT`, y un comentario sin cerrar debe reportarse al final. Si se permiten anidados, ya no son un lenguaje regular: requieren un contador. Conecta con la jerarquía de Chomsky | No |
| **Funciones definidas por el usuario** | `programa ::= { funcion }`, parámetros, `return` | Deja de existir solo `main`. `return` fuera de una función es otra restricción contextual, y aparecen las variables locales | Sí |
| **`break` y `continue`** | Sintaxis trivial; la restricción y la semántica no | Solo son válidos dentro de un ciclo. Se puede expresar con una GLC, pero duplicando reglas; en la práctica se verifica con un indicador o después. Ver sección dedicada | Sí |
| Expresiones en varias líneas dentro de paréntesis | El léxico cuenta paréntesis abiertos y suprime `NEWLINE` | El léxico necesita información que parece sintáctica; cuestiona la separación limpia de etapas | No |
| Recuperación de errores | Reportar más de un error (modo pánico) | Hoy el parser se detiene en el primero. Sincronizar en `NEWLINE` o `DEDENT` es elegante pero sutil | No |
| Generar el parser con una herramienta (Lark, ANTLR) | Escribir la gramática en la notación de la herramienta | Comparan el parser escrito a mano con uno generado. Lark trae soporte para sangría al estilo Python | No, si genera el mismo AST |
| Listas dinámicas (`append`, `len`, `for x in a`) | Expresiones postfijas, punto en el léxico | Sentencias que no se distinguen con lectura adelantada fija; verificación de *lvalue*; choque con flotantes por el punto. Ver sección de arreglos | Sí |
| Intérprete en otro lenguaje (C, Java) | Reescribir `interprete.py` | Obliga a definir explícitamente la semántica de `//`, `%`, el `for` y el tamaño de los enteros (el factorial de 30 es la prueba) | — |
| Análisis semántico | Tabla de símbolos | Detectar variables usadas sin asignar, o tipos incompatibles si alguien agregó flotantes o cadenas. Hay que distinguir dos niveles. Detectar en ejecución que una variable no tiene valor ya lo hace el intérprete. Verificar antes de ejecutar que tiene valor en todos los caminos posibles es análisis de asignación definida, como el de Java: en `for i in range(0, n): y = i` seguido de `print(y)`, `y` no tiene valor si `n` es 0, y el análisis debe decidir si rechaza el programa (conservador) o no | No (etapa nueva) |

## Azúcar sintáctica: ¿cuándo cambia el intérprete?

El intérprete solo cambia cuando la mejora agrega un **significado nuevo**. Si lo nuevo puede expresarse con los nodos que ya existen en el AST, el parser hace la traducción y el intérprete no se entera. Eso es azúcar sintáctica.

- **No lo tocan:** comentarios multilínea, paréntesis en varias líneas, bloques en una línea, recuperación de errores. Los números en otras bases o con separadores (`0x1F`, `1_000`) producen el mismo `Num`; basta `int(valor, 0)` en el parser, aunque `int("007", 0)` lanza `ValueError`: antes hay que resolver el pendiente de los ceros a la izquierda. Graphviz o un formateador son módulos nuevos que leen el AST.
- **Depende del diseño:** `x += 1` puede traducirse a `Asignacion("x", BinOp("+", Var("x"), Num(1)))`; `elif` a un `Si` anidado en el `sino`. Si el equipo crea nodos nuevos, debe modificar el intérprete. Ambas opciones son válidas; preguntar cuál eligió y por qué es buena pregunta de exposición.
- **Sí lo tocan:** todo lo que agrega comportamiento. Algunos casos engañosos:
  - Potencia y flotantes son casi gratis porque Python ya sabe hacerlo: otra vez semántica heredada, con todo y sus excepciones (ver la tabla de proyectos).
  - Con cadenas, `"a" + 1` lanza un `TypeError` de Python que el intérprete no atrapa. Aparece la necesidad de verificar tipos.
  - `and`/`or` no caben en la tabla de operaciones porque la tabla evalúa ambos lados. En `x != 0 and 10 // x > 1` con `x = 0` debe detenerse en el primer operando. Hay que implementar el cortocircuito aparte.

Pregunta para cada equipo: "¿tu mejora necesitó cambiar el intérprete?" Si no, deben poder explicar por qué es azúcar sintáctica; si sí, qué significado nuevo agregaron.

## `break` y `continue` a fondo

La sintaxis es trivial, pero alrededor hay tres problemas.

### 1. Sintaxis

Dos palabras reservadas y dos alternativas:

```
sentencia ::= asignacion | si | para | imprimir | "break" NEWLINE | "continue" NEWLINE
```

Así se acepta `break` en cualquier lugar, incluso directamente en `main`.

### 2. Dónde se permite

**Opción A: duplicar la gramática.**

```
bloque          ::= NEWLINE INDENT sentencia { sentencia } DEDENT
bloque_ciclo    ::= NEWLINE INDENT sentencia_ciclo { sentencia_ciclo } DEDENT

sentencia       ::= asignacion | si | para | imprimir
sentencia_ciclo ::= asignacion | si_ciclo | para | imprimir
                  | "break" NEWLINE | "continue" NEWLINE

si              ::= "if" condicion ":" bloque [ "else" ":" bloque ]
si_ciclo        ::= "if" condicion ":" bloque_ciclo [ "else" ":" bloque_ciclo ]
para            ::= "for" ID "in" "range" "(" expr [ "," expr ] ")" ":" bloque_ciclo
```

Demuestra que la restricción **sí es libre de contexto**: "estar dentro de" es una propiedad de anidamiento, como los paréntesis balanceados (a diferencia de "variable declarada antes de usarse", que no lo es). Pero `if` también tuvo que duplicarse, porque un `break` dentro de un `if` dentro de un `for` es válido. Cada sentencia con bloques necesita dos versiones; con `while` y `elif` crecen más, y si además se agregan funciones con `return`, se necesitan cuatro versiones de cada regla. La gramática crece de forma multiplicativa con cada restricción de este tipo.

**Opción B: un indicador en el parser.**

```python
def para(self):
    ...
    self.ciclos += 1
    cuerpo = self.bloque()
    self.ciclos -= 1
    ...

def sentencia(self):
    ...
    if self.ver("BREAK", "CONTINUE"):
        tok = self.actual()
        if self.ciclos == 0:
            raise ErrorSintactico(
                f"línea {tok.linea}: '{tok.valor}' fuera de un ciclo")
        self.pos += 1
        self.consumir("NEWLINE")
        return Break() if tok.tipo == "BREAK" else Continue()
```

Gramática pequeña y mejor mensaje de error. Formalmente equivale a un atributo heredado ("¿estoy en un ciclo?"): gramáticas de atributos.

**Opción C: verificarlo después, sobre el AST.** Una pasada posterior busca `break` fuera de un `Para`. Así lo hace Python: su gramática permite `break` como cualquier sentencia simple, y el error `'break' outside loop` lo detecta el compilador después del análisis sintáctico.

Pregunta para el equipo: ¿qué etapa reporta el error? Con A y B es sintáctico; con C, semántico. Las tres son defendibles. Sugerencia: que el equipo **muestre** la opción A aunque implemente la B; ver la gramática duplicada convence de por qué los compiladores no lo hacen así.

### 3. Semántica (con intérprete)

**`continue` y el incremento.** Si el `for` se traduce a un ciclo con contador manual, la versión ingenua:

```python
i = a
while i < b:
    cuerpo        # si aquí hay un continue...
    i = i + 1     # ...esta línea nunca se ejecuta
```

entra en ciclo infinito. Prueba (debe imprimir 0, 1, 3, 4):

```python
def main():
    for i in range(0, 5):
        if i == 2:
            continue
        print(i)

main()
```

**`break` solo sale del ciclo más interno.** En un intérprete en Python lo natural es usar excepciones (`raise Break`), y es fácil atraparlas en el lugar equivocado. Prueba (debe imprimir 0, 10, 20):

```python
def main():
    for i in range(0, 3):
        for j in range(0, 3):
            if j == 1:
                break
            print(i * 10 + j)

main()
```

**Valor de la variable después de `break`.** En Python conserva el valor del momento en que se salió.

### Extensiones para un equipo avanzado

- Detectar código inalcanzable después de un `break` en el mismo bloque (advertencia; primer análisis de flujo).
- `for ... else` de Python: el `else` se ejecuta solo si el ciclo terminó sin `break`.

## Arreglos y listas a fondo

La diferencia entre una y dos dimensiones es pequeña en la gramática y grande en la semántica; las listas dinámicas agregan un problema sintáctico nuevo.

### Una dimensión

Hay que decidir cómo se crean. Con literal es solo gramática:

```
factor     ::= ... | ID [ "[" expr "]" ] | "[" [ expr { "," expr } ] "]"
asignacion ::= ID [ "[" expr "]" ] "=" expr NEWLINE
```

`[0] * 10` parece gratis porque la gramática ya lo acepta, pero significa multiplicar una lista por un entero: un problema de tipos. Con cualquiera de las dos, el lenguaje deja de tener un solo tipo: `a + 1`, `print(a)` o `if a < 3:` son sintácticamente válidos y alguien debe decidir qué significan o rechazarlos. Errores de ejecución nuevos: índice fuera de rango e indexar algo que no es arreglo. Y con listas de Python, `a[-1]` da el último elemento sin que nadie lo haya decidido.

### Dos dimensiones

**Estilo Python: `m[i][j]`.** Arreglo de arreglos. La gramática se simplifica al generalizar: cambiar el corchete opcional por una repetición da n dimensiones.

```
factor  ::= ... | ID { "[" expr "]" }
destino ::= ID { "[" expr "]" }
```

Las literales anidadas (`[[1, 2], [3, 4]]`) no cuestan nada porque `expr` ya es recursiva. El costo es el **aliasing**. Con listas de Python se hereda:

```python
m = [[0] * 3] * 3
m[0][0] = 1
print(m)        # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
```

Las tres filas son el mismo objeto. El problema ya existe en una dimensión: después de `b = a`, modificar `b[0]` modifica `a`. Hasta ahora todo valor era un entero inmutable y la pregunta no existía; con arreglos el lenguaje debe decidir si la asignación copia o comparte. El equipo puede tomar esa decisión sin saber que la está tomando. También quedan permitidas por defecto filas de distinto tamaño.

**Estilo matriz: `m[i, j]`.** Como Fortran o NumPy. Lista de índices en la gramática y declaración con dimensiones. A cambio, rectangular por definición, sin aliasing entre filas, y errores de rango por dimensión. Menos parecido a Python, semánticamente más limpio.

### Listas dinámicas

`append` trae la notación de punto, con tres consecuencias:

- **Léxica:** el punto entra al alfabeto. Al integrar con flotantes, el léxico debe distinguir `a.append` de `2.5` (después de un identificador es acceso; después de dígitos, decimal).
- **Sintáctica:** hoy una sentencia que empieza con `ID` siempre es asignación. Con listas, `a = 5`, `a[i] = 5`, `a[i][j] = 5`, `a.append(5)` y `a[i].append(5)` empiezan igual, y el parser no sabe qué es hasta recorrer una cadena de sufijos de longitud arbitraria. Ninguna lectura adelantada fija lo resuelve. La solución estándar (la de Python) es analizar una expresión postfija y decidir después:

  ```
  sentencia_expr ::= postfijo [ "=" expr ] NEWLINE
  postfijo       ::= ID { "[" expr "]" | "." ID "(" [ args ] ")" }
  ```

  Pero esto acepta `a.append(5) = 3`, así que hace falta verificar fuera de la gramática que la izquierda del `=` sea asignable: la noción de *lvalue*. Otro caso, como `break`, de restricción que la gramática deja pasar.
- **Traslapes:** `len(a)` es una función (se cruza con funciones predefinidas), y `for x in a:` cambia la regla `para`.

## Organización de los equipos

Algunas mejoras chocan entre sí. Cadenas y comentarios tocan la misma parte del léxico; `and`/`or` y funciones predefinidas modifican `factor`; flotantes y potencia cambian la precedencia. Cada equipo trabaja sobre su propia copia de la versión base, y al final puede proponerse como reto unir dos mejoras.

El intérprete se entrega desde el inicio junto con el léxico y el sintáctico. Así cada equipo puede mostrar un programa que antes no corría y ahora sí.

Al asignar mejoras limítrofes (cadenas, `and`/`or`, arreglos), especificar el alcance para que la dificultad sea la pretendida.

Dependencias entre proyectos: `sqrt` real necesita flotantes. El ejemplo de las raíces de una ecuación cuadrática es buen candidato para el reto de integración (funciones predefinidas + flotantes).

## Evaluación

Todos los equipos entregan los mismos cinco elementos, sin importar la mejora. Da una base común para comparar proyectos de dificultad desigual, y evita que una exposición vistosa pero superficial valga lo mismo que una que resolvió un problema formal difícil.

1. **Especificación**, antes de implementar: qué programas nuevos acepta el lenguaje y qué hacen, en el estilo de «Semántica de MiniPy». Si introduce operadores, su precedencia y asociatividad; además, el comportamiento en casos límite y los errores que puede producir.
2. **Gramática** antes y después: reglas nuevas y modificadas.
3. **Implementación**: cambios en léxico, parser, AST e intérprete, según corresponda. Si cambió el intérprete, qué significado nuevo agregó; si no, por qué su mejora es azúcar sintáctica.
4. **Pruebas**: casos nuevos en `pruebas.py` (al menos un programa que ahora se acepta y uno que se rechaza en cada etapa que toque la mejora) y la suite completa pasando, sin tracebacks.
5. **Análisis de la decisión**: qué alternativas consideraron, por qué eligieron la suya y qué limitaciones quedan. Es el entregable que mejor distingue a un equipo que entendió de uno que solo hizo funcionar el código.

Como usarán IA, conviene evaluar lo que la IA no puede hacer por ellos durante la exposición: explicar, predecir y defender decisiones.

- **Pruebas cruzadas.** Antes de exponer, cada equipo entrega sus analizadores a otro, que intenta romperlos con programas que deberían aceptarse y no se aceptan, o al revés. Cada falla encontrada suma puntos al equipo atacante. Los defensores pueden corregir y explicar el error en su exposición.
- **Predecir antes de ejecutar.** El equipo muestra un programa y el grupo vota si se acepta y, si no, en qué etapa y línea falla. Luego se ejecuta. Evalúa también a la audiencia.
- **Preguntas a un integrante al azar.** "¿Qué pasa si intercambias el orden de estas dos alternativas?", "¿por qué esta regla no genera conflicto?", "¿por qué este error es léxico y no sintáctico?". Para el equipo de potencia o de recuperación de errores: "¿qué operadores se podrían reacomodar para que el árbol quede equilibrado, y por qué no `-` ni `//`?". Mide si el trabajo fue de todo el equipo.
- **Derivación a mano.** Árbol de derivación en el pizarrón de un programa corto con su mejora, comparado con el AST del analizador. Las diferencias (el de derivación tiene `expr`, `termino`, `factor`; el AST no) llevan a discutir árbol concreto contra abstracto. Si reescriben `{ }` en BNF, el árbol de derivación de `a - b - c` se inclina a la derecha y el AST a la izquierda (ver «Precedencia codificada en la gramática»).
- **Bitácora de uso de IA.** Qué le pidieron a la IA y, sobre todo, en qué se equivocó y cómo lo detectaron. Dar puntos por errores de la IA encontrados cambia el incentivo: conviene demostrar que la supervisaron. Con gramáticas es común que la IA proponga recursión por la izquierda o conflictos LL(1) sin advertirlo.
- **Especificación y gramática primero.** Entrega previa de los entregables 1 y 2, antes del código. Permite revisar el diseño cuando todavía es barato cambiarlo.
- **El diff como material de exposición.** Mostrar el `git diff` contra la versión base y justificar cada cambio. Un cambio pequeño y limpio refleja mejor comprensión que reescribir medio archivo.
- **Reto final de integración.** Juntar dos mejoras que choquen (cadenas con comentarios, `and`/`or` con funciones predefinidas, listas con flotantes por el punto) o que se necesiten (funciones con flotantes para la ecuación cuadrática).

Si solo se eligen dos: pruebas cruzadas (calidad del trabajo) y preguntas al azar (comprensión individual).

## Repositorio

- **No dejar el repositorio en Google Drive.** Drive sincroniza los archivos internos de `.git` mientras Git los modifica, y puede corromperlo o crear copias en conflicto (`ejemplo (1).py`). También genera los `desktop.ini`. Mejor una carpeta local y GitHub/GitLab como respaldo y para clonarlo en Linux.
- **`.gitignore`** en la raíz del proyecto (no confundir con el que virtualenv crea dentro de `.venv`, que debe contener solo `*`): `__pycache__/`, `*.pyc`, `.venv/`, `.idea/`, `*.pptx`, `~$*` (archivos de bloqueo de Office), `desktop.ini`, `Thumbs.db`.
- **`.gitattributes`** con `* text=auto eol=lf` para que los fines de línea de Windows no llenen los diffs de cambios falsos.
- **Mayúsculas en nombres de archivo:** Windows no las distingue y Linux sí, aunque no donde uno esperaría. Los `import` de Python las distinguen también en Windows (PEP 235): si el archivo se llama `Lexico.py`, `from lexico import` falla en los dos sistemas. Los problemas reales son otros dos. `python interprete.py Ejemplo.py` encuentra `ejemplo.py` en Windows y no en Linux, porque `open()` sí depende del sistema de archivos. Y Git en Windows no registra un renombrado que solo cambia mayúsculas: si un alumno renombra `lexico.py` a `Lexico.py` desde el explorador y ajusta sus `import`, en Windows todo funciona, pero el repositorio conserva `lexico.py` y el clon en Linux falla. Para renombrar así hay que usar `git mv lexico.py Lexico.py`.
- Verificar con `git ls-files` (qué se versiona) y `git status --ignored`. Si algo ya versionado debió ignorarse: `git rm -r --cached carpeta`.
- No hay dependencias externas; en Linux basta `python3 interprete.py ejemplo.py`.

## Pendientes

- **`main()` final:** la gramática lo exige, pero `sintactico.py` lo acepta como opcional. Decidir y alinear. (Ya que es un lenguaje separado, podría eliminarse de la gramática.)
- **Ceros a la izquierda:** la gramática excluye `007`, pero `lexico.py` lo acepta. Agregar la verificación o relajar la definición de `NUM`.
- **Definición de `letra`:** el léxico usa `isalpha()` para el primer carácter e `isalnum()` para los demás, que aceptan letras acentuadas (`año`) y otros caracteres Unicode. Consecuencias: acepta `x²` y `x₁`, que Python rechaza, y trata la ligadura `ﬁ` (un solo carácter, U+FB01, que a veces sale al copiar de un PDF) como distinta de `fi`. Así, `ﬁn = 10` seguido de `print(fin)` da "la variable 'fin' no tiene valor", mientras que Python imprime 10 porque normaliza los identificadores (forma NFKC). Decidir si `letra` y `digito` son solo ASCII, lo que convierte los tres casos en un error léxico claro.
