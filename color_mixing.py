"""
Kubelka-Munk paint-mixing optimiser.

The square-root weighting model is a well-known approximation of full KM theory
that works from reflectance values (i.e. tube hex codes) without needing per-pigment
absorption/scattering spectra.  It gives substantially better predictions than linear
RGB blending for opaque paint systems.

  mixed_linear[c] = ( Σ wᵢ · √linearRGB(tubeᵢ)[c] )²

We minimise ΔE (CIE 76) in L*a*b* space between the predicted mix and the target.
"""

from __future__ import annotations
import numpy as np
from itertools import combinations
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Colour-space helpers
# ---------------------------------------------------------------------------

def _srgb_to_linear(v: np.ndarray) -> np.ndarray:
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(v: np.ndarray) -> np.ndarray:
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)


_M_RGB_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_D65 = np.array([0.95047, 1.00000, 1.08883])


def _linear_to_lab(rgb_lin: np.ndarray) -> np.ndarray:
    xyz = _M_RGB_XYZ @ rgb_lin
    t = xyz / _D65
    f = np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    L = 116 * f[1] - 16
    a = 500 * (f[0] - f[1])
    b = 200 * (f[1] - f[2])
    return np.array([L, a, b])


def hex_to_linear(hex_code: str) -> np.ndarray:
    h = hex_code.lstrip("#")
    rgb = np.array([int(h[i: i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return _srgb_to_linear(rgb)


def hex_to_lab(hex_code: str) -> np.ndarray:
    return _linear_to_lab(hex_to_linear(hex_code))


def linear_to_hex(lin: np.ndarray) -> str:
    srgb = np.clip(_linear_to_srgb(np.clip(lin, 0, 1)) * 255, 0, 255).astype(int)
    return "#{:02X}{:02X}{:02X}".format(*srgb)


def delta_e(lab1: np.ndarray, lab2: np.ndarray) -> float:
    return float(np.linalg.norm(lab1 - lab2))


# ---------------------------------------------------------------------------
# KM mixing model
# ---------------------------------------------------------------------------

def km_predict(tube_linears: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Square-root KM mixing: returns linear RGB of the mixture."""
    sqrt_tubes = np.sqrt(np.clip(tube_linears, 0, 1))
    return np.clip((weights @ sqrt_tubes) ** 2, 0, 1)


def _objective(weights: np.ndarray, tube_linears: np.ndarray, target_lab: np.ndarray) -> float:
    w = np.clip(weights, 0, 1)
    s = w.sum()
    if s < 1e-9:
        return 1e6
    w = w / s
    mixed_lab = _linear_to_lab(km_predict(tube_linears, w))
    return float(np.sum((mixed_lab - target_lab) ** 2))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_best_mix(
    target_hex: str,
    tube_hex_map: dict[str, str],
    max_components: int = 3,
) -> tuple[dict[str, float], float, str]:
    """
    Find optimal shelf-tube weights to minimise ΔE to target_hex.

    Returns:
        recipe     – {tube_name: weight_fraction}, fractions sum to 1
        de         – achieved ΔE (CIE76) — lower is better; <5 visually close
        predicted  – hex code of the KM-predicted mixture
    """
    tubes = list(tube_hex_map.keys())
    linears = np.array([hex_to_linear(h) for h in tube_hex_map.values()])
    target_lab = hex_to_lab(target_hex)

    # Per-tube distance — rank candidates
    tube_labs = [_linear_to_lab(lin) for lin in linears]
    tube_de = [delta_e(target_lab, lab) for lab in tube_labs]
    ranked = sorted(range(len(tubes)), key=lambda i: tube_de[i])

    # Cap candidate pool to 8 closest tubes (keeps combination count reasonable)
    pool = ranked[:min(8, len(tubes))]

    best_recipe: dict[str, float] = {tubes[ranked[0]]: 1.0}
    best_de = tube_de[ranked[0]]
    best_lin = linears[ranked[0]]

    for n in range(1, max_components + 1):
        for combo in combinations(pool, n):
            combo_lin = linears[list(combo)]

            if n == 1:
                de_val = tube_de[combo[0]]
                if de_val < best_de:
                    best_de = de_val
                    best_lin = combo_lin[0]
                    best_recipe = {tubes[combo[0]]: 1.0}
                continue

            x0 = np.ones(n) / n
            try:
                res = minimize(
                    _objective,
                    x0,
                    args=(combo_lin, target_lab),
                    method="SLSQP",
                    bounds=[(0.0, 1.0)] * n,
                    constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                    options={"ftol": 1e-7, "maxiter": 200},
                )
                w = np.clip(res.x, 0, 1)
                w /= w.sum()
                mixed = km_predict(combo_lin, w)
                de_val = delta_e(_linear_to_lab(mixed), target_lab)
                if de_val < best_de:
                    best_de = de_val
                    best_lin = mixed
                    best_recipe = {tubes[combo[i]]: float(w[j]) for j, i in enumerate(combo)}
            except Exception:
                pass

    # Drop ingredients below 5% (too small to measure accurately)
    if len(best_recipe) > 1:
        best_recipe = {k: v for k, v in best_recipe.items() if v >= 0.05}
        total = sum(best_recipe.values())
        best_recipe = {k: v / total for k, v in best_recipe.items()}

    return best_recipe, best_de, linear_to_hex(best_lin)
