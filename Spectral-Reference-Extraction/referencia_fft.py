import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.io.wavfile import write

SAMPLE_RATE = 16000
FRAME_MS = 40.0      # duración de cada trama en milisegundos
HOP_MS = 15.0        # avance entre tramas en ms (50% de solapamiento)
MAX_FREQ_HZ = 4000.0
MIN_FREQ_HZ = 80.0


def load_and_normalize_wav(filepath, target_fs=SAMPLE_RATE):
    """Carga un WAV, lo pasa a mono float32 y normaliza su amplitud."""
    fs, data = wavfile.read(filepath)
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    if np.issubdtype(data.dtype, np.integer):
        max_val = float(np.iinfo(data.dtype).max)
        signal = data.astype(np.float32) / max_val
    else:
        signal = data.astype(np.float32)

    # Remuestreo lineal simple si la frecuencia de muestreo difiere
    if fs != target_fs and len(signal) > 1:
        duration = len(signal) / float(fs)
        n_target = int(round(duration * target_fs))
        t_old = np.linspace(0.0, duration, len(signal), endpoint=False)
        t_new = np.linspace(0.0, duration, n_target, endpoint=False)
        signal = np.interp(t_new, t_old, signal).astype(np.float32)

    signal = signal - np.mean(signal)
    peak = np.max(np.abs(signal))
    if peak > 1e-6:
        signal = 0.9 * (signal / peak)
    return signal


def generate_fallback_vowel_a(duration=0.5, fs=SAMPLE_RATE, f0_hz=135.0):
    """Genera un audio de prueba tipo /a/ si aún no cargas un archivo externo."""
    t = np.arange(int(duration * fs)) / fs
    phase = np.mod(f0_hz * t, 1.0)
    # Tren de pulsos armónicos base
    source = (
        np.sin(np.pi * phase) ** 1.5
        - 0.35 * np.sin(2.0 * np.pi * phase)
        + 0.12 * np.sin(3.0 * np.pi * phase)
    )
    # Resonancias aproximadas de /a/ (F1 ~ 700 Hz, F2 ~ 1200 Hz) mediante filtros resonantes simples
    from scipy.signal import butter, lfilter
    b1, a1 = butter(2, [550.0, 900.0], btype="bandpass", fs=fs)
    b2, a2 = butter(2, [1000.0, 1450.0], btype="bandpass", fs=fs)
    voiced = 0.7 * lfilter(b1, a1, source) + 0.45 * lfilter(b2, a2, source) + 0.25 * source

    env = np.ones_like(voiced)
    fade = int(0.02 * fs)
    env[:fade] = np.linspace(0.0, 1.0, fade)
    env[-fade:] = np.linspace(1.0, 0.0, fade)
    out = voiced * env
    peak = np.max(np.abs(out))
    if peak > 1e-6:
        out = 0.9 * (out / peak)
    return out.astype(np.float32)


def extract_windowed_fft_magnitude(
    signal,
    fs=SAMPLE_RATE,
    frame_ms=FRAME_MS,
    hop_ms=HOP_MS,
    min_freq=MIN_FREQ_HZ,
    max_freq=MAX_FREQ_HZ,
):
    """
    Divide la señal en tramas con ventana de Hann y calcula la magnitud de la FFT
    en el rango de frecuencias vocales [min_freq, max_freq].
    Regresa:
      freqs_band: arreglo de frecuencias (Hz) en la banda seleccionada
      mag_frames: matriz de forma (n_frames, n_bins_banda) con magnitudes
    """
    frame_len = max(16, int(round(fs * frame_ms / 1000.0)))
    hop_len = max(1, int(round(fs * hop_ms / 1000.0)))

    if len(signal) < frame_len:
        signal = np.pad(signal, (0, frame_len - len(signal)))

    window = np.hanning(frame_len)
    freqs = np.fft.rfftfreq(frame_len, d=1.0 / fs)
    band_mask = (freqs >= min_freq) & (freqs <= max_freq)
    freqs_band = freqs[band_mask]

    frames_mag = []
    for start in range(0, len(signal) - frame_len + 1, hop_len):
        frame = signal[start : start + frame_len] * window
        # Magnitud de la FFT real (equivalente al módulo |X[m]| de la DFT)
        spec_mag = np.abs(np.fft.rfft(frame))
        frames_mag.append(spec_mag[band_mask])

    mag_frames = np.array(frames_mag, dtype=np.float32)
    return freqs_band, mag_frames


if __name__ == "__main__":
    # Cambia a la ruta de un .wav si ya tienes uno; si es None, usa el respaldo /a/
    wav_path = "vocal_e.wav"

    if wav_path:
        ref_signal = load_and_normalize_wav(wav_path, SAMPLE_RATE)
        source_label = f"Archivo: {wav_path}"
    else:
        ref_signal = generate_fallback_vowel_a(duration=0.5, fs=SAMPLE_RATE, f0_hz=135.0)
        write("objetivo_a_paso2.wav", SAMPLE_RATE, (ref_signal * 32767).astype(np.int16))
        source_label = "Vocal /a/ sintética de prueba (guardada en objetivo_a_paso2.wav)"

    freqs_band, mag_frames = extract_windowed_fft_magnitude(ref_signal)
    print(f"Fuente: {source_label}")
    print(f"Muestras totales: {len(ref_signal)} ({len(ref_signal)/SAMPLE_RATE:.2f} s)")
    print(f"Matriz espectral (tramas, bins_frecuencia): {mag_frames.shape}")
    print(f"Rango analizado: {freqs_band[0]:.1f} Hz a {freqs_band[-1]:.1f} Hz")

    # Visualización para inspeccionar señal y espectro
    fig, axes = plt.subplots(2, 1, figsize=(10, 6))
    plt.subplots_adjust(hspace=0.4)

    t_axis = np.arange(len(ref_signal)) / SAMPLE_RATE
    axes[0].plot(t_axis, ref_signal, color="#2b6cb0", lw=1.2)
    axes[0].set_title("Señal de referencia en el dominio del tiempo")
    axes[0].set_xlabel("Tiempo (s)")
    axes[0].set_ylabel("Amplitud normalizada")
    axes[0].grid(True, alpha=0.3)

    mean_mag_db = 20.0 * np.log10(np.mean(mag_frames, axis=0) + 1e-6)
    axes[1].plot(freqs_band, mean_mag_db, color="#c53030", lw=1.6)
    axes[1].set_title("Magnitud espectral promedio por FFT (ventana de Hann)")
    axes[1].set_xlabel("Frecuencia (Hz)")
    axes[1].set_ylabel("Magnitud promedio (dB)")
    axes[1].grid(True, alpha=0.3)

    plt.show()
