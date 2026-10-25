"""Genera bucles de audio sin cortes (lluvia, tormenta, mar, ruido marrón)."""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import sys, os

SR = 44100
DUR = 300          # segundos del bucle
FADE = 4           # segundos de fundido para empalmar el bucle
N = (DUR + FADE) * SR
OUT = sys.argv[1]
rng = np.random.default_rng(1234)


def sos_bp(lo, hi, order=4):
    return signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def sos_lp(f, order=4):
    return signal.butter(order, f, btype="low", fs=SR, output="sos")


def sos_hp(f, order=4):
    return signal.butter(order, f, btype="high", fs=SR, output="sos")


def filt(sos, x):
    return signal.sosfilt(sos, x)


def pink(n):
    w = rng.standard_normal(n)
    f = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    freqs[0] = freqs[1]
    f /= np.sqrt(freqs)
    p = np.fft.irfft(f, n)
    return p / np.std(p)


def brown(n):
    w = rng.standard_normal(n)
    b = np.cumsum(w)
    b = filt(sos_hp(25, 2), b)
    return b / np.std(b)


def slow_mod(n, depth, periods):
    t = np.arange(n) / SR
    m = np.zeros(n)
    for p in periods:
        m += np.sin(2 * np.pi * t / p + rng.uniform(0, 2 * np.pi))
    m /= len(periods)
    return 1 + depth * m


def drops(n, rate, lo, hi, decay_ms=(3, 12), bands=6):
    """Gotas: impulsos aleatorios -> ráfagas cortas filtradas en varias bandas."""
    out = np.zeros(n)
    edges = np.geomspace(lo, hi, bands + 1)
    for i in range(bands):
        k = rng.poisson(rate / bands * n / SR)
        idx = rng.integers(0, n, k)
        imp = np.zeros(n)
        np.add.at(imp, idx, np.minimum(rng.pareto(4.0, k) + 0.3, 1.2))
        dms = rng.uniform(*decay_ms)
        L = int(SR * dms / 1000 * 5)
        tt = np.arange(L) / SR
        kern = rng.standard_normal(L) * np.exp(-tt / (dms / 1000))
        burst = signal.fftconvolve(imp, kern)[:n]
        out += filt(sos_bp(edges[i], edges[i + 1], 2), burst)
    return out / (np.std(out) + 1e-9)


def stereo_pair(fn):
    """Genera dos canales decorrelados con la misma receta."""
    return np.stack([fn(), fn()], axis=1)


def thunder(n, times):
    out = np.zeros(n)
    for t0 in times:
        L = int(SR * rng.uniform(7, 11))
        tt = np.arange(L) / SR
        att = rng.uniform(1.0, 2.2)
        env = np.minimum(tt / att, 1) * np.exp(-np.maximum(tt - att, 0) / rng.uniform(2.0, 3.5))
        # varios "rodamientos"
        env *= 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * tt * rng.uniform(0.3, 0.7)))
        rumble = filt(sos_lp(rng.uniform(140, 220), 4), brown(L)) * env
        s = int(t0 * SR)
        out[s:s + L] += rumble[: max(0, min(L, n - s))]
    return out


def make_loop(x):
    """Empalma el final con el principio con fundido de igual potencia."""
    F = FADE * SR
    L = DUR * SR
    th = np.linspace(0, np.pi / 2, F)[:, None] if x.ndim == 2 else np.linspace(0, np.pi / 2, F)
    y = x[:L].copy()
    y[:F] = x[:F] * np.sin(th) + x[L:L + F] * np.cos(th)
    return y


def finish(x, rms_db=-21.0):
    x = x - np.mean(x, axis=0)
    rms = np.sqrt(np.mean(x ** 2))
    x *= 10 ** (rms_db / 20) / rms
    # limitador suave
    x = np.tanh(x * 1.2) / 1.2
    peak = np.max(np.abs(x))
    if peak > 0.95:
        x *= 0.95 / peak
    return x


def save(name, x):
    x = finish(make_loop(x))
    wavfile.write(os.path.join(OUT, name + ".wav"), SR, (x * 32767).astype(np.int16))
    print("ok", name)


# 1. Lluvia suave
def lluvia_suave():
    base = filt(sos_bp(300, 9000, 3), pink(N)) * 0.9
    low = filt(sos_lp(250, 3), brown(N)) * 0.25
    d = drops(N, 900, 1200, 7000) * 0.35
    return (base + low + d) * slow_mod(N, 0.12, [23, 41, 67])


# 2. Tormenta
def tormenta():
    base = filt(sos_bp(150, 10000, 3), pink(N))
    low = filt(sos_lp(300, 3), brown(N)) * 0.45
    d = drops(N, 2500, 800, 8000) * 0.45
    return (base + low + d) * slow_mod(N, 0.2, [17, 31, 53])


# 3. Lluvia en la ventana (gotas más marcadas, menos "siseo")
def ventana():
    base = filt(sos_bp(400, 6000, 3), pink(N)) * 0.45
    d = drops(N, 400, 900, 5000, decay_ms=(4, 18)) * 0.9
    return (base + d) * slow_mod(N, 0.15, [29, 47, 71])


# 4. Mar
def mar():
    t = np.arange(N) / SR
    env = np.zeros(N)
    pos = rng.uniform(0, 4)
    while pos < N / SR:
        per = rng.uniform(8, 13)
        c = pos + per * 0.55
        rise = per * 0.5
        fall = per * 0.45
        e = np.where(t < c, np.exp(-((t - c) / (rise / 2.2)) ** 2), np.exp(-((t - c) / (fall / 2.6)) ** 2))
        env += e * rng.uniform(0.6, 1.0)
        pos += per
    env = 0.15 + env
    low = filt(sos_lp(600, 3), pink(N)) * env
    hiss = filt(sos_bp(1500, 9000, 3), pink(N)) * (env ** 1.3) * 0.5
    rumble = filt(sos_lp(120, 3), brown(N)) * 0.3
    return low + hiss + rumble


# 5. Ruido marrón
def marron():
    return filt(sos_lp(900, 2), brown(N))


ONLY = sys.argv[2:]
if not ONLY or "lluvia-suave" in ONLY: save("lluvia-suave", stereo_pair(lluvia_suave))

# tormenta: truenos iguales en ambos canales (con leve diferencia), lejos del empalme
if not ONLY or "tormenta" in ONLY:
  tor = stereo_pair(tormenta)
  times = [38, 112, 181, 247]
  th = thunder(N, times)
  tor[:, 0] += th * 1.4
  tor[:, 1] += np.roll(th, int(0.012 * SR)) * 1.3
  save("tormenta", tor)

if not ONLY or "ventana" in ONLY: save("ventana", stereo_pair(ventana))
if not ONLY or "mar" in ONLY: save("mar", stereo_pair(mar))
if not ONLY or "ruido-marron" in ONLY: save("ruido-marron", stereo_pair(marron))
