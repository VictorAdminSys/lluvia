"""Ruido blanco estéreo, bucle de 5 min sin cortes.
Plano en todo el espectro; solo se suaviza por encima de 14 kHz para que no pinche."""
import numpy as np
from scipy import signal
from scipy.io import wavfile
import sys

SR = 44100
DUR = 300
FADE = 4
N = (DUR + FADE) * SR
rng = np.random.default_rng(11)

x = rng.standard_normal((N, 2))
x = signal.sosfilt(signal.butter(2, 14000, btype="low", fs=SR, output="sos"), x, axis=0)
x = signal.sosfilt(signal.butter(1, 30, btype="high", fs=SR, output="sos"), x, axis=0)

F, L = FADE * SR, DUR * SR
th = np.linspace(0, np.pi / 2, F)[:, None]
y = x[:L].copy()
y[:F] = x[:F] * np.sin(th) + x[L:L + F] * np.cos(th)

y *= 10 ** (-25 / 20) / np.sqrt(np.mean(y ** 2))   # algo más bajo que el resto: el blanco cansa
y = np.clip(y, -0.95, 0.95)
wavfile.write(sys.argv[1], SR, (y * 32767).astype(np.int16))
print("ok")
