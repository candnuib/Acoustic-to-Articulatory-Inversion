# Función de Fitness Espectral y Suavizado Temporal (Paso 3)

Este script prueba la **función de *fitness*** que calificará a cada candidato ("ADN" o secuencia de parámetros del instrumento) cuando se entrene el algoritmo genético en el siguiente paso.

> **Aclaración importante:** En este paso **aún no hay ciclo evolutivo ni aprendizaje**. La función de *fitness* no inventa frecuencias de salida al azar: **recibe una secuencia de parámetros del instrumento** (`f0_hz`, `tongue_pos`, `tongue_ap`, `lip_ap` a lo largo de varias tramas), sintetiza un audio con ellos y mide qué tan bien se parece ese audio al objetivo en el dominio de la frecuencia.

---

## ¿Qué hace el script de prueba paso a paso?

1. **Construye el objetivo de referencia (`target_params` $\rightarrow$ `target_audio` $\rightarrow$ `target_spec`):**
   * Define `25` tramas con valores fijos del instrumento (`f0_hz = 135.0`, `tongue_pos = 0.38`, `tongue_ap = 0.55`, `lip_ap = 0.78`).
   * Sintetiza su señal de audio con `synthesize_trajectory_audio` y calcula su espectro de magnitud en dB por tramas con **FFT** y ventana de Hann (`extract_spec_db_frames`). Ese espectro (`target_spec`) es la meta a comparar.

2. **Crea dos candidatos de prueba (trayectorias de parámetros del instrumento):**
   * **`near_params` (candidato cercano):** Parte de los parámetros de referencia y les agrega pequeñas variaciones aleatorias (`rng.normal`). Representa una propuesta que ya se aproxima a la configuración buscada.
   * **`noisy_params` (candidato ruidoso):** Asigna valores aleatorios dentro de los rangos permitidos (`PARAM_RANGES`) para cada parámetro del instrumento en cada trama (`rng.uniform`). Representa una propuesta desordenada y con saltos.

3. **Evalúa cada candidato con `evaluate_fitness`:**
   * **Sintetiza el audio:** Convierte la matriz de parámetros del candidato `(n_frames, 4)` en una onda de audio en el tiempo.
   * **Calcula el espectro (FFT):** Divide el audio generado en tramas ventaneadas con Hann y obtiene su magnitud espectral en dB en la banda de `80 Hz` a `4000 Hz`.
   * **Mide el error espectral (`spectral_mse`):** Calcula el error cuadrático medio entre el espectro objetivo (`target_spec`) y el espectro generado (`gen_spec_db`). Un valor más bajo significa mayor similitud en frecuencia.
   * **Mide la penalización por suavizado (`smoothness_penalty`):** Revisa cuánto cambian los parámetros normalizados entre una trama y la siguiente (`np.diff`). Si hay cambios bruscos entre cuadros, aumenta la penalización para evitar movimientos erráticos.
   * **Calcula el costo total y el *fitness*:** Suma el error espectral y la penalización ponderada (`total_cost = spectral_mse + smooth_weight * smoothness_penalty`) y define `fitness = -total_cost`.

---

## Cómo interpretar los resultados impresos

* **`spectral_mse`:** Diferencia promedio al cuadrado entre los espectros (en dB) del audio objetivo y del audio sintetizado. **Menor es mejor** (más parecido en frecuencia).
* **`smoothness_penalty`:** Qué tan bruscos o "brincones" son los cambios de los parámetros del instrumento entre tramas consecutivas. **Menor es mejor** (trayectoria más suave).
* **`total_cost`:** Costo combinado que se busca minimizar. **Menor es mejor**.
* **`fitness`:** Calificación final (`-total_cost`). Como es negativo, **un valor más cercano a `0` (menos negativo) indica un mejor candidato**. En la prueba, `near_params` debe obtener un `fitness` mayor (menos negativo) que `noisy_params`.

---

## Por qué se usa la ventana de Hann en la comparación

Si no aplicas la ventana de Hann antes de calcular la **FFT** (dejando implícitamente una ventana rectangular), cortar cada trama de golpe provoca **fuga espectral (*spectral leakage*)**: la energía de los armónicos o picos se esparce hacia frecuencias vecinas y eleva el piso de ruido. Eso introduce diferencias artificiales entre espectros que pueden confundir al algoritmo genético al comparar candidatos.
