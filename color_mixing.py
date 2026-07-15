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
    force_blend: bool = False,
) -> tuple[dict[str, float], float, str]:
    """
    Find optimal shelf-tube weights to minimise ΔE to target_hex.

    Pool sizes per component count (catches cross-hue combos like Yellow+Cyan→Green):
        n=1 : all tubes
        n=2 : all tubes  (fast SLSQP, cross-hue pairs matter)
        n=3 : top 20
        n=4 : top 12
        n=5 : top 8

    force_blend: when True each blend component is constrained to >= MIN_BLEND_FRAC
    so the optimizer is forced to find meaningful proportions.  Any recipe with a
    component < MIN_BLEND_FRAC would be impractical to measure anyway.  This also
    guarantees that no component is dropped by the post-filter, so the returned
    recipe is always 2+ tubes when a valid blend was found.

    Returns:
        recipe     – {tube_name: weight_fraction}, fractions sum to 1
        de         – achieved ΔE (CIE76)
        predicted  – hex code of the KM-predicted mixture
    """
    MIN_BLEND_FRAC = 0.08   # each blend ingredient must be >= 8 %
    DROP_THRESHOLD = 0.05   # single-tube path: drop < 5% (unused in blend path)

    tubes = list(tube_hex_map.keys())
    linears = np.array([hex_to_linear(h) for h in tube_hex_map.values()])
    target_lab = hex_to_lab(target_hex)

    tube_labs = [_linear_to_lab(lin) for lin in linears]
    tube_de = [delta_e(target_lab, lab) for lab in tube_labs]
    ranked = sorted(range(len(tubes)), key=lambda i: tube_de[i])

    pool_limits = {1: len(tubes), 2: len(tubes), 3: 20, 4: 12, 5: 8}

    best_single_recipe: dict[str, float] = {tubes[ranked[0]]: 1.0}
    best_single_de = tube_de[ranked[0]]
    best_single_lin = linears[ranked[0]]

    best_blend_recipe: dict[str, float] | None = None
    best_blend_de = float("inf")
    best_blend_lin: np.ndarray | None = None

    for n in range(1, max_components + 1):
        pool = ranked[:min(pool_limits.get(n, 8), len(tubes))]
        for combo in combinations(pool, n):
            combo_lin = linears[list(combo)]

            if n == 1:
                de_val = tube_de[combo[0]]
                if de_val < best_single_de:
                    best_single_de = de_val
                    best_single_lin = combo_lin[0]
                    best_single_recipe = {tubes[combo[0]]: 1.0}
                continue

            # Lower bound per component: 0 for accuracy-first mode,
            # MIN_BLEND_FRAC for force_blend so every ingredient is
            # measurable and survives the drop filter below.
            lb = MIN_BLEND_FRAC if force_blend else 0.0
            x0 = np.ones(n) / n
            try:
                res = minimize(
                    _objective,
                    x0,
                    args=(combo_lin, target_lab),
                    method="SLSQP",
                    bounds=[(lb, 1.0)] * n,
                    constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
                    options={"ftol": 1e-7, "maxiter": 200},
                )
                w = np.clip(res.x, lb, 1.0)
                w /= w.sum()
                mixed = km_predict(combo_lin, w)
                de_val = delta_e(_linear_to_lab(mixed), target_lab)
                if de_val < best_blend_de:
                    best_blend_de = de_val
                    best_blend_lin = mixed
                    best_blend_recipe = {tubes[combo[i]]: float(w[j]) for j, i in enumerate(combo)}
            except Exception:
                pass

    # Prefer blend when it wins on ΔE, or when caller needs a recipe
    use_blend = best_blend_recipe is not None and (
        best_blend_de < best_single_de
        or (force_blend and best_single_de > 3)
    )

    if use_blend:
        best_recipe, best_de, best_lin = best_blend_recipe, best_blend_de, best_blend_lin
    else:
        best_recipe, best_de, best_lin = best_single_recipe, best_single_de, best_single_lin

    # Drop negligible ingredients (only relevant for non-force_blend path)
    if len(best_recipe) > 1:
        best_recipe = {k: v for k, v in best_recipe.items() if v >= DROP_THRESHOLD}
        total = sum(best_recipe.values())
        best_recipe = {k: v / total for k, v in best_recipe.items()}

    return best_recipe, best_de, linear_to_hex(best_lin)
