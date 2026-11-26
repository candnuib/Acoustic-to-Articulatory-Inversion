# Extracción de Referencia Espectral por Ventanas y FFT (Paso 2)

Script en Python para cargar un archivo `.wav` objetivo (o generar un audio de respaldo si no se indica ninguno), dividirlo en tramas cortas con **ventana de Hann** y calcular la magnitud de su espectro mediante **FFT** (`np.fft.rfft`) dentro de la banda vocal (`80 Hz` a `4000 Hz`).

Este paso prepara el **objetivo de frecuencia** con el que más adelante se comparará el audio sintetizado por cada individuo ("ADN") durante el entrenamiento del algoritmo genético.

---

## ¿Qué hace este programa?

1. **Carga o genera el audio objetivo:** Si defines una ruta en `wav_path`, lee el archivo `.wav`, lo convierte a mono `float32`, ajusta su frecuencia de muestreo a `16000 Hz` si es necesario y normaliza su amplitud. Si `wav_path = None`, genera una vocal `/a/` sintética de prueba y la guarda como `objetivo_a_paso2.wav`.
2. **Segmenta en tramas con ventaneo:** Divide la señal en ventanas de duración `FRAME_MS` avanzando cada `HOP_MS` (con solapamiento). A cada trama le aplica una ventana de Hann (`np.hanning`) para suavizar los extremos y reducir el *spectral leakage* (fuga espectral).
3. **Calcula la magnitud de la FFT:** Aplica `np.fft.rfft` a cada trama ventaneada, toma la magnitud (`np.abs(...)`) y filtra el rango entre `MIN_FREQ_HZ` y `MAX_FREQ_HZ`, devolviendo una matriz de forma `(n_frames, n_bins_banda)`.
4. **Grafica la señal y su espectro promedio:** Muestra en pantalla dos gráficas para inspeccionar el audio antes de pasar a la evaluación por *fitness*.

---

## ¿Qué muestran las gráficas y para qué sirven?

* **Gráfica superior — Señal de referencia en el dominio del tiempo:** Muestra la amplitud normalizada del audio a lo largo del tiempo (en segundos). Te sirve para comprobar visualmente la duración del clip, ver si hay silencios largos al inicio o al final, detectar saturaciones o cortes bruscos, y confirmar que cargaste el `.wav` correcto.
* **Gráfica inferior — Magnitud espectral promedio por FFT (en dB):** Muestra cómo se distribuye la energía de la señal a lo largo de la frecuencia (en Hz) promediada sobre todas las tramas. Te sirve para ubicar las zonas de mayor energía y resonancia (formantes y armónicos) que tu algoritmo genético intentará aproximar cuando evalúe el "parentesco" espectral de cada candidato.

---

## Cómo usar un `.wav` propio o generado en el Paso 1

1. **Si guardaste un sonido desde el simulador del Paso 1** (por ejemplo, `prueba_tracto_1d.wav` con el botón **Guardar WAV**) o tienes tu propia grabación/muestra en `.wav`, colócalo en la carpeta de trabajo.
2. Abre `paso2_referencia_fft.py` y modifica `wav_path`:
   ```python
   wav_path = "prueba_tracto_1d.wav"
