import colorsys
from pigment_data import lookup

_DENSITY_SCORE = {"heavy": 3, "medium": 2, "light": 1}
_COMPLEMENTARY_MIN, _COMPLEMENTARY_MAX = 150, 210


def _hex_to_hue(hex_code: str) -> float:
    hex_code = hex_code.lstrip("#")
    r, g, b = (int(hex_code[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)
    return h * 360


def _behavior_for_score(score: float, metallic: bool) -> str:
    if metallic:
        return "Floats (metallic sheen)"
    if score >= 2.5:
        return "Sinks"
    if score <= 1.5:
        return "Floats"
    return "Suspends"


def analyze_palette_pigments(colors) -> dict | None:
    """colors: list of objects with .name, .hex_code, .mix_recipe (each with .tube, .grams)."""
    if not colors:
        return None

    per_color = []
    for c in colors:
        ingredients = c.mix_recipe or []
        tinting_tubes = []
        metallic = False
        if ingredients:
            total_grams = sum(ing.grams for ing in ingredients) or 1
            score = sum(
                _DENSITY_SCORE.get(lookup(ing.tube).get("density", "medium"), 2) * ing.grams
                for ing in ingredients
            ) / total_grams
            for ing in ingredients:
                data = lookup(ing.tube)
                if data.get("tinting_strength") == "high":
                    tinting_tubes.append(ing.tube)
                if data.get("metallic"):
                    metallic = True
        else:
            data = lookup(c.name)
            score = _DENSITY_SCORE.get(data.get("density", "medium"), 2)
            if data.get("tinting_strength") == "high":
                tinting_tubes.append(c.name)
            metallic = bool(data.get("metallic"))

        density = "heavy" if score >= 2.5 else ("light" if score <= 1.5 else "medium")
        behavior = _behavior_for_score(score, metallic)

        mudding_risk = None
        if len(tinting_tubes) >= 2:
            mudding_risk = (
                f"Combines multiple high-strength tinting pigments ({', '.join(tinting_tubes)}) "
                f"— mix gradually and test a small amount first."
            )
        elif metallic:
            mudding_risk = "Metallic/pearlescent — can dull neighboring colors if over-mixed; keep it as an accent."

        per_color.append({
            "color_name": c.name,
            "hex_code": c.hex_code,
            "score": score,
            "density": density,
            "behavior": behavior,
            "mudding_risk": mudding_risk,
            "tinting_tubes": tinting_tubes,
        })

    pour_order = [p["color_name"] for p in sorted(per_color, key=lambda p: -p["score"])]

    warnings = []
    for i in range(len(per_color)):
        for j in range(i + 1, len(per_color)):
            a, b = per_color[i], per_color[j]
            if not a["tinting_tubes"] or not b["tinting_tubes"]:
                continue
            diff = abs(_hex_to_hue(a["hex_code"]) - _hex_to_hue(b["hex_code"]))
            diff = min(diff, 360 - diff)
            if _COMPLEMENTARY_MIN <= diff <= _COMPLEMENTARY_MAX:
                warnings.append(
                    f"\"{a['color_name']}\" and \"{b['color_name']}\" are near-complementary and both "
                    f"high-tinting — if they blend directly during the pour they'll likely turn muddy "
                    f"grey/brown. Keep a buffer color between them or pour them apart."
                )

    return {
        "pour_order": pour_order,
        "notes": [
            {"color_name": p["color_name"], "hex_code": p["hex_code"], "density": p["density"],
             "behavior": p["behavior"], "mudding_risk": p["mudding_risk"]}
            for p in per_color
        ],
        "warnings": warnings,
    }
