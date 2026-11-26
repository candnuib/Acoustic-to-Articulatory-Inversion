import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from scipy.io.wavfile import write

# --- Configuración general de audio ---
SAMPLE_RATE = 16000
DURATION = 0.6  # segundos por prueba
N_SEGMENTS = 44  # similar a los segmentos de tubo de Pink Trombone

# Rangos explícitos de cada parámetro [mínimo, máximo]
PARAM_RANGES = {
    "f0_hz": (80.0, 260.0),      # Frecuencia fundamental (tono de voz en Hz)
    "tongue_pos": (0.15, 0.85),  # Posición a lo largo del tracto (0=glotis, 1=labios)
    "tongue_ap": (0.05, 0.95),   # Apertura/radio en la constricción de la lengua
    "lip_ap": (0.05, 0.95),      # Apertura de los labios / salida oral
}


def build_vocal_tract_areas(tongue_pos, tongue_ap, lip_ap, n_seg=N_SEGMENTS):
  """Construye un perfil de áreas normalizadas (0 a 1) de glotis (izq) a labios (der)."""
  x = np.linspace(0.0, 1.0, n_seg)
  area = 0.35 + 0.20 * x

  sigma = 0.11
  constriction_depth = 1.0 - tongue_ap
  area *= 1.0 - 0.85 * constriction_depth * np.exp(
      -((x - tongue_pos) ** 2) / (2.0 * sigma ** 2)
  )

  area[-1] = np.clip(lip_ap, 0.03, 1.0)
  return np.clip(area, 0.02, 1.2)


def synthesize_tract_audio(
    f0_hz, tongue_pos, tongue_ap, lip_ap, duration=DURATION, fs=SAMPLE_RATE
):
  """Simula un tubo acústico discreto de guía de ondas (1D) con excitación glótica."""
  n_samples = int(duration * fs)
  areas = build_vocal_tract_areas(tongue_pos, tongue_ap, lip_ap, N_SEGMENTS)

  r = (areas[:-1] - areas[1:]) / (areas[:-1] + areas[1:] + 1e-8)
  r_lip = (areas[-1] - 0.6) / (areas[-1] + 0.6 + 1e-8)

  t = np.arange(n_samples) / fs
  phase = np.mod(f0_hz * t, 1.0)
  glottal = (
      np.sin(np.pi * phase) ** 1.5
      - 0.35 * np.sin(2.0 * np.pi * phase)
      + 0.12 * np.sin(3.0 * np.pi * phase)
  )

  env = np.ones(n_samples)
  fade = int(0.02 * fs)
  env[:fade] = np.linspace(0.0, 1.0, fade)
  env[-fade:] = np.linspace(1.0, 0.0, fade)
  source = glottal * env * 0.4

  f_wave = np.zeros(N_SEGMENTS)
  b_wave = np.zeros(N_SEGMENTS)
  out = np.zeros(n_samples)

  for n in range(n_samples):
    f_wave[0] = 0.7 * b_wave[0] + source[n]
    for i in range(N_SEGMENTS - 1):
      b_next = b_wave[i + 1]
      f_wave[i + 1] = (1.0 + r[i]) * f_wave[i] - r[i] * b_next
      b_wave[i] = r[i] * f_wave[i] + (1.0 - r[i]) * b_next
    out[n] = (1.0 + r_lip) * f_wave[-1]
    b_wave[-1] = r_lip * f_wave[-1] * 0.95

  out = out - np.mean(out)
  peak = np.max(np.abs(out))
  if peak > 1e-6:
    out = 0.8 * (out / peak)
  return out.astype(np.float32)


def compute_fft_db(signal, fs=SAMPLE_RATE, max_freq=4000.0):
  """Calcula magnitud en dB mediante FFT real."""
  window = np.hanning(len(signal))
  spec = np.abs(np.fft.rfft(signal * window))
  freqs = np.fft.rfftfreq(len(signal), d=1.0 / fs)
  mask = freqs <= max_freq
  spec_db = 20.0 * np.log10(spec[mask] + 1e-6)
  return freqs[mask], spec_db


def play_pcm_audio(wave, fs=SAMPLE_RATE):
  """Reproduce el arreglo de audio en memoria sin guardar archivo."""
  try:
    import sounddevice as sd
    sd.stop()
    sd.play(wave, fs)
    print("Reproduciendo audio en memoria (sounddevice)...")
    return True
  except Exception:
    pass

  try:
    import simpleaudio as sa
    sa.stop_all()
    pcm_int16 = (np.clip(wave, -1.0, 1.0) * 32767).astype(np.int16)
    play_obj = sa.play_buffer(pcm_int16, 1, 2, fs)
    print("Reproduciendo audio en memoria (simpleaudio)...")
    return True
  except Exception:
    pass

  print(
      "No se encontró backend de reproducción en memoria. Instala 'sounddevice'"
      " (pip install sounddevice) para escuchar directo sin guardar."
  )
  return False


# --- Interfaz gráfica ---
fig = plt.figure(figsize=(10, 6.6))
plt.subplots_adjust(left=0.09, right=0.96, top=0.90, bottom=0.35, hspace=0.42)

ax_tract = fig.add_subplot(2, 1, 1)
init_f0 = 135.0
init_tpos = 0.45
init_tap = 0.45
init_lap = 0.65

x_axis = np.linspace(0.0, 1.0, N_SEGMENTS)
init_areas = build_vocal_tract_areas(init_tpos, init_tap, init_lap)
(line_top,) = ax_tract.plot(x_axis, init_areas, lw=2.5, color="#d95f87")
(line_bot,) = ax_tract.plot(x_axis, -init_areas, lw=2.5, color="#d95f87")
fill_tract = ax_tract.fill_between(
    x_axis, -init_areas, init_areas, color="#f4a6be", alpha=0.55
)
ax_tract.set_xlim(0.0, 1.0)
ax_tract.set_ylim(-1.1, 1.1)
ax_tract.set_xlabel("Tracto vocal (0.0 = Glotis / Garganta  --->  1.0 = Labios)")
ax_tract.set_ylabel("Apertura")
ax_tract.set_title("Simulador 1D del Tracto Vocal y Espectro FFT en Tiempo Real")
ax_tract.grid(True, alpha=0.3)

ax_fft = fig.add_subplot(2, 1, 2)
init_audio = synthesize_tract_audio(init_f0, init_tpos, init_tap, init_lap)
freqs, spec_db = compute_fft_db(init_audio)
(line_fft,) = ax_fft.plot(freqs, spec_db, lw=1.8, color="#1f6feb")
ax_fft.set_xlim(50, 4000)
ax_fft.set_ylim(-40, 85)
ax_fft.set_xlabel("Frecuencia (Hz)")
ax_fft.set_ylabel("Magnitud (dB)")
ax_fft.grid(True, alpha=0.3)

ax_s_f0 = plt.axes([0.22, 0.23, 0.65, 0.024])
ax_s_tpos = plt.axes([0.22, 0.18, 0.65, 0.024])
ax_s_tap = plt.axes([0.22, 0.13, 0.65, 0.024])
ax_s_lap = plt.axes([0.22, 0.08, 0.65, 0.024])

s_f0 = Slider(
    ax_s_f0,
    f"f0 Hz [{PARAM_RANGES['f0_hz'][0]}–{PARAM_RANGES['f0_hz'][1]}]",
    *PARAM_RANGES["f0_hz"],
    valinit=init_f0,
)
s_tpos = Slider(
    ax_s_tpos,
    f"Pos. Lengua [{PARAM_RANGES['tongue_pos'][0]}–{PARAM_RANGES['tongue_pos'][1]}]",
    *PARAM_RANGES["tongue_pos"],
    valinit=init_tpos,
)
s_tap = Slider(
    ax_s_tap,
    f"Apert. Lengua [{PARAM_RANGES['tongue_ap'][0]}–{PARAM_RANGES['tongue_ap'][1]}]",
    *PARAM_RANGES["tongue_ap"],
    valinit=init_tap,
)
s_lap = Slider(
    ax_s_lap,
    f"Apert. Labios [{PARAM_RANGES['lip_ap'][0]}–{PARAM_RANGES['lip_ap'][1]}]",
    *PARAM_RANGES["lip_ap"],
    valinit=init_lap,
)

current_audio = {"wave": init_audio}

def play_pcm_audio(wave, fs=SAMPLE_RATE):
  """Reproduce el arreglo de audio en memoria sin guardar archivo."""
  pcm_int16 = (np.clip(wave, -1.0, 1.0) * 32767).astype(np.int16)

  # 1. Intentar sounddevice
  try:
    import sounddevice as sd
    sd.stop()
    sd.play(wave, fs)
    print("Reproduciendo con sounddevice...")
    return True
  except Exception:
    pass

  # 2. Intentar pygame.mixer desde bytes en memoria
  try:
    import io
    import pygame
    if not pygame.mixer.get_init():
      pygame.mixer.init(frequency=fs, size=-16, channels=1)
    snd = pygame.mixer.Sound(buffer=pcm_int16.tobytes())
    snd.play()
    print("Reproduciendo con pygame...")
    return True
  except Exception:
    pass

  # 3. Respaldo en Linux via PulseAudio/PipeWire (paplay) o ALSA (aplay)
  import shutil
  import subprocess
  for cmd in (
      ["paplay", "--raw", "--format=s16le", f"--rate={fs}", "--channels=1"],
      ["aplay", "-q", "-f", "S16_LE", "-r", str(fs), "-c", "1"],
  ):
    if shutil.which(cmd[0]):
      try:
        subprocess.Popen(cmd, stdin=subprocess.PIPE).communicate(
            input=pcm_int16.tobytes(), timeout=2
        )
        print(f"Reproduciendo con {cmd[0]}...")
        return True
      except Exception:
        pass

  print(
      "No se encontró backend de audio disponible. Instala 'sounddevice' o"
      " 'pygame'."
  )
  return False
def update_visuals(_val=None):
  global fill_tract
  f0 = s_f0.val
  tpos = s_tpos.val
  tap = s_tap.val
  lap = s_lap.val

  areas = build_vocal_tract_areas(tpos, tap, lap)
  line_top.set_ydata(areas)
  line_bot.set_ydata(-areas)
  fill_tract.remove()
  fill_tract = ax_tract.fill_between(
      x_axis, -areas, areas, color="#f4a6be", alpha=0.55
  )

  audio = synthesize_tract_audio(f0, tpos, tap, lap)
  current_audio["wave"] = audio
  _, db = compute_fft_db(audio)
  line_fft.set_ydata(db)
  fig.canvas.draw_idle()


for sl in (s_f0, s_tpos, s_tap, s_lap):
  sl.on_changed(update_visuals)

# Botón 1: Reproducir directo en memoria
ax_btn_play = plt.axes([0.27, 0.012, 0.20, 0.038])
btn_play = Button(ax_btn_play, "Reproducir")


def on_play(_event):
  play_pcm_audio(current_audio["wave"], SAMPLE_RATE)


btn_play.on_clicked(on_play)

# Botón 2: Guardar WAV solo cuando tú quieras
ax_btn_save = plt.axes([0.52, 0.012, 0.22, 0.038])
btn_save = Button(ax_btn_save, "Guardar WAV")


def on_save(_event):
  out_file = "prueba_tracto_1d.wav"
  pcm = (np.clip(current_audio["wave"], -1.0, 1.0) * 32767).astype(np.int16)
  write(out_file, SAMPLE_RATE, pcm)
  print(f"Audio guardado en '{out_file}'.")


btn_save.on_clicked(on_save)
plt.show()
