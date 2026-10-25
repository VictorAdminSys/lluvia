"""Lluvia sobre el techo de un coche, oída desde dentro. Versión limpia.

Cada gota es un golpe sintetizado (senos amortiguados = vibración de la chapa),
con su propio tono, fuerza y posición estéreo. Sin capa de siseo: el fondo es
solo un murmullo grave muy bajo. Bucle de 5 min sin cortes.
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import sys

SR = 44100
DUR = 300
FADE = 4
N = (DUR + FADE) * SR
rng = np.random.default_rng(77)


def lp(f, o=4):
    return signal.butter(o, f, btype="low", fs=SR, output="sos")


def hp(f, o=2):
    return signal.butter(o, f, btype="high", fs=SR, output="sos")


def brown(n):
    b = signal.sosfilt(hp(20), np.cumsum(rng.standard_normal(n)))
    return b / np.std(b)


def golpe(f_alto, f_bajo, decay_ms, peso_bajo):
    """Una gota: 'tic' agudo de la chapa + cuerpo grave + un clic de 1 ms."""
    L = int(SR * decay_ms / 1000 * 6)
    t = np.arange(L) / SR
    d = decay_ms / 1000
    k = (np.sin(2 * np.pi * f_alto * t) * np.exp(-t / d)
         + 0.6 * np.sin(2 * np.pi * f_alto * rng.uniform(1.4, 1.7) * t) * np.exp(-t / (d * 0.6))
         + peso_bajo * np.sin(2 * np.pi * f_bajo * t) * np.exp(-t / (d * 1.6)))
    clic = rng.standard_normal(L) * np.exp(-t / 0.0007) * 0.5
    k = k + clic
    k[: int(SR * 0.0004)] *= np.linspace(0, 1, int(SR * 0.0004))  # ataque sin chasquido
    return k / np.abs(k).max()


def capa_gotas(n, rate, protos, amp_rango, pan_l):
    """Reparte 'rate' gotas por segundo entre varios prototipos de golpe."""
    out = np.zeros(n)
    k = rng.poisson(rate * n / SR)
    pos = rng.integers(0, n, k)
    amp = rng.uniform(*amp_rango, k) ** 2          # muchas suaves, pocas fuertes
    amp *= pan_l[rng.integers(0, len(pan_l), k)]   # posición en el techo
    cual = rng.integers(0, len(protos), k)
    for i, p in enumerate(protos):
        sel = cual == i
        imp = np.zeros(n)
        np.add.at(imp, pos[sel], amp[sel])
        out += signal.fftconvolve(imp, p)[:n]
    return out


# prototipos compartidos por los dos canales (es el mismo techo)
protos_techo = [golpe(rng.uniform(1100, 2600), rng.uniform(260, 520), rng.uniform(10, 22), rng.uniform(0.3, 0.7))
                for _ in range(28)]
protos_gordas = [golpe(rng.uniform(500, 900), rng.uniform(150, 260), rng.uniform(25, 45), 1.0) for _ in range(8)]
protos_fino = [golpe(rng.uniform(2500, 4200), rng.uniform(600, 900), rng.uniform(4, 8), 0.2) for _ in range(16)]


def canal(lado):
    # ganancia por posición: cada gota cae más a la izquierda o a la derecha
    pan = np.linspace(0.25, 1.0, 9) if lado == 0 else np.linspace(1.0, 0.25, 9)
    techo = capa_gotas(N, 70, protos_techo, (0.25, 1.0), pan)
    gordas = capa_gotas(N, 0.5, protos_gordas, (0.6, 1.0), pan) * 1.1
    fino = capa_gotas(N, 150, protos_fino, (0.1, 0.4), pan) * 0.45
    murmullo = signal.sosfilt(lp(220, 4), brown(N)) * 0.06
    x = techo + gordas + fino + murmullo
    return signal.sosfilt(lp(6500, 2), x)


def make_loop(x):
    F, L = FADE * SR, DUR * SR
    th = np.linspace(0, np.pi / 2, F)[:, None]
    y = x[:L].copy()
    y[:F] = x[:F] * np.sin(th) + x[L:L + F] * np.cos(th)
    return y


def finish(x, rms_db=-23.0):
    x = x - x.mean(axis=0)
    x *= 10 ** (rms_db / 20) / np.sqrt(np.mean(x ** 2))
    x = np.tanh(x * 1.1) / 1.1
    pk = np.abs(x).max()
    return x * (0.92 / pk) if pk > 0.92 else x


# Las mismas gotas en ambos canales pero con distinta posición:
# se reutiliza la semilla para que coincidan los instantes.
estado = rng.bit_generator.state
izq = canal(0)
rng.bit_generator.state = estado
der = canal(1)
x = finish(make_loop(np.stack([izq, der], axis=1)))
wavfile.write(sys.argv[1], SR, (x * 32767).astype(np.int16))
print("ok")
