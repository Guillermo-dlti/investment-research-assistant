# Course assignment and team context

This file keeps the original course brief and the teammate handoff message, word for word, so every person and AI tool on the project works from the same source. The brief is the grading source of truth.

## Quick summary (English)

- **Goal**: question → search → retrieve chunks → select context → Hugging Face model → answer.
- **Stages**: 1 documents and chunking, 2 preprocessing and index structure, 3 exact search (KMP, Z function), 4 approximate search (at least two techniques), 5 context selection and LLM answers (at least 20 questions shown), 6 exact vs approximate comparison.
- **Deliverables**: code, a report (no code inside it), and a short demo video of the app in use.
- **Bonus (10 points on the first exam)**: a GUI app with a question window that autocompletes words using a Trie. Only counts if the whole project is complete. Exam capped at 100 points.
- **Team split**: Stages 1 to 3 done by teammate. Stage 4 is next (Levenshtein, n grams, Jaccard in C++, wired into the search engine), then Stage 5 and Stage 6.

## Teammate handoff message (original, Spanish)

Hey, ya terminé las primeras 3 etapas del proyecto de Algoritmos Avanzados y dejé todo subido a GitHub.

También hice un documento que se llama `reports/DEVELOPER_HANDOFF.md`, donde viene explicado todo lo que hemos desarrollado, la arquitectura, cómo configurar el proyecto, los algoritmos, las pruebas y lo que falta por hacer.

**Lo que ya está terminado:**

- **Stage 1:** Descarga y procesamiento de 10 reportes financieros de NVIDIA, AMD, Microsoft, Apple y Google.
- **Stage 2:** Normalización de texto, Trie e Inverted Index implementados en C++, e integración con Python.
- **Stage 3:** KMP y Z-function en C++, búsqueda exacta, ranking, filtros y benchmarks comparando ambos algoritmos.

Todo funciona y pasaron las 139 pruebas automatizadas (56 de C++ y 83 de Python).

**A ti te tocaría continuar desde Stage 4: Approximate String Matching**, donde tenemos que implementar Levenshtein Distance, n-grams y Jaccard Similarity, y conectarlos con el motor de búsqueda que ya tenemos.

Después todavía faltan Stage 5 (integración con Hugging Face) y Stage 6 (evaluación final).

Te recomiendo que primero clones el repositorio y leas el `DEVELOPER_HANDOFF.md` antes de empezar a programar.

Una cosa importante: los documentos financieros y los JSON generados no se suben a GitHub porque están en el `.gitignore`. En el handoff vienen los comandos para generarlos en tu computadora.

También tienes que configurar Python, compilar C++ y comprobar que pasen las pruebas antes de empezar Stage 4.

Si vas a usar Codex, dale el handoff como contexto para que entienda lo que ya está implementado y no cambie cosas que funcionan.

La idea es seguir haciendo los algoritmos en C++ y utilizar Python para integrarlos con la aplicación.

## Course brief (original, Spanish)

### Instrucciones

Desarrolla el siguiente proyecto que involucra la manipulación de strings. Al final de esta sección, se dan las indicaciones de los entregables, y los requisitos mínimos para la entrega.

### Proyecto: Recuperación de información para un asistente basado en modelos de lenguaje

En la actualidad, los modelos de lenguaje de gran escala pueden responder preguntas y generar texto a partir de la información que reciben como contexto. Sin embargo, cuando la información disponible se encuentra distribuida entre documentos extensos, no siempre es posible proporcionar todo el contenido directamente al modelo. Antes de formular una respuesta es necesario localizar, seleccionar y organizar los fragmentos que contienen la información más relevante para la consulta realizada.

Este problema combina técnicas modernas de inteligencia artificial con problemas clásicos de búsqueda y procesamiento de cadenas. En este proyecto construirás una herramienta que, dada una colección de documentos y una pregunta realizada por el usuario, busque los fragmentos de texto más relacionados con la consulta, seleccione los más relevantes y los utilice como contexto para un modelo de lenguaje preentrenado. El propósito es analizar cómo diferentes algoritmos de búsqueda y comparación de cadenas afectan tanto la eficiencia de la recuperación como la calidad de la información proporcionada al modelo.

### Etapa 1 - Selección y preparación de documentos

En esta primera etapa deberás elegir una colección de documentos que utilizarás como fuente de información durante el proyecto. Puedes trabajar, por ejemplo, con novelas, artículos, manuales, documentación técnica o cualquier conjunto de textos que permita realizar preguntas sobre su contenido. Se recomienda utilizar documentos suficientemente extensos para que la búsqueda de información sea necesaria y preferentemente materiales de dominio público.

Anota en tu reporte:

- El nombre y descripción general de los documentos utilizados.
- La fuente de donde los obtuviste.
- La extensión aproximada de la colección en palabras o caracteres.
- Una breve justificación de tu elección, explicando qué tipo de preguntas esperas poder realizar sobre el contenido.

Debido a que los modelos de lenguaje no pueden recibir cantidades ilimitadas de texto, deberás además dividir los documentos en fragmentos o bloques que puedan ser recuperados posteriormente. Puedes utilizar párrafos, grupos de párrafos o bloques de tamaño aproximadamente constante.

Reporta el criterio que utilizaste para realizar esta división y la cantidad de fragmentos obtenidos.

El propósito de esta etapa es construir la colección de fragmentos de texto sobre la cual se realizarán posteriormente las búsquedas.

### Etapa 2 - Preprocesamiento e indexación del texto

Antes de realizar las búsquedas, será necesario preparar los textos para facilitar su comparación. Investiga qué técnicas de preprocesamiento pueden resultar útiles y aplica al menos dos de ellas.

Algunas opciones posibles son:

- Convertir el contenido a minúsculas.
- Eliminar signos de puntuación y caracteres especiales.
- Separar los fragmentos en palabras o tokens.
- Eliminar palabras muy frecuentes o stopwords.
- Normalizar palabras eliminando acentos o variaciones simples.
- Construir una lista de las palabras únicas presentes en la colección.

Además, deberás construir al menos una estructura que facilite posteriormente la búsqueda de información. Algunas posibilidades son:

- Un arreglo de sufijos o árbol de sufijos.
- Un Trie para almacenar el vocabulario de la colección.
- Una tabla de hashing para almacenar términos o n-gramas.
- Una lista ordenada que permita realizar búsquedas eficientes.

Tu reporte deberá explicar qué técnicas de preprocesamiento y qué estructura utilizaste, justificando tus decisiones y analizando la complejidad de construcción y almacenamiento.

### Etapa 3 - Recuperación mediante búsqueda exacta

En esta etapa implementarás un primer mecanismo para recuperar información utilizando búsquedas exactas de cadenas.

A partir de una pregunta realizada por el usuario, deberás identificar las palabras o expresiones importantes y buscar su aparición dentro de los fragmentos de la colección. Para realizar estas búsquedas deberás utilizar al menos dos de los algoritmos vistos en clase, por ejemplo:

- KMP (Knuth–Morris–Pratt)
- Z-function

Tu sistema deberá asignar una puntuación a cada fragmento de acuerdo con la cantidad o importancia de las coincidencias encontradas y devolver los fragmentos con mayor puntuación.

Por ejemplo, dada una consulta como:

> ¿Qué se menciona sobre programación dinámica y caminos más cortos?

el programa deberá localizar los fragmentos donde aparecen términos relacionados con la consulta y ordenarlos de acuerdo con algún criterio definido por ti.

Deberás reportar:

- Los términos o patrones utilizados para realizar la búsqueda.
- Los fragmentos recuperados.
- La puntuación asignada a cada fragmento.
- El tiempo necesario para realizar la búsqueda.
- La complejidad del algoritmo utilizado.

Comenta brevemente los resultados obtenidos y las principales limitaciones de realizar únicamente búsquedas exactas.

### Etapa 4 - Recuperación mediante búsqueda aproximada

Las preguntas realizadas por un usuario no necesariamente utilizarán exactamente las mismas palabras que aparecen en los documentos. Además, pueden existir errores de escritura, variaciones de palabras o expresiones parcialmente coincidentes.

En esta etapa deberás incorporar un segundo mecanismo de recuperación que permita realizar búsquedas aproximadas.

Deberás implementar al menos dos técnicas. Algunas opciones son:

- Búsqueda aproximada utilizando un Trie.
- Comparación mediante subsecuencias o substrings comunes.
- Distancia de edición (Levenshtein) para localizar palabras similares.
- n-gramas y similitud de Jaccard para comparar fragmentos de texto.
- Algún otro algoritmo de cadenas que consideres adecuado.

Tu sistema deberá utilizar esta información para volver a calcular la relevancia de los fragmentos y producir un nuevo ordenamiento.

Deberás reportar:

- Los algoritmos utilizados.
- La forma en que calculaste la similitud.
- Los fragmentos recuperados.
- Los tiempos de ejecución.
- Las diferencias observadas respecto a la búsqueda exacta.

Explica brevemente en qué situaciones la búsqueda aproximada mejora los resultados y en cuáles puede introducir coincidencias poco útiles.

### Etapa 5 - Selección del contexto e integración con un modelo de lenguaje

Hasta este punto, tu programa será capaz de encontrar fragmentos relacionados con una consulta. En esta etapa utilizarás estos resultados para construir el contexto que será proporcionado a un modelo de lenguaje preentrenado.

El modelo de lenguaje será alguno disponible en Hugging Face, y no será necesario entrenarlo. Su función será únicamente generar una respuesta a partir de la pregunta realizada y los fragmentos seleccionados por tu algoritmo. Para ver un ejemplo de uso de modelo pequeño, consulta este cuaderno de Jupiter (Descargar cuaderno de Jupiter).

Debido a que la cantidad de información que puede recibir el modelo es limitada, deberás seleccionar únicamente una parte de los fragmentos recuperados.

Puedes utilizar estrategias como:

- Seleccionar los k fragmentos con mayor puntuación.
- Establecer un límite máximo de palabras o tokens.
- Eliminar fragmentos redundantes.
- Priorizar fragmentos que contengan varios términos de la consulta.

El flujo general del programa deberá ser:

Pregunta → búsqueda → recuperación de fragmentos → selección del contexto → modelo de lenguaje → respuesta

Deberás mostrar al menos veinte preguntas realizadas al sistema e incluir para cada una:

- La pregunta realizada.
- Los fragmentos seleccionados como contexto.
- La respuesta generada por el modelo.
- El tiempo utilizado para recuperar la información.

Analiza si la respuesta generada está respaldada por los fragmentos seleccionados y comenta qué ocurre cuando la recuperación proporciona información incompleta o poco relacionada.

### Etapa 6 - Comparación y análisis de resultados

Finalmente, deberás evaluar cómo las diferentes estrategias de búsqueda afectan tanto la recuperación de información como las respuestas producidas por el sistema.

Selecciona un conjunto de preguntas de prueba y compara al menos:

- La búsqueda exacta desarrollada en la Etapa 3.
- La búsqueda aproximada desarrollada en la Etapa 4.

Para cada estrategia reporta:

- El tiempo promedio de búsqueda.
- La cantidad de fragmentos examinados o recuperados.
- La calidad o utilidad de los fragmentos seleccionados.
- El comportamiento final del modelo de lenguaje.

Incluye casos donde ambos métodos produzcan resultados similares y casos donde exista una diferencia importante.

En tu análisis explica:

- Qué algoritmo ofrece búsquedas más rápidas.
- Qué método recupera información más útil para las preguntas realizadas.
- Cómo afecta el tamaño de la colección al tiempo de búsqueda.
- Cómo afecta la selección del contexto a la respuesta generada por el modelo.
- Qué ventajas y limitaciones tiene utilizar algoritmos clásicos de cadenas para recuperar información destinada a un modelo de lenguaje.

Puedes complementar el análisis con tablas, gráficas, fragmentos recuperados o capturas de la aplicación.

Con esta etapa concluirás mostrando cómo la eficiencia y calidad de los algoritmos de búsqueda influyen directamente en la información que recibe un modelo de lenguaje y, por lo tanto, en las respuestas que puede generar.

### Entregables

Los entregables de este proyecto son el código desarrollado, un reporte, y un video explicativo. El código se debe subir a esta plataforma. En el reporte, no se debe incluir código.

#### Reporte

El reporte debe contener lo siguiente:

- Introducción de la problemática a resolver.
- El desarrollo de todas las etapas del proyecto, junto con las respuestas a los planteamientos indicados en las instrucciones.
- Explicación de cada algoritmo implementado, indicando las técnicas de diseño que están detrás de los algoritmos y el análisis de su complejidad algorítmica.
- Conclusiones personales.

#### Video

Preparen un video corto en el que se muestre el uso de su aplicación desarrollada, explicando su funcionalidad. No es necesario explicar algoritmos ni código, es un video que demuestre cómo se utiliza su aplicación y cómo se ven los resultados.

**NOTA 1:** Para 10 puntos en el primer examen, deberás desarrollar una aplicación con GUI, y una ventana donde realices preguntas con capacidades de autocompletado de palabras. El autocompletado debe estar implementada con una TRIE. Esto está sujeto a que el proyecto esté completo con todas las funcionalidades solicitadas.

**NOTA 2:** El examen está topado a 100 puntos.
