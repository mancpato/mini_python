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
- **Ceros a la izquierda** (léxico). `007` es inválido en Python 3. Por eso la definición de `NUM` los excluye (ver pendientes: el código aún no lo verifica).
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
ID      ::= letra { letra | digito | "_" }    (excepto palabras reservadas)
NUM     ::= "0" | digito_no_cero { digito }
OPREL   ::= "==" | "!=" | "<" | "<=" | ">" | ">="
Reservadas: def main if else for in range print
NEWLINE, INDENT, DEDENT  (los genera el analizador léxico)
Comentarios: desde "#" hasta el fin de línea (el léxico los descarta)
```

Son 10 reglas sintácticas y un puñado de tokens.

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

**División entera `//`.** Se usa en lugar de `/` porque en Python `/` devuelve flotante, lo que rompería la restricción a enteros.

**Precedencia codificada en la gramática.** La cascada `expr → termino → factor` hace que `*` gane sobre `+` sin reglas adicionales, y el `-` unario en `factor` permite escribir `-x`. Las repeticiones `{ }` dan asociatividad por la izquierda.

**Es LL(1).** No tiene recursión por la izquierda (usa repeticiones `{ }`) y cada alternativa de `sentencia` empieza con un token distinto, excepto `asignacion`, que empieza con `ID` y no choca con ninguna otra. Se puede implementar directamente como analizador descendente recursivo, con una función por regla.

**`print` incluido.** Técnicamente no hace falta, pero sin él los programas no producen salida observable, y eso dificulta probar un intérprete.

## Implementación

Tres etapas separadas, cada una ejecutable por sí misma:

```
python lexico.py ejemplo.py       # lista de tokens
python sintactico.py ejemplo.py   # árbol de sintaxis abstracta (AST)
python interprete.py ejemplo.py   # ejecuta el programa
```

### `lexico.py` (~120 líneas)

Trabaja línea por línea en tres pasos:

1. Mide la sangría y emite `INDENT`/`DEDENT` comparando con una pila de niveles. Si la sangría baja a un nivel que no está en la pila, es error léxico. Rechaza tabuladores.
2. Reconoce los lexemas del resto de la línea. Las palabras reservadas se distinguen de los identificadores con una búsqueda en un conjunto. Los operadores de dos caracteres se prueban antes que los de uno (si no, `//` se leería como dos `/`).
3. Al terminar el archivo, cierra con `DEDENT` los bloques abiertos y emite `EOF`.

Quita los comentarios cortando cada línea en el primer `#`.

### `sintactico.py` (~200 líneas)

Analizador descendente recursivo con la gramática en el encabezado y una función por regla con el mismo nombre, para leerlas lado a lado. Todo descansa en dos utilidades: `ver()` mira el token actual sin consumirlo y `consumir()` lo exige o lanza el error. Construye un AST con `dataclasses` y lo imprime con sangría.

Decisiones del código:
- `range(n)` se normaliza a `range(0, n)` en el árbol.
- La llamada final `main()` es **opcional** en el código (ver pendientes).

### `interprete.py` (~60 líneas)

Recorre el AST. `ejecutar()` procesa listas de sentencias y no devuelve nada; `evaluar()` calcula el valor de expresiones y condiciones. Las variables viven en un diccionario. `BinOp` y `Condicion` tienen la misma forma (operador, izquierda, derecha), así que se resuelven con una sola tabla de operaciones; las condiciones devuelven `True` o `False`. Reporta dos errores de ejecución: variable sin valor y división entre cero.

**Semántica prestada.** El intérprete toma la semántica de Python en tres puntos sin que nadie la haya decidido explícitamente:
- `-7 // 2` da `-4` (redondea hacia menos infinito; en C daría `-3`). Igual con `%`.
- El `for` usa el `range` de Python: los límites se evalúan una vez y modificar la variable o el límite dentro del cuerpo no altera las iteraciones (a diferencia del `for` de C).
- Los enteros no tienen límite de tamaño.

Si un equipo escribiera el intérprete en C o Java, tendría que decidir estos tres puntos. Es buena discusión sobre dónde está definido el significado de un lenguaje.

**Limitación.** Los errores de ejecución no reportan línea, porque el AST no guarda posiciones.

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
| `range(a, b, paso)` | Una alternativa en `para` | Buen calentamiento para entender el código | Sí (campo `paso`) |
| `while` | Una regla nueva | Muestra lo fácil que es crecer cuando la gramática es LL(1) | Sí |
| `elif` | Una regla y una palabra reservada | Corrige el mensaje confuso del ejemplo de error 4 | Depende |
| `+=`, `-=`, `*=` | Tokens nuevos y una alternativa en `asignacion` | El léxico debe probar `+=` antes que `+` | Depende |
| `print` con varios argumentos | Lista separada por comas | Patrón de lista que se reutiliza en funciones | Sí |

### Nivel ★★

| Mejora | Qué cambia | Por qué es interesante | Intérprete |
|---|---|---|---|
| **Potencia** (`**`) | Nuevo nivel de precedencia | Es asociativa por la derecha (`2**3**2` = `2**9`) y además `-2**2` vale `-4`, así que hay que reacomodar el menos unario. Excelente para precedencia y asociatividad | Sí (una línea) |
| **Flotantes** | Léxico: `3.14`, `.5`, `2.`, `1e-3`; gramática: casi nada | El autómata del léxico es lo valioso. La gramática apenas cambia, y descubren que mezclar enteros y flotantes es un problema semántico, no sintáctico | Casi nada (hereda Python) |
| **Cadenas** | Léxico: comillas, escapes, cadena sin cerrar | Rompe los comentarios: hoy `print("a#b")` se corta en el `#`. **Especificar el alcance:** solo en `print` es ★★; si se permite `"a" + "b"` aparecen los tipos y se vuelve semántico | Sí (`"a" + 1` produce un traceback de Python) |
| **Funciones predefinidas** (`abs`, `max`, `sqrt`) | `factor ::= ID [ "(" args ")" ]` | Si la escriben como dos alternativas que empiezan con `ID`, deja de ser LL(1). Ejemplo perfecto de factorización por la izquierda | Sí |
| **`and`, `or`, `not`** (limítrofe con ★★★) | Varios niveles de precedencia en condiciones | Conflicto real: al ver `(`, el parser no sabe si abre una expresión o una condición. Se resuelve unificando expresiones y condiciones en una sola jerarquía, como Python; es un cambio grande | Sí (cortocircuito) |
| Arreglos (`a[i]`, `a[i] = 5`) | Asignación y factor con índice | Otra vez factorización: `ID` puede ir seguido de `=` o de `[` | Sí |
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
| Intérprete en otro lenguaje (C, Java) | Reescribir `interprete.py` | Obliga a definir explícitamente la semántica de `//`, `%`, el `for` y el tamaño de los enteros | — |
| Análisis semántico | Tabla de símbolos | Detectar variables usadas sin asignar, o tipos incompatibles si alguien agregó flotantes o cadenas | No (etapa nueva) |

## Azúcar sintáctica: ¿cuándo cambia el intérprete?

El intérprete solo cambia cuando la mejora agrega un **significado nuevo**. Si lo nuevo puede expresarse con los nodos que ya existen en el AST, el parser hace la traducción y el intérprete no se entera. Eso es azúcar sintáctica.

- **No lo tocan:** comentarios multilínea, paréntesis en varias líneas, bloques en una línea, recuperación de errores. Los números en otras bases o con separadores (`0x1F`, `1_000`) producen el mismo `Num`; basta `int(valor, 0)` en el parser. Graphviz o un formateador son módulos nuevos que leen el AST.
- **Depende del diseño:** `x += 1` puede traducirse a `Asignacion("x", BinOp("+", Var("x"), Num(1)))`; `elif` a un `Si` anidado en el `sino`. Si el equipo crea nodos nuevos, debe modificar el intérprete. Ambas opciones son válidas; preguntar cuál eligió y por qué es buena pregunta de exposición.
- **Sí lo tocan:** todo lo que agrega comportamiento. Algunos casos engañosos:
  - Potencia y flotantes son casi gratis porque Python ya sabe hacerlo: otra vez semántica heredada.
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

## Organización de los equipos

Algunas mejoras chocan entre sí. Cadenas y comentarios tocan la misma parte del léxico; `and`/`or` y funciones predefinidas modifican `factor`; flotantes y potencia cambian la precedencia. Cada equipo trabaja sobre su propia copia de la versión base, y al final puede proponerse como reto unir dos mejoras.

El intérprete se entrega desde el inicio junto con el léxico y el sintáctico. Así cada equipo puede mostrar un programa que antes no corría y ahora sí.

Al asignar mejoras limítrofes (cadenas, `and`/`or`), especificar el alcance para que la dificultad sea la pretendida.

## Evaluación

Cada equipo presenta:
- La gramática antes y después.
- Un programa que ahora se acepta y uno que se rechaza en cada etapa.
- Si su mejora cambió el intérprete y por qué.

Como usarán IA, conviene evaluar lo que la IA no puede hacer por ellos durante la exposición: explicar, predecir y defender decisiones.

- **Pruebas cruzadas.** Antes de exponer, cada equipo entrega sus analizadores a otro, que intenta romperlos con programas que deberían aceptarse y no se aceptan, o al revés. Cada falla encontrada suma puntos al equipo atacante. Los defensores pueden corregir y explicar el error en su exposición.
- **Predecir antes de ejecutar.** El equipo muestra un programa y el grupo vota si se acepta y, si no, en qué etapa y línea falla. Luego se ejecuta. Evalúa también a la audiencia.
- **Preguntas a un integrante al azar.** "¿Qué pasa si intercambias el orden de estas dos alternativas?", "¿por qué esta regla no genera conflicto?", "¿por qué este error es léxico y no sintáctico?". Mide si el trabajo fue de todo el equipo.
- **Derivación a mano.** Árbol de derivación en el pizarrón de un programa corto con su mejora, comparado con el AST del analizador. Las diferencias (el de derivación tiene `expr`, `termino`, `factor`; el AST no) llevan a discutir árbol concreto contra abstracto.
- **Bitácora de uso de IA.** Qué le pidieron a la IA y, sobre todo, en qué se equivocó y cómo lo detectaron. Dar puntos por errores de la IA encontrados cambia el incentivo: conviene demostrar que la supervisaron. Con gramáticas es común que la IA proponga recursión por la izquierda o conflictos LL(1) sin advertirlo.
- **Gramática primero.** Entrega previa de la gramática modificada, antes del código. Permite revisar el diseño cuando todavía es barato cambiarlo.
- **El diff como material de exposición.** Mostrar el `git diff` contra la versión base y justificar cada cambio. Un cambio pequeño y limpio refleja mejor comprensión que reescribir medio archivo.
- **Reto final de integración.** Juntar dos mejoras que choquen (cadenas con comentarios, `and`/`or` con funciones predefinidas).

Si solo se eligen dos: pruebas cruzadas (calidad del trabajo) y preguntas al azar (comprensión individual).

## Pendientes

- **`main()` final:** la gramática lo exige, pero `sintactico.py` lo acepta como opcional. Decidir y alinear. (Ya que es un lenguaje separado, podría eliminarse de la gramática.)
- **Ceros a la izquierda:** la gramática excluye `007`, pero `lexico.py` lo acepta. Agregar la verificación o relajar la definición de `NUM`.
- **Definición de `letra`:** el léxico usa `isalpha()`, que acepta letras acentuadas (`año`) y otros caracteres Unicode. Decidir si `letra` es solo ASCII.
