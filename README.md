# Inversión Acústico-Articulatoria con Algoritmos Genéticos y Análisis Espectral (FFT)

## ¿De qué trata este proyecto?

Este proyecto busca **reconstruir los movimientos de la garganta, la lengua y la boca a partir de un audio de voz** usando un **algoritmo genético** y un **simulador físico del tracto vocal** (inspirado en *Pink Trombone*).

En términos sencillos: si le das al programa un audio corto de voz —por ejemplo, alguien pronunciando la vocal `/a/`—, el sistema probará secuencias de posiciones de la lengua y tonos de voz, comparará qué tan parecido suena el resultado en frecuencia respecto al audio original y hará "evolucionar" las mejores opciones hasta imitarlo, mostrando gráficamente cómo se mueve el tracto vocal y reproduciendo el audio generado.

---

## Conceptos clave explicados de forma simple

Aunque el proyecto mezcla áreas técnicas, la idea central es intuitiva si se divide en piezas:

### 1. Síntesis articulatoria y tracto vocal 1D
* **Qué significa:** En lugar de grabar una voz humana o usar un archivo MP3 pregrabado, el sonido se genera simulando físicamente cómo vibra el aire dentro de un tubo que representa el tracto vocal (desde la garganta/glotis hasta los labios).
* **Ejemplo cotidiano:** Piensa en soplar por un tubo o modificar la forma de tu boca al decir *"o"* o *"a"*. Cambiar dónde se estrecha el tubo cambia qué frecuencias resuenan más y qué vocal se escucha. En un modelo 1D simplificado, ese conducto se divide en segmentos y se controla con unos pocos parámetros clave (como posición y estrechamiento de la lengua, apertura de la boca/labios y frecuencia fundamental o tono de voz).

### 2. Inversión Acústico-Articulatoria (*Acoustic-to-Articulatory Inversion*)
* **Qué significa:** Normalmente, un simulador de voz toma **movimientos** y produce **sonido**. Hacer la **inversión** es ir en sentido contrario: tomar un **sonido** y descubrir **qué movimientos** internos pudieron haberlo producido.
* **Ejemplo cotidiano:** Es como escuchar una nota tocada en un instrumento y deducir en qué traste o posición se colocaron los dedos para lograr ese sonido.

### 3. Dominio de la frecuencia, DFT y FFT
* **Qué significa:** Una señal de audio es una lista de valores de presión/amplitud a lo largo del tiempo, pero nuestro oído distingue vocales y timbres por las **frecuencias** presentes en la señal. La **DFT** (*Discrete Fourier Transform*) descompone una señal discreta en ondas sinusoidales usando números complejos ($e^{-j2\pi mn/N}$), y la **FFT** (*Fast Fourier Transform*) es el algoritmo rápido para calcularla en computadora.
* **Ejemplo cotidiano:** Si tocas un acorde en el piano, el micrófono registra una sola onda combinada, pero la FFT te dice qué notas/frecuencias están sonando ahí dentro. En la voz, esto permite observar los **formantes** (las zonas de frecuencia donde resuena el tracto vocal) sin depender de que ambas ondas estén exactamente alineadas en fase o milisegundos.

### 4. Ventaneo (por ejemplo, ventana de Hann)
* **Qué significa:** Como la voz cambia con el tiempo, el audio se corta en pedazos pequeños llamados **tramas** o ventanas. Multiplicar cada trama por una **ventana de Hann** suaviza los bordes para reducir el *spectral leakage* (fuga espectral), un artefacto que aparece cuando cortas una onda de golpe y genera frecuencias artificiales que no estaban en el sonido real.
* **Ejemplo cotidiano:** Es como hacer un fundido suave al inicio y al final de un recorte de audio en vez de cortarlo con tijera, evitando un "clic" artificial en el análisis.

### 5. Algoritmo genético, "ADN" (genoma) y *fitness*
* **Qué significa:** Un **algoritmo genético** es un método de búsqueda inspirado en la evolución biológica:
  * **Individuo / "ADN" (genoma):** Es una propuesta de solución. Aquí, el "ADN" es una secuencia de parámetros de articulación y tono a lo largo del tiempo (por ejemplo, una tabla de valores de tono y posición/apertura del tracto en cada tramo del audio).
  * **Función de *fitness* (aptitud):** Es la "calificación" que mide qué tan bueno es un individuo. Compara el espectro (FFT) del audio generado por ese "ADN" contra el espectro del audio objetivo: cuanto menor es el error espectral, mejor puntuación obtiene. También puede penalizar cambios demasiado bruscos entre un instante y el siguiente para que el movimiento sea más natural.
  * **Selección, cruza y mutación:** Los individuos con mejor *fitness* sobreviven y se combinan ("cruzan") o sufren pequeños ajustes aleatorios ("mutan") en cada generación, mientras los peores se descartan.
* **Ejemplo cotidiano:** Imagina que intentas dar con una combinación de perillas para imitar una vocal sin ver los números exactos. Pruebas 50 combinaciones al azar, te quedas con las 10 que suenan más parecidas, las combinas con pequeños ajustes y repites el proceso ronda tras ronda hasta acercarte mucho al objetivo.

---

## ¿Qué hará el programa paso a paso?

1. **Cargar y preparar el audio objetivo:** Toma un archivo `.wav` corto y claro (por ejemplo, una vocal sostenida como `/a/`), normaliza su amplitud, lo divide en tramas cortas y aplica ventaneo para calcular su espectro de referencia mediante la FFT.
2. **Crear una población inicial:** Genera un conjunto de "genomas" aleatorios que representan trayectorias de parámetros articulatorios y de tono.
3. **Sintetizar y evaluar cada individuo:** Para cada genoma, el simulador genera un audio, calcula su espectro con la FFT y la función de *fitness* mide qué tan cerca está del audio objetivo (sumando reglas de suavizado temporal).
4. **Evolucionar por generaciones:** Aplica selección, cruza y mutación durante varias generaciones para reducir el error espectral.
5. **Mostrar el resultado:** Reconstruye el audio `.wav` del mejor individuo final para escucharlo y genera una visualización animada que muestra el movimiento del tracto vocal junto con la comparación espectral.

---

## Alcance y limitaciones iniciales

* **Punto de partida recomendado:** Empezar con sonidos estables y cortos (como una vocal `/a/`, `/o/` o `/u/`) antes de intentar palabras completas o consonantes rápidas.
* **Mapeo uno-a-muchos:** Dos posturas ligeramente distintas de la lengua y la boca pueden producir un sonido muy parecido; por eso combinar la comparación espectral con suavizado temporal ayuda a obtener trayectorias más limpias y coherentes.
