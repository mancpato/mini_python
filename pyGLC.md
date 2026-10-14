
# Gramática para un python mínimo

## ¿Ya existe algo así?

Hay cosas parecidas, pero ninguna tan pequeña:

- **ChocoPy** (Universidad de Berkeley, curso CS164) es un subconjunto de Python con tipos estáticos, pensado justamente para cursos de compiladores. Está muy bien documentado, pero incluye clases, listas, cadenas y funciones, así que es demasiado grande para revisarlo en una sola clase.
- **Mini-Python** (Jean-Christophe Filliâtre, curso de compilación en Francia) es más pequeño, pero sigue teniendo listas, cadenas y funciones definidas por el usuario.
- La **gramática oficial de Python** (PEG, en la documentación del lenguaje) es la referencia, pero tiene cientos de reglas.

La que se presenta a continuación es muy reducida. Sólo escribe código en la función main (no llama a funciones) y sólo tiene variables enteras. Usa sentencias for e if.

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
NUM ::= "0" | digito_no_cero { digito }
OPREL   ::= "==" | "!=" | "<" | "<=" | ">" | ">="
Reservadas: def main if else for in range print
NEWLINE, INDENT, DEDENT  (los genera el analizador léxico)
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
```

## Decisiones de diseño que vale la pena comentar en clase

**Sangría como tokens.** Es lo más interesante pedagógicamente. La gramática no menciona espacios: el analizador léxico lleva una pila de niveles de sangría y emite `INDENT` o `DEDENT` cuando cambia. Así la gramática queda libre de contexto y parece la de un lenguaje con llaves, donde `INDENT` equivale a `{` y `DEDENT` a `}`. De paso desaparece el problema del *else colgante*, porque la sangría deja claro a qué `if` pertenece cada `else`.

**Condiciones solo relacionales.** Al exigir `expr OPREL expr` se evita introducir un tipo booleano, así que todo el lenguaje sigue siendo solo de enteros. Por eso no hay `and`, `or` ni `not`; si los quieres después, son una buena ampliación como ejercicio.

**División entera `//`.** Se usa en lugar de `/` porque en Python `/` devuelve flotante, lo que rompería la restricción a enteros.

**Precedencia codificada en la gramática.** La cascada `expr → termino → factor` hace que `*` gane sobre `+` sin reglas adicionales, y el `-` unario en `factor` permite escribir `-x`.

**Es LL(1).** No tiene recursión por la izquierda (usa repeticiones `{ }`) y cada alternativa de `sentencia` empieza con un token distinto, excepto `asignacion`, que empieza con `ID` y no choca con ninguna otra. Se puede implementar directamente como analizador descendente recursivo, con una función por regla.

**`print` incluido.** Técnicamente no hace falta, pero sin él los programas no producen salida observable, y eso dificulta probar un intérprete.

## Detalle práctico

En Python real, el programa anterior no hace nada, porque `main` nunca se invoca. Si quieres que todo programa válido en tu lenguaje también funcione en Python, agrega una línea final obligatoria:

```
programa ::= "def" "main" "(" ")" ":" bloque "main" "(" ")" NEWLINE
```

Así los alumnos pueden verificar sus resultados ejecutando el mismo archivo con el intérprete oficial.

Si te sirve, puedo escribir el analizador léxico (con el manejo de `INDENT`/`DEDENT`) y el analizador descendente recursivo en Python, en unas 150 líneas, para mostrarlo junto con la gramática.

## Proyectos de modificación:

Antes de la lista, una corrección a tus ejemplos: los comentarios de una línea con `#` ya funcionan, porque `lexico.py` corta cada línea en el primer `#`. Pero eso se vuelve un problema interesante en cuanto alguien agregue cadenas, como explico más abajo.

Clasifiqué las mejoras en tres niveles según cuánto tocan del código y qué tan lejos llevan de lo visto en clase: **★** cambia solo el léxico o agrega una regla independiente; **★★** varias reglas, alguna decisión de diseño o un conflicto que resolver; **★★★** cambia la estructura de una etapa o requiere conceptos más allá de las GLC.

## Nivel ★

| Mejora | Qué cambia | Por qué es interesante |
|---|---|---|
| `range(a, b, paso)` | Una alternativa en `para` | Buen calentamiento para entender el código |
| `while` | Una regla nueva | Muestra lo fácil que es crecer cuando la gramática es LL(1) |
| `elif` | Una regla y una palabra reservada | Corrige el mensaje confuso del ejemplo de error 4 |
| `+=`, `-=`, `*=` | Tokens nuevos y una alternativa en `asignacion` | El léxico debe probar `+=` antes que `+` |
| `print` con varios argumentos | Lista separada por comas | Patrón de lista que se reutiliza en funciones |
|
## Nivel ★★

| Mejora | Qué cambia | Por qué es interesante |
|---|---|---|
| **Potencia `**`** | Nuevo nivel de precedencia | Es asociativa por la derecha (`2**3**2` = `2**9`) y además `-2**2` vale `-4`, así que hay que reacomodar el menos unario. Excelente para precedencia y asociatividad |
| **Flotantes** | Léxico: `3.14`, `.5`, `2.`, `1e-3`; gramática: casi nada | El autómata del léxico es lo valioso. La gramática apenas cambia, y descubren que mezclar enteros y flotantes es un problema semántico, no sintáctico |
| **Cadenas** | Léxico: comillas, escapes, cadena sin cerrar | Rompe los comentarios: hoy `print("a#b")` se corta en el `#`. El léxico debe saber si está dentro de una cadena. Además hay que decidir dónde se permiten: ¿solo en `print`, o también `"a" + "b"`? |
| **Funciones predefinidas** (`abs`, `max`, `sqrt`) | `factor ::= ID [ "(" args ")" ]` | Si la escriben como dos alternativas que empiezan con `ID`, deja de ser LL(1). Ejemplo perfecto de factorización por la izquierda |
| **`and`, `or`, `not`** | Varios niveles de precedencia en condiciones | Aparece un conflicto real: al ver `(`, el parser no sabe si abre una expresión o una condición. Se resuelve unificando expresiones y condiciones, como hace Python |
| Arreglos (`a[i]`, `a[i] = 5`) | Asignación y factor con índice | Otra vez factorización: `ID` puede ir seguido de `=` o de `[` |
| Árbol visual con Graphviz | Genera un `.dot` desde el AST | Muy útil para todo el grupo: las demás mejoras se ven mejor en el árbol |
| Tipos explícitos (`x: int = 3`) | Una alternativa en `asignacion` | Prepara el terreno para verificación de tipos |

## Nivel ★★★

| Mejora | Qué cambia | Por qué es interesante |
|---|---|---|
| **Comentarios multilínea** | El léxico trabaja línea por línea y hay que reestructurarlo | Una línea dentro del comentario no debe generar `INDENT`, y un comentario sin cerrar debe reportarse al final. Si se permiten anidados, ya no son un lenguaje regular: requieren un contador. Conecta directamente con la jerarquía de Chomsky |
| **Funciones definidas por el usuario** | `programa ::= { funcion }`, parámetros, `return` | Deja de existir solo `main`. `return` fuera de una función es otra restricción contextual, y aparecen las variables locales |
| **`break` y `continue`** | Gramática trivial | Solo son válidos dentro de un ciclo, y eso no se expresa bien en una GLC: o se duplican reglas (`sentencia_en_ciclo`) o se verifica después. Introduce la noción de restricción dependiente del contexto |
| Expresiones en varias líneas dentro de paréntesis | El léxico cuenta paréntesis abiertos y suprime `NEWLINE` | El léxico necesita información que parece sintáctica; cuestiona la separación limpia de etapas |
| Recuperación de errores | Reportar más de un error (modo pánico) | Hoy el parser se detiene en el primero. Sincronizar en `NEWLINE` o `DEDENT` es elegante pero sutil |
| Generar el parser con una herramienta (Lark, ANTLR) | Escribir la gramática en la notación de la herramienta | Comparan el parser escrito a mano con uno generado. Lark trae soporte para sangría al estilo Python |
| **Intérprete** | Recorrer el AST y evaluar | Unas 50 líneas. Convierte todo en algo ejecutable, y obliga a decidir la semántica de `//` con negativos y del `for` |
| Análisis semántico | Tabla de símbolos | Detectar variables usadas sin asignar, o tipos incompatibles si alguien agregó flotantes o cadenas |

## Sugerencias para organizar los equipos

Algunas mejoras chocan entre sí. Cadenas y comentarios tocan la misma parte del léxico; `and`/`or` y funciones predefinidas modifican `factor`; flotantes y potencia cambian la precedencia. Conviene que cada equipo trabaje sobre su propia copia de la versión base, y quizá al final proponer como reto unir dos mejoras.

También vale la pena considerar que el intérprete lo haga un equipo temprano, o dárselo tú desde el inicio. Sin él, agregar flotantes o cadenas solo se nota en el AST, y las presentaciones lucen poco. Con él, cada equipo puede mostrar un programa que antes no corría y ahora sí.

Por último, pide que cada equipo presente tres cosas: la gramática antes y después, un programa que ahora se acepta y uno que se rechaza en cada etapa. Así cada presentación refuerza la diferencia entre léxico y sintaxis, que es justo lo que están aprendiendo.
