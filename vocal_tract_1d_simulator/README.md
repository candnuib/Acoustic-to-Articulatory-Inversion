# Simulador Interactivo 1D del Tracto Vocal (Paso 1)

Programa interactivo en Python que simula un tubo acústico 1D (inspirado en *Pink Trombone*) para explorar cómo cambia el sonido y el espectro de frecuencia (**FFT**) al modificar los parámetros del tracto vocal y el tono base. Permite ajustar variables en tiempo real, ver la forma del conducto y el espectro, escuchar el audio directamente en memoria y guardar archivos `.wav`.

> **Nota sobre la cavidad nasal:** Este simulador **no utiliza parámetro nasal** (ni rama nasal independiente). Modela únicamente un conducto oral unidimensional de 44 segmentos desde la glotis hasta los labios, suficiente para probar vocales orales y transiciones sencillas con bajo costo computacional.

---

## Parámetros modificables y sus rangos

Cada parámetro está acotado a un rango específico en el código (`PARAM_RANGES`):

| Parámetro en la interfaz | Variable en código | Rango `[mín, máx]` | Qué controla |
| :--- | :--- | :---: | :--- |
| **`f0 Hz`** | `f0_hz` | `80.0 – 260.0` | Frecuencia fundamental (tono de voz en Hz) de la fuente glótica. |
| **`Pos. Lengua`** | `tongue_pos` | `0.15 – 0.85` | Posición a lo largo del tracto (`0.0` = glotis/garganta, `1.0` = labios). |
| **`Apert. Lengua`** | `tongue_ap` | `0.05 – 0.95` | Grado de apertura en la zona de constricción de la lengua (valores bajos estrechan más el conducto). |
| **`Apert. Labios`** | `lip_ap` | `0.05 – 0.95` | Apertura del último segmento / salida oral hacia el exterior. |

---

## Valores de referencia aproximados para vocales

Estos valores sirven como punto de partida para probar vocales orales en este modelo simplificado (ajusta ligeramente según el timbre que busques):

| Vocal | `f0_hz` | `Pos. Lengua` | `Apert. Lengua` | `Apert. Labios` | Qué observar en la FFT y al escuchar |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`/a/`** | `135.0` | `0.38` | `0.55` | `0.78` | Boca abierta; resonancia principal marcada en zona media-baja. |
| **`/e/`** | `145.0` | `0.65` | `0.42` | `0.62` | Constricción más adelantada; mayor energía en frecuencias medias. |
| **`/i/`** | `150.0` | `0.74` | `0.25` | `0.45` | Estrechamiento frontal pronunciado; separación clara entre picos espectrales. |
| **`/o/`** | `130.0` | `0.34` | `0.40` | `0.35` | Constricción más atrás y labios más cerrados. |
| **`/u/`** | `125.0` | `0.28` | `0.22` | `0.22` | Conducto estrecho y redondeado; tono y resonancias más graves. |

---

## Controles y botones

* **Sliders (`f0 Hz`, `Pos. Lengua`, `Apert. Lengua`, `Apert. Labios`):** Actualizan en tiempo real el perfil del tracto vocal (panel superior), la señal sintetizada y su magnitud espectral en dB mediante `np.fft.rfft` con ventana de Hann (panel inferior).
* **Botón `Reproducir`:** Reproduce el arreglo de audio en memoria (usando `sounddevice` o `simpleaudio`) sin crear archivos `.wav` en disco.
* **Botón `Guardar WAV`:** Exporta el audio actual a `prueba_tracto_1d.wav` (`16000 Hz`, mono, PCM de 16 bits).

---

## Guía de trabajo: experimentar, aprender y documentar paso a paso

Para construir criterio técnico antes de pasar a la etapa de optimización/entrenamiento (como algoritmos genéticos y comparación espectral), sigue este ciclo en cada sesión:

1. **Establece una hipótesis antes de mover un slider:** Anota qué esperas que ocurra al cambiar un solo parámetro (por ejemplo, *"si bajo `Apert. Labios` de `0.78` a `0.22` en `/a/`, las frecuencias altas se atenuarán y sonará más hacia `/o/` o `/u/`"*).
2. **Aísla una variable a la vez:** Mueve solo un control cada vez, pulsa **Reproducir** y observa cómo se desplazan los picos (resonancias/formantes) en la gráfica de **FFT**. Esto te ayuda a distinguir cambios de tono (`f0`, que desplaza armónicos) de cambios de forma del tubo (que moldean el contorno espectral).
3. **Registra tus pruebas en una bitácora simple:** Lleva una tabla o nota de experimento con:
   * Vocal o sonido probado.
   * Valores exactos de `f0_hz`, `tongue_pos`, `tongue_ap` y `lip_ap`.
   * Qué escuchaste y qué cambio notaste en la **FFT**.
   * Nombre del archivo `.wav` si decidiste guardarlo.
4. **Compara el oído contra la gráfica de frecuencia:** Verifica si dos configuraciones distintas producen espectros parecidos o si un pequeño cambio en la posición de la lengua altera mucho la percepción; esa observación será clave al diseñar la función de *fitness* y la penalización por cambios bruscos en el siguiente paso.
5. **Cierra cada sesión con una conclusión breve:** Escribe 2 o 3 líneas sobre qué aprendiste o qué duda surgió (por ejemplo, qué vocales cuesta más distinguir con este modelo sin cavidad nasal) para tenerlo listo al avanzar al análisis espectral por ventanas y al ciclo evolutivo.
