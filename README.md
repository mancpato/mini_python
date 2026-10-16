# MiniPy

MiniPy es un lenguaje de programación mínimo, con sintaxis parecida a la de Python, hecho para estudiar cómo una gramática libre de contexto se convierte en un programa que reconoce y ejecuta un lenguaje.

Es deliberadamente pequeño: solo tiene variables enteras, asignación, `if`, `for` con `range` y `print`, y todo el código va dentro de la función `main`. Su gramática tiene 11 reglas sintácticas. El trabajo del curso consiste en extenderlo, por equipos, y explicar qué cambia en la gramática y en cada etapa del analizador.

## Archivos

| Archivo | Qué es |
|---|---|
| `gramatica.ebnf` | La gramática del lenguaje: **la referencia oficial**. Todo lo demás debe coincidir con ella. |
| `lexico.py` | Analizador léxico: convierte el texto del programa en una lista de tokens. |
| `sintactico.py` | Analizador sintáctico: convierte los tokens en un árbol de sintaxis abstracta (AST). |
| `interprete.py` | Intérprete: recorre el árbol y ejecuta el programa. |
| `pruebas.py` | Pruebas de regresión: verifica que todo lo anterior funcione y siga funcionando. |

Su trabajo consiste en modificar los cuatro primeros, según lo que pida su extensión, y en agregar sus casos a `pruebas.py`. Los demás archivos son de apoyo y no se modifican:

| Archivo | Qué es |
|---|---|
| `lexico_simple.py`, `sintactico_simple.py` | Esqueletos de las dos primeras etapas, sin los mensajes ni las protecciones de la versión completa; conviene leerlos primero. Su árbol es de tuplas, no de clases, así que `interprete.py` no lo entiende, y las pruebas no los revisan. |
| `lex2tok.py` | Escribe los tokens de un programa en un archivo `.tok`, un renglón por cada línea del programa, para compararlos lado a lado con el original. Sirve para revisar cualquier cambio al léxico. |
| `llaves.py` | Muestra el programa con llaves en lugar de sangría, que es como lo ve el analizador sintáctico. |
| `ejemplos/` | Programas de ejemplo y, en `ejemplos/errores/`, uno por cada renglón de la tabla «Qué etapa detecta cada error». |

`lex2tok.py` y `llaves.py` dependen de `lexico.py`: de `analizar()` y de los cuatro campos de cada `Token` (tipo, valor, línea y columna). Si su cambio al léxico los conserva, siguen funcionando; `pruebas.py` lo verifica para `lex2tok.py`.

Solo usan la biblioteca estándar de Python (3.8 o posterior); no hay nada que instalar.

## Uso

Cada etapa se puede ejecutar por separado, para ver qué produce:

```
python lexico.py ejemplos/ejemplo.py       # lista de tokens
python sintactico.py ejemplos/ejemplo.py   # árbol de sintaxis abstracta
python interprete.py ejemplos/ejemplo.py   # ejecuta el programa
python pruebas.py                          # corre todas las pruebas
```

Y las herramientas de apoyo:

```
python lex2tok.py ejemplos/ejemplo.py      # escribe ejemplos/ejemplo.tok
python llaves.py ejemplos/ejemplo.py       # el programa con llaves
python sintactico_simple.py ejemplos/ejemplo.py   # árbol de tuplas, versión simple
```

`llaves.py` tiene dos opciones más, `--plano` y `--una-linea`, descritas al inicio del archivo. En Linux, use `python3` en lugar de `python`.

## Un programa de ejemplo

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

Imprime `25`. La llamada final `main()` es obligatoria. Este programa está en `ejemplos/ejemplo.py`.

Aunque el lenguaje es mínimo, alcanza para algoritmos clásicos. Por ejemplo, el máximo común divisor con el algoritmo de Euclides, que normalmente se escribe con `while`, se puede escribir con un `for` cuyo límite seguro alcanza:

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

Imprime `21`. Está en `ejemplos/euclides.py`.

## Un lenguaje propio, no un subconjunto de Python

La mayoría de los programas de MiniPy también corren en Python y dan el mismo resultado, pero MiniPy es un lenguaje independiente: lo definen `gramatica.ebnf` y la sección «Semántica de MiniPy» de este documento, no Python. Hay programas que Python acepta y MiniPy no (`if (x > 0):`, `año = 1`) y viceversa (`while = 3` es un identificador válido en MiniPy).

## La gramática

La gramática está en `gramatica.ebnf`, en notación EBNF:

| Notación | Significado |
|---|---|
| `"x"` | el terminal `x`, literalmente |
| `{ x }` | cero o más repeticiones de `x` |
| `[ x ]` | `x` es opcional |
| `( x )` | agrupa: `( "+" \| "-" )` es `"+"` o `"-"` |
| `a \| b` | `a` o `b` |
| `"a" \| ... \| "z"` | todos los caracteres del rango (abreviatura) |

El archivo tiene dos partes. La **sintaxis** describe cómo se combinan los tokens (sentencias, expresiones, bloques). El **léxico** describe cómo se forman los tokens a partir de caracteres (identificadores, números, operadores).

Dos decisiones de la gramática que conviene entender desde el principio:

**La precedencia está en la gramática.** Las reglas `expr`, `termino` y `factor` forman una cascada: `expr` suma términos, `termino` multiplica factores. Por eso `*` se aplica antes que `+` sin ninguna regla adicional. La asociatividad, en cambio, no la fija la repetición `{ }`: la decide el código que arma el árbol (ver `sintactico.py`).

**La sangría no aparece en la gramática.** No hay espacios en ninguna regla. El analizador léxico convierte la sangría en dos tokens, `INDENT` y `DEDENT`, que funcionan como las llaves `{` y `}` de C o Java. Así, el analizador sintáctico nunca ve un espacio.

## Las tres etapas

### Analizador léxico (`lexico.py`)

Recorre el programa línea por línea. Para cada línea:

1. Cuenta los espacios del inicio y los compara con una **pila de niveles de sangría**. Si la sangría aumenta, apila el nuevo nivel y emite `INDENT`. Si disminuye, desapila hasta encontrar el nivel y emite un `DEDENT` por cada nivel que cierra (pueden ser varios). Si no encuentra el nivel, es un error léxico.
2. Reconoce los tokens del resto de la línea: números, identificadores, palabras reservadas y operadores. Los operadores de dos caracteres (`//`, `==`, `<=`, …) se prueban antes que los de uno, y un identificador se lee completo antes de decidir si es palabra reservada. Es la regla del lexema más largo: `<=` es un solo token, e `ifx` es un identificador, no `if` seguido de `x`.
3. Emite `NEWLINE` al final de la línea.

Las líneas vacías y los comentarios (desde `#` hasta el fin de línea) no producen tokens. El alfabeto es ASCII: letras sin acento, dígitos, `_` y los símbolos de los operadores. Algunos caracteres que se ven iguales a otros válidos (el espacio no separable, la raya `—`, las comillas tipográficas), y que suelen colarse al copiar código desde una presentación o un PDF, reciben un mensaje de error específico. Cualquier otro carácter fuera de ASCII se reporta con su código y su nombre Unicode, por ejemplo `'а' (U+0430 CYRILLIC SMALL LETTER A)`, para distinguirlo del carácter válido al que se parece.

### Analizador sintáctico (`sintactico.py`)

Es un **analizador descendente recursivo**: tiene un método por cada regla de la gramática, con el mismo nombre, y el docstring de cada método es su regla, copiada de `gramatica.ebnf`. Leer la regla junto a su método es la mejor forma de entender cómo una gramática se convierte en código.

Todo descansa en dos utilidades: `ver()` revisa si el token actual es de cierto tipo sin consumirlo, y `consumir()` exige un token de cierto tipo y avanza, o produce un error si no lo encuentra.

La gramática es **LL(1)**: en cada punto de decisión basta mirar un token para saber qué regla aplicar. Por ejemplo, las cuatro alternativas de `sentencia` empiezan con `ID`, `if`, `for` y `print`, todos distintos. Cualquier cambio a la gramática debe conservar esta propiedad.

El resultado es un árbol de sintaxis abstracta, hecho con clases `dataclass` (`Asignacion`, `Si`, `Para`, `BinOp`, …).

### Intérprete (`interprete.py`)

Recorre el árbol con dos funciones: `ejecutar()` procesa sentencias, que no devuelven nada, y `evaluar()` calcula el valor de expresiones y condiciones. Las variables se guardan en un diccionario. Si encuentra un nodo que no conoce, lo reporta como error, para que un nodo nuevo que se olvidó implementar no pase inadvertido.

## Semántica de MiniPy

La gramática dice qué programas son válidos; esta sección dice qué hacen. Es la definición del lenguaje: el intérprete debe cumplirla, y cualquier otra implementación se compara contra ella, no contra Python.

**Valores.** Solo hay enteros (positivos, negativos y el cero), sin límite de tamaño.

**Variables.** Hay un solo espacio de nombres, el de `main`. Una variable existe a partir de su primera asignación. Usar una variable que no tiene valor es error de ejecución.

**Expresiones.** En una operación binaria se evalúa primero el operando izquierdo y después el derecho; esto decide qué error aparece si ambos fallan. Los operadores:
- `+`, `-`, `*` y el menos unario tienen su significado aritmético usual.
- `a // b` es el cociente redondeado hacia menos infinito: `7 // 2` es `3` y `-7 // 2` es `-4`.
- `a % b` es el residuo que cumple `a == (a // b) * b + a % b`; su signo es el del divisor cuando no es cero: `-7 % 2` es `1` y `7 % -2` es `-1`.
- `//` y `%` con divisor cero son error de ejecución.

**Condiciones.** Comparan dos enteros. No son valores: no se pueden asignar ni imprimir.

**Sentencias.**
- `x = expr`: evalúa la expresión y la asigna a `x`.
- `print(expr)`: imprime el entero en decimal, seguido de un salto de línea.
- `if`: evalúa la condición y ejecuta el bloque que corresponde; sin `else`, si la condición es falsa no hace nada.
- `for v in range(a, b)`: evalúa `a` y luego `b`, una sola vez. Si `a >= b`, no ejecuta el cuerpo. Si no, antes de cada vuelta asigna a `v` los valores `a`, `a + 1`, …, `b - 1`. Asignar a `v` o a las variables de los límites dentro del cuerpo no cambia el número de vueltas ni el siguiente valor de `v`. Al terminar, `v` conserva el último valor asignado; si no hubo vueltas, `v` no se modifica. `range(b)` equivale a `range(0, b)`.

**Errores de ejecución.** Detienen el programa con un mensaje del lenguaje. Ningún programa, válido o no, debe producir un traceback de Python.

**Terminación.** Todo programa termina: cada `for` fija su número de vueltas antes de empezar, y no hay otra forma de repetir. Pero terminar no es terminar pronto: `x = x * x` duplica en cada vuelta los bits de `x`, y si `x` empieza en 2, cien vueltas darían un número de 2^100 bits. Agotar la memoria es error de ejecución (en Linux, el sistema operativo puede terminar el proceso antes).

## Qué etapa detecta cada error

Cada error lo detecta una etapa distinta, y saber cuál es parte de entender el lenguaje. Algunos casos, varios de ellos engañosos:

| Fragmento | Etapa | Por qué |
|---|---|---|
| `promedio = suma / 5` | léxico | `/` sola no pertenece al alfabeto; solo existe `//` |
| `x = 2.5` | léxico | el punto no pertenece al alfabeto |
| `año = 1` | léxico | las letras con acento o `ñ` no pertenecen al alfabeto |
| `x = 007` | léxico | un número no puede empezar con cero |
| sangría que regresa a un nivel que no existía | léxico | el léxico no sabe cuántos bloques cerrar |
| `2x = 4` | sintáctico | el léxico lo parte sin problema en `NUM` e `ID`; es el parser quien ve que ninguna sentencia empieza con un número |
| `elif x == 0:` | sintáctico | `elif` no es palabra reservada: llega como identificador, y el parser espera una asignación |
| `if x = 3:` | sintáctico | los tokens son válidos; el orden no |
| `if (x > 0):` | sintáctico | los paréntesis solo pueden encerrar una expresión, no una condición |
| sangría de más | sintáctico | abrir un nivel siempre es posible para el léxico; la gramática solo permite `INDENT` después de `:` |
| `print(x)` sin asignar `x` | ejecución | es válido sintácticamente; el problema solo aparece al ejecutar |
| `x // 0` | ejecución | ídem |

Cada renglón tiene un programa completo en `ejemplos/errores/`, cuyo nombre empieza con la etapa que detecta el error.

## Las pruebas (`pruebas.py`)

`pruebas.py` corre una lista de programas y compara lo que producen con lo esperado. Hay tres listas de casos:

- **`CASOS`**: se ejecutan con `interprete.py`. Cada caso es `(nombre, programa, salida esperada, comparar_con_python)`. La salida esperada es lo que el programa imprime o, si hay un error, el mensaje exacto. Si el último campo es `True`, el programa también se ejecuta con Python y debe dar lo mismo.
- **`CASOS_ARBOL`**: se ejecutan con `sintactico.py` y comparan el árbol impreso. Sirven para lo que solo se ve en el árbol, como la asociatividad.
- **`CASOS_TOK`**: se ejecutan con `lex2tok.py` y comparan el archivo `.tok` que genera.

También hay dos verificaciones fijas. La de la gramática lee `gramatica.ebnf` y comprueba que el docstring de cada método del parser coincide con la regla del mismo nombre. La otra le pasa a cada script una carpeta en lugar de un programa, y espera un mensaje, no un traceback.

Además, cualquier salida que contenga un traceback de Python cuenta como falla, aunque el caso no lo haya previsto, y cada caso tiene un límite de tiempo, para que un ciclo infinito cuente como falla en lugar de dejar colgadas las pruebas.

**Al modificar el lenguaje:**
- Agreguen sus casos al final de la lista que corresponda: al menos un programa que ahora se acepta y uno que se rechaza en cada etapa que toque su cambio.
- Si agregan o modifican una regla, actualícenla en `gramatica.ebnf` y en el docstring de su método, y registren las reglas nuevas en la lista de reglas de `pruebas.py` (los comentarios del archivo explican cómo). Si cambian la gramática sin cambiar el parser, o al revés, las pruebas lo van a detectar.
- Para obtener el árbol esperado de un caso nuevo, pueden correr `sintactico.py`, pero **revisen a mano que el árbol sea correcto** antes de copiarlo. Una prueba que copia una salida equivocada solo garantiza que el error se repita.
- Todas las pruebas, las anteriores y las suyas, deben pasar.

## Proyectos de modificación

Cada equipo hará una de las siguientes extensiones. El nivel indica la dificultad aproximada: **★** cambia el léxico o agrega una regla bastante independiente; **★★** varias reglas, alguna decisión de diseño o un conflicto que resolver; **★★★** cambia la estructura de una etapa o va más allá de lo visto con gramáticas libres de contexto.

Junto a cada extensión hay preguntas que su exposición debe responder. No son las únicas, pero sí las mínimas. En algunas extensiones el profesor indicará el alcance (por ejemplo, dónde se permiten las cadenas).

### Nivel ★

| Extensión | Preguntas que deben responder |
|---|---|
| `range(a, b, paso)` | ¿Qué pasa con un paso negativo? ¿Y con paso cero? Especifíquenlo en la semántica. |
| `while` | ¿Qué propiedad del lenguaje base se pierde (ver «Terminación»)? ¿Qué cambia en las pruebas? ¿Existe un programa de MiniPy base que imprima A(n, n), la función de Ackermann, para cualquier valor de `n` en su primera asignación? ¿Y con `while`? |
| `elif` | ¿Necesitaron un nodo nuevo en el árbol, o pudieron expresarlo con los nodos que ya existen? |
| `+=`, `-=`, `*=` | ¿En qué orden debe probar el léxico `+=` y `+`, y por qué? ¿Nodo nuevo o traducción a una `Asignacion`? |
| `print` con varios argumentos | ¿Qué imprime entre un valor y otro? ¿Cómo se escribe en la gramática una lista separada por comas? |

### Nivel ★★

| Extensión | Preguntas que deben responder |
|---|---|
| Potencia `**` | ¿Qué asociatividad tiene: cuánto vale `2 ** 3 ** 2`? ¿Cuánto vale `-2 ** 2`, y cómo lo refleja la gramática? ¿Qué hacen con un exponente negativo en un lenguaje de enteros? |
| Flotantes (`3.14`, `.5`, `2.`, `1e-3`, y el operador `/`) | ¿Qué autómata reconoce los literales? ¿Qué cambió en la gramática y qué en la semántica? ¿Qué pasa al mezclar enteros y flotantes, o al usar un flotante en `range`? |
| Cadenas | ¿Qué pasa con un `#` dentro de una cadena? ¿Qué etapa detecta una cadena sin cerrar? ¿Qué significa `"a" + 1`? |
| Funciones predefinidas (`abs`, `max`, `sqrt`) | ¿Cómo distingue el parser una variable de una llamada, si ambas empiezan con `ID`? ¿Qué devuelve `sqrt` en un lenguaje de enteros? |
| `and`, `or`, `not` | ¿Qué precedencia tienen? Al ver `(`, ¿cómo sabe el parser si empieza una expresión o una condición? ¿Siempre debe evaluarse el segundo operando? |
| Arreglos de una dimensión (`a[i]`, `a[i] = 5`, `[1, 2, 3]`) | ¿Cómo decide el parser entre `ID` seguido de `=` y de `[`? ¿Qué significan `a + 1` o `print(a)`? ¿Qué errores nuevos aparecen? |
| Arreglos de dos dimensiones (`m[i][j]`) | ¿Cómo se generaliza la gramática a n dimensiones? Después de `b = a`, ¿modificar `b` modifica `a`? Decidan y justifiquen. ¿Se permiten filas de distinto tamaño? |
| Árbol visual con Graphviz | ¿Qué información del árbol conviene mostrar y cuál omitir? |
| Tipos explícitos (`x: int = 3`) | ¿Qué hace el intérprete con la anotación? ¿Qué haría falta para verificarla? |
| Errores de ejecución con número de línea | ¿Qué información debe pasar del token al nodo del árbol? En `x + 1 // 0`, ¿qué nodo es responsable del error? |

### Nivel ★★★

| Extensión | Preguntas que deben responder |
|---|---|
| Comentarios de varias líneas | ¿Cómo se reestructura un léxico que trabaja línea por línea? ¿Qué pasa con la sangría dentro de un comentario? ¿Y con un comentario sin cerrar? Si se permiten comentarios anidados, ¿siguen siendo un lenguaje regular? |
| Funciones definidas por el usuario (`def`, parámetros, `return`) | ¿Dónde es válido `return` y cómo lo verifican? ¿Qué pasa con las variables de cada función? |
| `break` y `continue` | ¿Cómo garantizan que solo aparezcan dentro de un ciclo: en la gramática, en el parser o después? ¿Qué cuesta cada opción? ¿Qué pasa con la variable del `for` después de `continue` y de `break`? |
| Listas dinámicas (`append`, `len`, `for x in a`) | ¿Cómo distingue el parser `a[i] = 5` de `a[i].append(5)`? ¿Qué impide que `a.append(5) = 3` sea válido? ¿Hay conflicto con los flotantes? |
| Expresiones en varias líneas dentro de paréntesis | ¿Qué información necesita el léxico que parecería del parser? |
| Recuperación de errores (reportar más de uno) | ¿En qué tokens se puede sincronizar? ¿Cómo evitan reportar errores en cascada? |
| Generar el parser con una herramienta (Lark, ANTLR) | ¿Qué cambió al pasar la gramática a la notación de la herramienta? ¿Cómo maneja la sangría? ¿Qué se gana y qué se pierde frente al parser escrito a mano? |
| El intérprete en otro lenguaje (C, Java) | ¿Cómo cumplen la semántica de `//` y `%` si el otro lenguaje redondea distinto? ¿Y el tamaño de los enteros? |
| Análisis semántico | ¿Se puede saber antes de ejecutar que una variable podría no tener valor? ¿Qué hacen cuando depende de si un `for` llega a ejecutarse? |

## Qué entrega cada equipo

Todos los equipos entregan los mismos cinco elementos, sin importar la extensión:

1. **Especificación**, antes de programar: qué programas nuevos acepta el lenguaje y qué hacen, en el estilo de «Semántica de MiniPy». Si introduce operadores, su precedencia y asociatividad. También el comportamiento en casos límite y los errores que puede producir.
2. **Gramática**: `gramatica.ebnf` modificado, y la explicación de qué reglas son nuevas o cambiaron y por qué.
3. **Implementación**: los cambios en el léxico, el parser, el árbol y el intérprete, según corresponda. Si cambiaron el intérprete, qué significado nuevo agregaron; si no fue necesario, por qué.
4. **Pruebas**: sus casos nuevos en `pruebas.py` y la suite completa pasando, sin tracebacks.
5. **Análisis de la decisión**: qué alternativas consideraron, por qué eligieron la suya y qué limitaciones quedan.

La especificación y la gramática se entregan primero, antes del código, para poder revisar el diseño cuando todavía es fácil cambiarlo.

**La exposición.** Cada equipo presenta su gramática antes y después, programas que ahora se aceptan y que se rechazan, y responde las preguntas de su extensión. Cualquier integrante del equipo puede ser llamado a explicar cualquier parte del trabajo.

**Pruebas cruzadas.** Antes de exponer, cada equipo recibirá la implementación de otro equipo e intentará encontrarle fallas: programas que deberían aceptarse y no se aceptan, que deberían rechazarse y no se rechazan, o que producen un traceback. Escriban sus pruebas pensando en que alguien más va a buscar lo que se les escapó.

**Uso de inteligencia artificial.** Se permite, pero ustedes responden por el resultado. Entreguen una bitácora breve: qué le pidieron, en qué se equivocó y cómo lo detectaron. Encontrar los errores de la IA cuenta a su favor.

## Recomendaciones prácticas

- Trabajen sobre su propia copia de los archivos. Si usan Git, el `git diff` contra la versión original es una excelente forma de mostrar exactamente qué cambiaron.
- Guarden los archivos en UTF-8. Un archivo en otra codificación se reporta como error léxico.
- No copien código desde la presentación o desde un PDF: se cuelan caracteres invisibles o parecidos a los normales. El léxico los detecta, pero es mejor evitarlos.
- Escriban los nombres de archivo en minúsculas. Windows no distingue mayúsculas en los nombres de archivo y Linux sí, así que un archivo que funciona en una computadora puede fallar en otra.
- Si una prueba falla después de un cambio, no la "arreglen" cambiando la salida esperada sin entender por qué cambió.
