"""
Kubelka-Munk paint-mixing model.

Square-root weighting approximation — works from tube hex codes as reflectance
estimates without needing per-pigment spectral data.

  mixed_linear[c] = ( Σ wᵢ · √linearRGB(tubeᵢ)[c] )²
"""

from __future__ import annotations
import numpy as np
from itertools import combinations
from scipy.optimize import minimize_scalar, minimize


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


def _de_of_mix(lins: np.ndarray, weights: np.ndarray, target_lab: np.ndarray) -> tuple[float, np.ndarray]:
    mixed = km_predict(lins, weights)
    return delta_e(_linear_to_lab(mixed), target_lab), mixed


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
    Find the best recipe from tube_hex_map to approximate target_hex.

    Strategy:
    - n=1: pick the closest single tube (baseline)
    - n=2: 1-D bounded optimisation (Brent) over ALL pairs — catches
           cross-hue combos (e.g. Yellow+Cyan → Teal) that a naïve
           closest-to-target pool would miss
    - n=3: grid search over top-15 pool, then SLSQP refinement from
           the best grid point

    force_blend: if True and best single-tube ΔE > 3, always return a
    multi-tube recipe even when it has a slightly higher ΔE — the user
    asked for a mixing recipe, not a tube-identification answer.

    Every blend component is constrained to ≥ MIN_FRAC so nothing is
    too small to measure and the recipe is actionable.
    """
    MIN_FRAC = 0.10  # minimum fraction per blend component (10 %)

    tubes = list(tube_hex_map.keys())
    n_tubes = len(tubes)
    linears = np.array([hex_to_linear(h) for h in tube_hex_map.values()])
    target_lab = hex_to_lab(target_hex)

    tube_de_vals = [delta_e(target_lab, _linear_to_lab(lin)) for lin in linears]
    ranked = sorted(range(n_tubes), key=lambda i: tube_de_vals[i])

    # ---- best single tube ----
    best_single_idx = ranked[0]
    best_single_de = tube_de_vals[best_single_idx]
    best_single_lin = linears[best_single_idx]

    # ---- best blend ----
    best_blend_recipe: dict[str, float] | None = None
    best_blend_de = float("inf")
    best_blend_lin: np.ndarray | None = None

    # n=2: 1-D Brent optimisation over every pair
    if max_components >= 2 and n_tubes >= 2:
        for i, j in combinations(range(n_tubes), 2):
            lins_ij = np.stack([linears[i], linears[j]])

            def obj_1d(w1, lins=lins_ij):
                w = np.array([w1, 1.0 - w1])
                return float(np.sum((_linear_to_lab(km_predict(lins, w)) - target_lab) ** 2))

            try:
                res = minimize_scalar(obj_1d, bounds=(MIN_FRAC, 1.0 - MIN_FRAC), method="bounded")
                w1 = float(np.clip(res.x, MIN_FRAC, 1.0 - MIN_FRAC))
                w = np.array([w1, 1.0 - w1])
                de_val, mixed = _de_of_mix(lins_ij, w, target_lab)
                if de_val < best_blend_de:
                    best_blend_de = de_val
                    best_blend_lin = mixed
                    best_blend_recipe = {tubes[i]: w1, tubes[j]: 1.0 - w1}
            except Exception:
                pass

    # n=3: grid search (step 10 %) + SLSQP refinement
    if max_components >= 3 and n_tubes >= 3:
        pool = ranked[:min(15, n_tubes)]
        STEP = 0.10
        best_grid_keys: tuple | None = None
        best_grid_w: np.ndarray | None = None

        for combo in combinations(pool, 3):
            lins_c = linears[list(combo)]
            # iterate over the simplex at step resolution
            w1 = STEP
            while w1 <= 1.0 - 2 * STEP + 1e-9:
                w2 = STEP
                while w2 <= 1.0 - w1 - STEP + 1e-9:
                    w3 = 1.0 - w1 - w2
                    if w3 >= STEP - 1e-9:
                        w = np.array([w1, w2, w3])
                        de_val, mixed = _de_of_mix(lins_c, w, target_lab)
                        if de_val < best_blend_de:
                            best_blend_de = de_val
                            best_blend_lin = mixed
                            best_blend_recipe = {tubes[combo[k]]: float(w[k]) for k in range(3)}
                            best_grid_keys = combo
                            best_grid_w = w.copy()
                    w2 += STEP
                w1 += STEP

        # Refine the best 3-component grid result with SLSQP
        if best_grid_keys is not None and best_grid_w is not None:
            lins_best = linears[list(best_grid_keys)]

            def obj_3d(ww, lins=lins_best):
                ww = np.clip(ww, 0, 1)
                s = ww.sum()
                if s < 1e-9:
                    return 1e6
                return float(np.sum((_linear_to_lab(km_predict(lins, ww / s)) - target_lab) ** 2))

            try:
                res3 = minimize(
                    obj_3d, best_grid_w,
                    method="SLSQP",
                    bounds=[(MIN_FRAC, 1.0)] * 3,
                    constraints={"type": "eq", "fun": lambda ww: ww.sum() - 1},
                    options={"ftol": 1e-8, "maxiter": 300},
                )
                w_opt = np.clip(res3.x, MIN_FRAC, 1.0)
                w_opt /= w_opt.sum()
                de_opt, mixed_opt = _de_of_mix(lins_best, w_opt, target_lab)
                if de_opt < best_blend_de:
                    best_blend_de = de_opt
                    best_blend_lin = mixed_opt
                    best_blend_recipe = {tubes[best_grid_keys[k]]: float(w_opt[k]) for k in range(3)}
            except Exception:
                pass

    # ---- decide: single or blend ----
    use_blend = best_blend_recipe is not None and (
        best_blend_de < best_single_de
        or (force_blend and best_single_de > 3)
    )

    if use_blend:
        return best_blend_recipe, best_blend_de, linear_to_hex(best_blend_lin)
    else:
        return {tubes[best_single_idx]: 1.0}, best_single_de, linear_to_hex(best_single_lin)
