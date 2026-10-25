"""Lluvia sobre el techo de un coche, oída desde dentro. Bucle de 5 min sin cortes."""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import sys

SR = 44100
DUR = 300
FADE = 4
N = (DUR + FADE) * SR
rng = np.random.default_rng(2026)


def sosf(sos, x):
    return signal.sosfilt(sos, x)


def lp(f, o=4):
    return signal.butter(o, f, btype="low", fs=SR, output="sos")


def hp(f, o=2):
    return signal.butter(o, f, btype="high", fs=SR, output="sos")


def bp(lo, hi, o=2):
    return signal.butter(o, [lo, hi], btype="band", fs=SR, output="sos")


def pink(n):
    f = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    fr[0] = fr[1]
    p = np.fft.irfft(f / np.sqrt(fr), n)
    return p / np.std(p)


def brown(n):
    b = sosf(hp(20), np.cumsum(rng.standard_normal(n)))
    return b / np.std(b)


def slow_mod(n, depth, periods):
    t = np.arange(n) / SR
    m = sum(np.sin(2 * np.pi * t / p + rng.uniform(0, 6.28)) for p in periods) / len(periods)
    return 1 + depth * m


def impulses(n, rate, amp_max=1.0):
    k = rng.poisson(rate * n / SR)
    imp = np.zeros(n)
    np.add.at(imp, rng.integers(0, n, k), np.minimum(rng.pareto(4.0, k) + 0.25, amp_max))
    return imp


def resonate(x, freqs, q):
    """Banco de resonadores: modos de vibración de la chapa del techo."""
    out = np.zeros_like(x)
    for f in freqs:
        b, a = signal.iirpeak(f, q * rng.uniform(0.8, 1.2), fs=SR)
        out += signal.lfilter(b, a, x) * rng.uniform(0.6, 1.0)
    return out


def tick_kernel(ms):
    L = int(SR * ms / 1000 * 5)
    t = np.arange(L) / SR
    return rng.standard_normal(L) * np.exp(-t / (ms / 1000))


def canal():
    # 1) Lluvia exterior amortiguada por el habitáculo
    fondo = sosf(lp(1400, 4), pink(N)) * 0.55 + sosf(lp(180, 2), brown(N)) * 0.35

    # 2) Golpeteo denso sobre el techo: impulsos -> clic corto -> modos metálicos
    gotas = signal.fftconvolve(impulses(N, 450), tick_kernel(1.2))[:N]
    techo = resonate(gotas, [290, 470, 690, 960, 1330, 1870, 2600], q=7)
    techo = sosf(lp(3200, 4), techo)
    techo /= np.std(techo)

    # 3) Patter en el parabrisas (cristal: más agudo, más seco, más suave)
    cristal = signal.fftconvolve(impulses(N, 220), tick_kernel(0.8))[:N]
    cristal = sosf(bp(1500, 4500), cristal)
    cristal /= np.std(cristal)

    # 4) Gotas gordas de los árboles: escasas, graves, con algo de cola
    gordas = signal.fftconvolve(impulses(N, 0.6, amp_max=1.0), tick_kernel(4))[:N]
    gordas = resonate(gordas, [180, 260, 410, 640], q=12)
    gordas = sosf(lp(1800, 2), gordas)
    gordas /= (np.std(gordas) + 1e-9)

    mezcla = fondo * 0.8 + techo * 1.0 + cristal * 0.3 + gordas * 0.18
    # resonancia de la cabina (caja cerrada)
    b, a = signal.iirpeak(140, 2.0, fs=SR)
    mezcla = mezcla + signal.lfilter(b, a, mezcla) * 0.4
    mezcla = sosf(lp(5000, 4), mezcla)  # todo se oye desde dentro
    return mezcla * slow_mod(N, 0.18, [19, 37, 61])


def make_loop(x):
    F, L = FADE * SR, DUR * SR
    th = np.linspace(0, np.pi / 2, F)[:, None]
    y = x[:L].copy()
    y[:F] = x[:F] * np.sin(th) + x[L:L + F] * np.cos(th)
    return y


def finish(x, rms_db=-21.0):
    x = x - x.mean(axis=0)
    x *= 10 ** (rms_db / 20) / np.sqrt(np.mean(x ** 2))
    x = np.tanh(x * 1.2) / 1.2
    pk = np.abs(x).max()
    return x * (0.95 / pk) if pk > 0.95 else x


x = np.stack([canal(), canal()], axis=1)
x = finish(make_loop(x))
wavfile.write(sys.argv[1], SR, (x * 32767).astype(np.int16))
print("ok")
