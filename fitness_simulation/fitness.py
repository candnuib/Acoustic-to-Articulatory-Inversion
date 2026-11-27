import numpy as np
from scipy.signal import butter, lfilter

SAMPLE_RATE = 16000
FRAME_MS = 35.0
HOP_MS = 17.5
MIN_FREQ_HZ = 80.0
MAX_FREQ_HZ = 4000.0
N_SEGMENTS = 44

PARAM_RANGES = {
    "f0_hz": (80.0, 260.0),
    "tongue_pos": (0.15, 0.85),
    "tongue_ap": (0.05, 0.95),
    "lip_ap": (0.05, 0.95),
}


def build_vocal_tract_areas(tongue_pos, tongue_ap, lip_ap, n_seg=N_SEGMENTS):
  x = np.linspace(0.0, 1.0, n_seg)
  area = 0.35 + 0.20 * x
  sigma = 0.11
  constriction_depth = 1.0 - tongue_ap
  area *= 1.0 - 0.85 * constriction_depth * np.exp(
      -((x - tongue_pos) ** 2) / (2.0 * sigma**2)
  )
  area[-1] = np.clip(lip_ap, 0.03, 1.0)
  return np.clip(area, 0.02, 1.2)


def synthesize_trajectory_audio(params_traj, fs=SAMPLE_RATE):
  """
    Sintetiza audio a partir de una trayectoria temporal de parámetros.
    params_traj: arreglo de forma (n_frames, 4) con columnas:
      [f0_hz, tongue_pos, tongue_ap, lip_ap]
    """
  params_traj = np.asarray(params_traj, dtype=np.float32)
  n_frames = params_traj.shape[0]
  hop_len = max(1, int(round(fs * HOP_MS / 1000.0)))
  frame_len = max(16, int(round(fs * FRAME_MS / 1000.0)))
  n_samples = (n_frames - 1) * hop_len + frame_len

  # Interpolar parámetros cuadro a cuadro hacia cada muestra de audio
  frame_centers = np.arange(n_frames) * hop_len + frame_len * 0.5
  sample_idx = np.arange(n_samples, dtype=np.float32)

  f0_curve = np.interp(sample_idx, frame_centers, params_traj[:, 0])
  tpos_curve = np.interp(sample_idx, frame_centers, params_traj[:, 1])
  tap_curve = np.interp(sample_idx, frame_centers, params_traj[:, 2])
  lap_curve = np.interp(sample_idx, frame_centers, params_traj[:, 3])

  # Fase acumulada continua para evitar saltos de fase cuando f0 cambia en el tiempo
  phase = np.mod(np.cumsum(f0_curve / fs), 1.0)
  source = (
      np.sin(np.pi * phase) ** 1.5
      - 0.35 * np.sin(2.0 * np.pi * phase)
      + 0.12 * np.sin(3.0 * np.pi * phase)
  ) * 0.4

  # Evaluamos guía de ondas por bloques de muestras para mantener velocidad aceptable en Python
  out = np.zeros(n_samples, dtype=np.float32)
  f_wave = np.zeros(N_SEGMENTS, dtype=np.float32)
  b_wave = np.zeros(N_SEGMENTS, dtype=np.float32)

  for start in range(0, n_samples, hop_len):
    end = min(start + hop_len, n_samples)
    mid = (start + end) // 2
    areas = build_vocal_tract_areas(
        tpos_curve[mid], tap_curve[mid], lap_curve[mid], N_SEGMENTS
    )
    r = (areas[:-1] - areas[1:]) / (areas[:-1] + areas[1:] + 1e-8)
    r_lip = (areas[-1] - 0.6) / (areas[-1] + 0.6 + 1e-8)

    for n in range(start, end):
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
    out = 0.85 * (out / peak)
  return out.astype(np.float32)


def extract_spec_db_frames(
    signal,
    fs=SAMPLE_RATE,
    frame_ms=FRAME_MS,
    hop_ms=HOP_MS,
    min_freq=MIN_FREQ_HZ,
    max_freq=MAX_FREQ_HZ,
):
  """Devuelve matriz (n_frames, n_bins) de magnitud espectral en dB con ventana de Hann."""
  frame_len = max(16, int(round(fs * frame_ms / 1000.0)))
  hop_len = max(1, int(round(fs * hop_ms / 1000.0)))
  if len(signal) < frame_len:
    signal = np.pad(signal, (0, frame_len - len(signal)))

  window = np.hanning(frame_len)
  freqs = np.fft.rfftfreq(frame_len, d=1.0 / fs)
  mask = (freqs >= min_freq) & (freqs <= max_freq)

  frames_db = []
  for start in range(0, len(signal) - frame_len + 1, hop_len):
    frame = signal[start : start + frame_len] * window
    mag = np.abs(np.fft.rfft(frame))[mask]
    db = 20.0 * np.log10(mag + 1e-6)
    frames_db.append(db)

  return np.array(frames_db, dtype=np.float32)


def compute_smoothness_penalty(params_traj):
  """
    Mide cuánto cambian los parámetros normalizados [0, 1] entre tramas consecutivas.
    Un cambio brusco aumenta la penalización.
    """
  if params_traj.shape[0] < 2:
    return 0.0

  norm = np.zeros_like(params_traj, dtype=np.float32)
  keys = ["f0_hz", "tongue_pos", "tongue_ap", "lip_ap"]
  for idx, k in enumerate(keys):
    lo, hi = PARAM_RANGES[k]
    norm[:, idx] = (params_traj[:, idx] - lo) / (hi - lo + 1e-8)

  diffs = np.diff(norm, axis=0)
  return float(np.mean(diffs**2))


def evaluate_fitness(
    candidate_params,
    target_spec_db,
    fs=SAMPLE_RATE,
    smooth_weight=5.0,
    use_hann=True,
):
  """
    Calcula:
      - fitness (mayor es mejor)
      - desglose de error espectral y penalización temporal para depurar
    """
  gen_audio = synthesize_trajectory_audio(candidate_params, fs=fs)

  if use_hann:
    gen_spec_db = extract_spec_db_frames(gen_audio, fs=fs)
  else:
    # Prueba comparativa sin ventana de Hann (ventana rectangular implícita)
    frame_len = max(16, int(round(fs * FRAME_MS / 1000.0)))
    hop_len = max(1, int(round(fs * HOP_MS / 1000.0)))
    freqs = np.fft.rfftfreq(frame_len, d=1.0 / fs)
    mask = (freqs >= MIN_FREQ_HZ) & (freqs <= MAX_FREQ_HZ)
    frames = []
    for start in range(0, len(gen_audio) - frame_len + 1, hop_len):
      mag = np.abs(np.fft.rfft(gen_audio[start : start + frame_len]))[mask]
      frames.append(20.0 * np.log10(mag + 1e-6))
    gen_spec_db = np.array(frames, dtype=np.float32)

  n_frames = min(target_spec_db.shape[0], gen_spec_db.shape[0])
  n_bins = min(target_spec_db.shape[1], gen_spec_db.shape[1])

  diff_db = target_spec_db[:n_frames, :n_bins] - gen_spec_db[:n_frames, :n_bins]
  spectral_mse = float(np.mean(diff_db**2))
  smooth_pen = compute_smoothness_penalty(candidate_params)

  total_cost = spectral_mse + smooth_weight * smooth_pen
  fitness = -total_cost
  return {
      "fitness": fitness,
      "total_cost": total_cost,
      "spectral_mse": spectral_mse,
      "smoothness_penalty": smooth_pen,
  }


if __name__ == "__main__":
  rng = np.random.default_rng(42)
  n_frames = 25

  # 1. Creamos una trayectoria de referencia (simulando una vocal /a/ estable)
  target_params = np.column_stack([
      np.full(n_frames, 135.0),
      np.full(n_frames, 0.38),
      np.full(n_frames, 0.55),
      np.full(n_frames, 0.78),
  ])
  target_audio = synthesize_trajectory_audio(target_params)
  target_spec = extract_spec_db_frames(target_audio)

  # 2. Candidato cercano al objetivo
  near_params = target_params.copy()
  near_params[:, 0] += rng.normal(0.0, 2.0, size=n_frames)
  near_params[:, 1:] += rng.normal(0.0, 0.02, size=(n_frames, 3))

  # 3. Candidato aleatorio y brusco
  noisy_params = np.column_stack([
      rng.uniform(*PARAM_RANGES["f0_hz"], size=n_frames),
      rng.uniform(*PARAM_RANGES["tongue_pos"], size=n_frames),
      rng.uniform(*PARAM_RANGES["tongue_ap"], size=n_frames),
      rng.uniform(*PARAM_RANGES["lip_ap"], size=n_frames),
  ])

  res_near = evaluate_fitness(near_params, target_spec)
  res_noisy = evaluate_fitness(noisy_params, target_spec)

  print("--- Prueba de Función de Fitness ---")
  print(f"Candidato cercano -> {res_near}")
  print(f"Candidato ruidoso -> {res_noisy}")
