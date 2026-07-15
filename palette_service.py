import os
import re
import random
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict
from color_mixing import find_best_mix

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-5",
    max_tokens=4096,
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

suggest_llm = ChatAnthropic(
    model="claude-sonnet-5",
    max_tokens=8192,
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

parser = JsonOutputParser()

# --- Palette generation with LangGraph ---

palette_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for artists, especially acrylic pour painters.
When given a mood, theme, or description, respond ONLY with a JSON object containing:
1. "colors": an array of exactly {num_colors} colors, each with:
   - hexCode: a valid hex color
   - colorName: if the mixRecipe uses only one tube, the colorName MUST be exactly that tube's name (e.g. "Titanium White 105", "Phthalo Green 675"). When mixing two or more tubes, use the commonly recognized color name for the resulting mix (e.g. "Sage Green", "Teal", "Dusty Rose").
   - emotionalDescription: the mood this color evokes
   - pourRatio: the recommended percentage of this color in the pour as a whole number (all {num_colors} must add up to 100). Consider which colors should dominate as base vs accent.
   - mixRecipe: an array of ingredients to mix using Royal Talens Amsterdam Standard Series acrylic tubes to approximate this color. Each ingredient has:
     - tube: the paint name and number (e.g. "Burnt Umber 409")
     - tubeHex: the approximate hex color of that tube straight from the bottle (e.g. "#5C4033")
     - grams: amount in grams as a number (use realistic amounts totaling 15-25g per color, good for a single pour cup layer)
   Mix 2-4 tubes per color to create interesting intermediary tones. Only use a single tube when it is a perfect match with no room for improvement.
   IMPORTANT: the {num_colors} colors MUST span at least 3 clearly distinct hue families (e.g. not all blues, not all earth tones). Include meaningful contrast across the palette.
2. "technique": an object with:
   - "name": the recommended acrylic pour technique
   - "reason": one sentence explaining why this technique suits these colors
   - "tip": one practical tip for executing this technique with this specific palette
No other text, no markdown, no explanation. Just the JSON object.
Example format:
{{"colors": [{{"hexCode": "#8B6914", "colorName": "Warm Ochre", "emotionalDescription": "Warm earthy grounding tone", "pourRatio": 35, "mixRecipe": [{{"tube": "Yellow Ochre 227", "tubeHex": "#C8A63C", "grams": 12}}, {{"tube": "Burnt Umber 409", "tubeHex": "#5C4033", "grams": 5}}, {{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 3}}]}}, {{"hexCode": "#FAFAFA", "colorName": "Titanium White 105", "emotionalDescription": "Clean and pure", "pourRatio": 20, "mixRecipe": [{{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 20}}]}}], "technique": {{"name": "Dirty Pour", "reason": "The earthy tones blend naturally with organic movement.", "tip": "Layer the darkest color first in your cup for depth."}}}}"""),
    ("human", "Generate a color palette for: {prompt}. Use exactly {num_colors} colors.")
])

retry_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert. Your previous response was invalid.
You MUST respond with ONLY a JSON object containing:
1. "colors": an array of exactly {num_colors} colors, each with hexCode, colorName (if single tube, MUST be exactly the tube name like "Titanium White 105"; if mixed, use a real color name like "Sage Green"), emotionalDescription, pourRatio (percentage, all {num_colors} add to 100), and mixRecipe (array of {{tube, tubeHex, grams}} using Amsterdam Standard Series)
2. "technique": an object with name, reason, and tip
hexCode MUST be a valid hex color starting with #, exactly 7 characters.
Example:
{{"colors": [{{"hexCode": "#8B6914", "colorName": "Warm Ochre", "emotionalDescription": "Earthy tone", "pourRatio": 35, "mixRecipe": [{{"tube": "Yellow Ochre 227", "tubeHex": "#C8A63C", "grams": 12}}, {{"tube": "Burnt Umber 409", "tubeHex": "#5C4033", "grams": 5}}]}}, {{"hexCode": "#FAFAFA", "colorName": "Titanium White 105", "emotionalDescription": "Pure and clean", "pourRatio": 20, "mixRecipe": [{{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 20}}]}}], "technique": {{"name": "Dirty Pour", "reason": "These tones blend naturally.", "tip": "Layer darkest first."}}}}"""),
    ("human", "Generate a color palette for: {prompt}. Use exactly {num_colors} colors. Previous error: {error}")
])

palette_chain = palette_prompt | llm | parser
retry_chain = retry_prompt | llm | parser

palette_flood_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for acrylic pour painters.
The user has pre-selected {num_bases} flood base color(s). Add {num_accents} accent color(s) that harmonize for a split canvas pour.

Respond ONLY with a JSON object with:
1. "colors": exactly {num_colors} total. Include the base color(s) first (role="base", keep their hex exactly as given), then {num_accents} new accent colors (role="accent"). Each color:
   - hexCode: valid 7-char hex (use exact provided hex for base colors; choose harmonious hex for accents)
   - colorName: if single-tube mix, MUST be exactly that tube's name (e.g. "Titanium White 105"); if multi-tube, use a recognized color name
   - emotionalDescription: mood evoked
   - pourRatio: percentage (all {num_colors} must sum to 100; base colors typically 25–40% each)
   - role: "base" or "accent"
   - mixRecipe: Amsterdam Standard Series ingredients (tube, tubeHex, grams; 15–25g total per color)
2. "technique": {{name, reason, tip}} suited to a split canvas pour.
No other text. Just the JSON."""),
    ("human", "Palette mood: {prompt}\nBase colors:\n{base_color_desc}\nAdd {num_accents} accent color(s) that complement these for a split canvas pour.")
])

palette_flood_chain = palette_flood_prompt | llm | parser

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
REQUIRED_KEYS = {"hexCode", "colorName", "emotionalDescription"}


class PaletteState(TypedDict):
    prompt: str
    num_colors: int
    base_colors: list
    colors: list
    is_valid: bool
    error: str
    attempts: int


def generate(state: PaletteState) -> dict:
    nc = state.get("num_colors", 5)
    base_colors = state.get("base_colors") or []
    try:
        if base_colors:
            num_bases = len(base_colors)
            num_accents = max(1, nc - num_bases)
            base_desc = "\n".join(
                f"- {b.get('name', 'Color')} ({b.get('hex', '#888888')})"
                for b in base_colors
            )
            result = palette_flood_chain.invoke({
                "prompt": state["prompt"],
                "num_colors": num_bases + num_accents,
                "num_bases": num_bases,
                "num_accents": num_accents,
                "base_color_desc": base_desc,
            })
        elif state["attempts"] == 0:
            result = palette_chain.invoke({"prompt": state["prompt"], "num_colors": nc})
        else:
            result = retry_chain.invoke({
                "prompt": state["prompt"],
                "num_colors": nc,
                "error": state["error"]
            })
        return {"colors": result, "attempts": state["attempts"] + 1}
    except Exception as e:
        return {
            "colors": [],
            "attempts": state["attempts"] + 1,
            "error": str(e)
        }


def validate(state: PaletteState) -> dict:
    colors = state["colors"]

    if isinstance(colors, dict) and "colors" in colors:
        colors = colors["colors"]

    if not isinstance(colors, list):
        return {"is_valid": False, "error": "Response is not a list"}

    expected = state.get("num_colors", 5)
    if len(colors) != expected:
        return {"is_valid": False, "error": f"Expected {expected} colors, got {len(colors)}"}

    for i, color in enumerate(colors):
        if not isinstance(color, dict):
            return {"is_valid": False, "error": f"Color {i} is not an object"}

        missing = REQUIRED_KEYS - set(color.keys())
        if missing:
            return {"is_valid": False, "error": f"Color {i} missing keys: {missing}"}

        if not HEX_PATTERN.match(color["hexCode"]):
            return {"is_valid": False, "error": f"Color {i} has invalid hex: {color['hexCode']}"}

    return {"is_valid": True, "error": ""}


def should_retry(state: PaletteState) -> str:
    if state["is_valid"]:
        return "done"
    if state["attempts"] >= 3:
        return "fail"
    return "retry"


graph = StateGraph(PaletteState)
graph.add_node("generate", generate)
graph.add_node("validate", validate)
graph.set_entry_point("generate")
graph.add_edge("generate", "validate")
graph.add_conditional_edges("validate", should_retry, {
    "retry": "generate",
    "done": END,
    "fail": END
})

palette_graph = graph.compile()


def generate_palette(prompt: str, num_colors: int = 5, base_colors: list | None = None) -> dict:
    result = palette_graph.invoke({
        "prompt": prompt,
        "num_colors": num_colors,
        "base_colors": base_colors or [],
        "colors": [],
        "is_valid": False,
        "error": "",
        "attempts": 0
    })
    if not result["is_valid"]:
        raise Exception(f"Failed after 3 attempts: {result['error']}")
    raw = result["colors"]
    if isinstance(raw, dict) and "colors" in raw:
        return {"colors": raw["colors"], "technique": raw.get("technique", {})}
    return {"colors": raw, "technique": {}}


# --- Suggest palettes from the user's shelf ---

CREATIVE_DIRECTIONS = [
    "Explore moody, dramatic high-contrast combinations",
    "Focus on soft, dreamy pastel harmonies",
    "Push bold, vibrant saturated tones",
    "Embrace earthy, muted naturalistic hues",
    "Explore cool oceanic blues and teals",
    "Create warm sunset and fire palettes",
    "Combine cold and warm colors for visual tension",
    "Explore a forest and botanical theme",
    "Create a stormy, atmospheric palette",
    "Lean into metallic and pearlescent effects",
    "Explore deep jewel tones — emerald, sapphire, ruby",
    "Create a desert and mineral palette",
    "Explore complementary color harmony",
    "Go for a split-complementary triadic tension",
    "Create a misty, ethereal watercolour feel",
    "Explore retro 70s earth tones",
    "Go maximalist — clashing, unexpected combinations",
    "Create a minimalist palette with one dominant neutral",
    "Explore neon-adjacent vivid accents against darks",
]

suggest_standard_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for acrylic pour painters.
The user gives you a list of Royal Talens Amsterdam Standard Series tubes they own.
Suggest exactly 3 distinct pour palettes they can make using ONLY those tubes. You may mix tubes together to create new colors beyond the raw tubes.
Each of the 3 palettes MUST explore a completely different mood, style, and color range — do not repeat similar feels.
IMPORTANT RULES:
- Every palette must span at least 3 clearly distinct hue families — no near-monochromatic palettes.
- Mix 2-4 tubes per color to create interesting intermediary tones. Only use a single tube when it is a perfect match.
- Every tube in every mixRecipe MUST come from the user's provided list. Do not invent tubes they do not own.
Respond ONLY with a JSON object containing a "palettes" array of 3 palettes. Each palette has:
- "name": a short evocative name for the palette (e.g. "Autumn Embers")
- "mood": one short sentence describing the feeling of this palette
- "colors": an array of exactly {num_colors} colors, each with:
  - hexCode: a valid hex color
  - colorName: if the mixRecipe uses only one tube, MUST be exactly that tube's name. When mixing, use a recognized color name.
  - emotionalDescription: the mood this color evokes
  - pourRatio: percentage in the pour as a whole number (all {num_colors} add to 100)
  - mixRecipe: array of ingredients using ONLY tubes from the user's list. Each has tube, tubeHex, grams (totaling 15-25g).
- "technique": an object with name, reason, and tip
No other text, no markdown. Just the JSON object."""),
    ("human", "I own these Amsterdam Standard Series tubes: {tubes}. Suggest 3 palettes I can make with exactly {num_colors} colors each. Creative direction: {direction}. Be adventurous and avoid obvious or generic combinations.")
])

suggest_flood_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for acrylic pour painters who use a flood-and-accent technique.
The user floods their canvas with {num_bases} base color(s) first, then adds {num_accents} accent colors on top for contrast and interest.
The user gives you a list of Royal Talens Amsterdam Standard Series tubes they own.
Suggest exactly 3 distinct pour palettes using ONLY those tubes. Each palette MUST explore a completely different mood, style, and color range.
IMPORTANT RULES:
- Each palette has exactly {num_colors} colors: {num_bases} base(s) and {num_accents} accents.
- Base colors flood the canvas — they must be strong, intentional colors.
- The {num_accents} accent colors must contrast strongly against the base(s). No accent should visually disappear into a base.
- Every palette must span at least 3 clearly distinct hue families.
- Mix 2-4 tubes per color for interesting intermediary tones. Only use a single tube when it is a perfect match.
- Every tube in every mixRecipe MUST come from the user's provided list. Do not invent tubes they do not own.
Respond ONLY with a JSON object containing a "palettes" array of 3 palettes. Each palette has:
- "name": a short evocative name
- "mood": one short sentence describing the feeling
- "colors": an array of exactly {num_colors} colors, each with:
  - hexCode: a valid hex color
  - colorName: if the mixRecipe uses only one tube, MUST be exactly that tube's name. If mixed, use a recognized color name.
  - emotionalDescription: the mood this color evokes
  - role: "base" for flood colors (exactly {num_bases} per palette), "accent" for all others
  - pourRatio: percentage in the pour as a whole number (all {num_colors} add to 100). Each base 30-60%, accents share the remainder.
  - mixRecipe: array of ingredients using ONLY tubes from the user's list. Each has tube, tubeHex, grams. Base totals 40-60g, each accent totals 10-20g.
- "technique": an object with name, reason, and tip specific to the flood-and-accent style
No other text, no markdown. Just the JSON object."""),
    ("human", "I own these Amsterdam Standard Series tubes: {tubes}. Suggest 3 palettes with exactly {num_colors} colors each ({num_bases} base(s) + {num_accents} accents). {base_instruction} Creative direction: {direction}. Be adventurous and avoid obvious combinations.")
])

suggest_standard_chain = suggest_standard_prompt | suggest_llm | parser
suggest_flood_chain = suggest_flood_prompt | suggest_llm | parser

suggest_retry_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert. Your previous response was invalid JSON.
Respond ONLY with a valid JSON object (no markdown, no code blocks, no extra text) containing a "palettes" array of 3 palettes.
Each palette: name, mood, colors (array of {num_colors}), technique.
Each color: hexCode (#RRGGBB), colorName, emotionalDescription, pourRatio (int, all {num_colors} sum to 100), mixRecipe (array of {{tube, tubeHex, grams}}).
IMPORTANT: Every tube in every mixRecipe MUST come from the user's tube list. Do not invent tubes."""),
    ("human", "Tubes: {tubes}. Suggest 3 palettes with {num_colors} colors each. Previous error: {error}")
])

suggest_retry_chain = suggest_retry_prompt | suggest_llm | parser


def suggest_from_shelf(tubes: list, base_tubes: list | None = None, flood_mode: bool = False, num_colors: int = 5) -> dict:
    tube_list = ", ".join(tubes)
    direction = random.choice(CREATIVE_DIRECTIONS)
    base_tubes = base_tubes or []
    num_bases = max(1, len(base_tubes)) if flood_mode else 0
    num_accents = num_colors - num_bases

    for attempt in range(3):
        try:
            if attempt == 0:
                if flood_mode:
                    if not base_tubes:
                        base_instruction = (
                            f"You choose which of my tubes works best as the flood base color for each palette. "
                            f"Mark it with role 'base' and the other {num_accents} colors with role 'accent'. "
                            f"Choose accents that contrast strongly against the base."
                        )
                    elif len(base_tubes) == 1:
                        base_instruction = (
                            f"I want to use '{base_tubes[0]}' as my flood base — it covers the entire canvas first. "
                            f"Choose {num_accents} accent colors from my remaining tubes that contrast strongly against it. "
                            f"Mark '{base_tubes[0]}' with role 'base' and all other colors with role 'accent'."
                        )
                    else:
                        base_list = " and ".join(f"'{b}'" for b in base_tubes)
                        base_instruction = (
                            f"I want to use {base_list} as my {num_bases} flood bases — they cover the canvas in sections (split canvas). "
                            f"Mark all {num_bases} of them with role 'base'. "
                            f"Choose {num_accents} accent colors that work harmoniously across both bases and contrast meaningfully against at least one. "
                            f"Mark all accents with role 'accent'."
                        )
                    result = suggest_flood_chain.invoke({"tubes": tube_list, "direction": direction, "base_instruction": base_instruction, "num_colors": num_colors, "num_accents": num_accents, "num_bases": num_bases})
                else:
                    result = suggest_standard_chain.invoke({"tubes": tube_list, "direction": direction, "num_colors": num_colors})
            else:
                result = suggest_retry_chain.invoke({"tubes": tube_list, "error": last_error, "num_colors": num_colors})

            if isinstance(result, dict) and "palettes" in result:
                valid = [p for p in result["palettes"] if len(p.get("colors", [])) >= 4]
                if valid:
                    return {"palettes": valid[:3]}
                last_error = "Palettes array was empty or all palettes had fewer than 4 colors"
            else:
                last_error = f"Response missing 'palettes' key, got: {list(result.keys()) if isinstance(result, dict) else type(result)}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Failed to suggest palettes after 3 attempts: {last_error}")


# --- Color mixing with LangChain chain ---

mix_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color mixing expert for acrylic pour painters using the Royal Talens Amsterdam Standard Series.
When given two colors (either Amsterdam tube names like "Phthalo Blue 570" or hex codes), respond ONLY with a JSON object containing:
- resultHex: the approximate hex code of the mixed color
- resultName: a descriptive name for the mixed color
- description: how this mix would look in an acrylic pour
- pourTip: a practical tip for using this combination in acrylic pouring
No other text, no markdown. Just the JSON object."""),
    ("human", "What happens when you mix {color1} and {color2} in acrylic pouring?")
])

mix_chain = mix_prompt | llm | parser


def mix_colors(color1: str, color2: str) -> dict:
    return mix_chain.invoke({"color1": color1, "color2": color2})


# --- Complementary color suggestions ---

complement_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for acrylic pour painters.
The user has chosen {num_seed} seed color(s) for a pour palette and wants you to suggest exactly {num_suggestions} additional colors that complement them (via contrast, harmony, or accent) to round out a {num_total}-color palette.
Respond ONLY with a JSON object containing a "colors" array of exactly {num_suggestions} colors, each with:
- hexCode: a valid hex color
- colorName: if the mixRecipe uses only one tube, colorName MUST be exactly that tube's name (e.g. "Titanium White 105"). When mixing two or more tubes, use a commonly recognized color name for the mix.
- emotionalDescription: one short sentence on why this color complements the seed color(s)
- mixRecipe: an array of ingredients to mix using Royal Talens Amsterdam Standard Series acrylic tubes to approximate this color. Each ingredient has tube, tubeHex, grams (realistic amounts totaling 15-25g).
{shelf_instruction}
The {num_suggestions} suggestions should not be near-duplicates of each other or of the seed color(s) — offer real variety.
No other text, no markdown, no explanation. Just the JSON object."""),
    ("human", "Seed color(s): {seed_colors}. Suggest {num_suggestions} colors that complement them well for a {num_total}-color acrylic pour palette.")
])

complement_chain = complement_prompt | llm | parser


def suggest_complementary_colors(seed_colors: list, shelf_tubes: list | None = None, num_colors: int = 5) -> dict:
    num_suggestions = max(1, num_colors - len(seed_colors))
    seed_list = ", ".join(seed_colors)
    if shelf_tubes:
        tube_list = ", ".join(shelf_tubes)
        shelf_instruction = (
            f"The user owns these Amsterdam tubes: {tube_list}. Prefer mixRecipe combinations using ONLY these tubes. "
            f"If one of their tubes is already close to ideal on its own, suggest it directly as a single-tube mixRecipe."
        )
    else:
        shelf_instruction = "You may use any tube from the Amsterdam Standard Series."
    result = complement_chain.invoke({
        "num_seed": len(seed_colors),
        "num_suggestions": num_suggestions,
        "num_total": num_colors,
        "seed_colors": seed_list,
        "shelf_instruction": shelf_instruction
    })
    if isinstance(result, dict) and "colors" in result:
        return {"colors": result["colors"][:num_suggestions]}
    return {"colors": []}



# --- Mix from primaries: approximate any Amsterdam tube using only the 5 primaries ---


_UNMIXABLE_CATEGORIES = [
    (
        ["phthalo"],
        "Phthalo pigments are single-pigment specialty colors — the CMYK approximation gives a mixed green/blue that will look quite different from the real tube's characteristic transparent teal. Use this as a rough starting direction only.",
    ),
    (
        ["prussian"],
        "Prussian Blue is a single-pigment specialty color — the recipe is a rough approximation that won't capture the unique deep transparency and cool blue of the real tube.",
    ),
    (
        ["quinacridone"],
        "Quinacridone pigments have a unique transparent single-pigment chroma that cannot be reproduced from CMYK primaries — treat this recipe as a rough approximation only.",
    ),
    (
        ["reflex", "iridescent", "metallic", "interference", "pearl", "gold", "silver", "bronze", "fluorescent"],
        "This is a special-effect pigment — CMYK primary mixing cannot capture its metallic, iridescent, or fluorescent qualities.",
    ),
]


def _specialty_warning(tube_name: str) -> str:
    lower = tube_name.lower()
    for keywords, msg in _UNMIXABLE_CATEGORIES:
        if any(kw in lower for kw in keywords):
            return msg
    return ""


_PRIMARIES_HEX = {
    "Primary Yellow 275":  "#F4C800",
    "Primary Magenta 369": "#C41E7F",
    "Primary Cyan 572":    "#0093C8",
    "Oxide Black 735":     "#2C2420",
    "Titanium White 105":  "#FAFAFA",
}

# Relative tinting strength vs Primary Yellow (higher = stronger pigment = fewer grams needed)
_TINTING_STRENGTH = {
    "Primary Yellow 275":  1.0,
    "Primary Magenta 369": 2.0,
    "Primary Cyan 572":    2.5,
    "Oxide Black 735":     8.0,   # very high — a little goes a long way
    "Titanium White 105":  0.6,   # weak — needs more grams to lighten
}

def hex_to_primaries(hex_color: str) -> list[dict]:
    """Compute minimum viable primary recipe (all ingredients ≥ 1g, whole grams, scale ×1 base)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return [{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 1}]

    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0

    max_rgb = max(r, g, b)
    min_rgb = min(r, g, b)

    if max_rgb < 0.04:
        return [{"tube": "Oxide Black 735", "tubeHex": "#2C2420", "grams": 1}]
    if min_rgb > 0.96:
        return [{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 1}]

    # CMYK decomposition
    k = 1.0 - max_rgb
    c = (1.0 - r - k) / max_rgb
    m = (1.0 - g - k) / max_rgb
    y = (1.0 - b - k) / max_rgb

    # White only for desaturated / pastel colours (saturation below ~65%)
    saturation = (max_rgb - min_rgb) / max_rgb
    white = max(0.0, (0.65 - saturation) * max_rgb * 1.5)

    components = [
        ("Primary Yellow 275",  y),
        ("Primary Magenta 369", m),
        ("Primary Cyan 572",    c),
        ("Oxide Black 735",     k),
        ("Titanium White 105",  white),
    ]

    # Tinting strength correction: divide by strength so high-strength pigments
    # (especially black at 8×) don't get disproportionately large gram amounts
    adjusted = [
        (name, raw / _TINTING_STRENGTH[name])
        for name, raw in components
    ]

    total = sum(v for _, v in adjusted)
    if total == 0:
        return [{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 1}]

    # Normalize to proportions; drop anything below 2% (too small to matter at any batch size)
    proportions = [(name, adj / total) for name, adj in adjusted if adj / total >= 0.02]
    if not proportions:
        return [{"tube": "Titanium White 105", "tubeHex": "#FAFAFA", "grams": 1}]

    # Re-normalize after dropping tiny proportions
    prop_total = sum(p for _, p in proportions)
    proportions = [(name, p / prop_total) for name, p in proportions]

    # Scale so the smallest ingredient = 1g — this is the minimum viable base batch
    min_prop = min(p for _, p in proportions)
    scale = 1.0 / min_prop

    result = []
    for name, prop in sorted(proportions, key=lambda x: -x[1]):
        grams = round(prop * scale)
        if grams >= 1:
            result.append({"tube": name, "tubeHex": _PRIMARIES_HEX[name], "grams": grams})

    return result


primaries_notes_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color mixing expert for acrylic pour painters.
The user has a computed mixing recipe given as proportions. Write practical guidance for it.
Respond ONLY with a JSON object containing:
- steps: array of 3-4 concise plain-English steps for physically mixing these paints in order (mention tube names and proportions like "largest portion", "a small amount", NOT absolute grams — the user picks their own total)
- notes: one honest sentence on how close this approximation gets to the real tube and what pigment character is lost (transparency, single-pigment chroma, special effects)
No other text. Just the JSON."""),
    ("human", "Target colour: {target_tube}. Recipe proportions: {recipe_desc}. Write mixing steps and a note on accuracy.")
])

primaries_notes_chain = primaries_notes_prompt | llm | parser


# --- Mix from shelf: KM optimiser + LangGraph refinement ---

shelf_mix_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color mixing expert for acrylic pour painters.
An algorithm has computed the best mix of the user's available paint tubes to approximate a target color.
Write practical guidance for executing this mix.
Respond ONLY with a JSON object containing:
- steps: array of 3-4 concise plain-English steps for physically mixing these paints in order (mention tube names, start with the dominant tube, avoid mentioning grams — the user picks their batch size)
- notes: one honest sentence on how close this approximation gets and any pigment character differences (opacity, transparency, tinting strength) to be aware of
No other text. Just the JSON."""),
    ("human", """Target: {target_name} ({target_hex})
Recipe: {recipe_desc}
Predicted result hex: {predicted_hex}
ΔE from target: {delta_e:.1f} (< 5 = visually close · 5–10 = reasonable · > 15 = approximate)
Write mixing steps and an accuracy note."""),
])

shelf_mix_chain = shelf_mix_prompt | llm | parser


class ShelfMixState(TypedDict):
    target_name: str
    target_hex: str
    shelf_tubes: list          # [{tube: str, hex: str}]
    max_components: int
    recipe: list               # [{tube, tubeHex, grams}]
    fractions: dict            # {tube_name: fraction}
    delta_e: float
    predicted_hex: str
    steps: list
    notes: str
    warning: str


def _km_compute(state: ShelfMixState) -> dict:
    """Run KM optimisation to find the best mix."""
    tube_hex_map = {
        t["tube"]: t["hex"]
        for t in state["shelf_tubes"]
        if t.get("tube") and t.get("hex")
    }
    fractions, de, predicted = find_best_mix(
        state["target_hex"], tube_hex_map,
        max_components=state["max_components"],
        force_blend=True,
    )
    # Scale fractions to grams: aim for ~20g total so even 8% ingredients
    # round to at least 2g (avoids single-tube collapse from rounding to 0)
    TARGET_GRAMS = 20
    recipe = []
    for tube_name, frac in sorted(fractions.items(), key=lambda x: -x[1]):
        grams = max(1, round(frac * TARGET_GRAMS))
        recipe.append({
            "tube": tube_name,
            "tubeHex": tube_hex_map[tube_name],
            "grams": grams,
        })
    return {"recipe": recipe, "fractions": fractions, "delta_e": de, "predicted_hex": predicted}


def _should_expand(state: ShelfMixState) -> str:
    """If match is poor and we haven't tried all tubes yet, widen the search."""
    if state["delta_e"] > 12 and state["max_components"] < 5:
        return "expand"
    return "refine"


def _expand(state: ShelfMixState) -> dict:
    return {"max_components": state["max_components"] + 2}


def _ai_refine(state: ShelfMixState) -> dict:
    """Ask the AI for mixing steps and an accuracy note."""
    recipe_desc = ", ".join(
        f"{ing['tube']} (~{round(state['fractions'].get(ing['tube'], 0) * 100)}%)"
        for ing in state["recipe"]
    )
    try:
        ai = shelf_mix_chain.invoke({
            "target_name": state["target_name"] or state["target_hex"],
            "target_hex": state["target_hex"],
            "recipe_desc": recipe_desc,
            "predicted_hex": state["predicted_hex"],
            "delta_e": state["delta_e"],
        })
        if not isinstance(ai, dict):
            ai = {}
    except Exception:
        ai = {}
    de = state["delta_e"]
    if de > 15:
        warning = (
            f"Approximate match (ΔE {de:.0f}) — the closest achievable with your shelf. "
            "Adding a tube closer to the target would improve accuracy."
        )
    elif de > 8:
        warning = f"Reasonable match (ΔE {de:.0f}) — expect some difference from the target, particularly in chroma or value."
    else:
        warning = ""
    steps = ai.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    return {
        "steps": [str(s) for s in steps if s],
        "notes": str(ai.get("notes") or ""),
        "warning": warning,
    }


_shelf_graph = StateGraph(ShelfMixState)
_shelf_graph.add_node("compute", _km_compute)
_shelf_graph.add_node("expand", _expand)
_shelf_graph.add_node("refine", _ai_refine)
_shelf_graph.set_entry_point("compute")
_shelf_graph.add_conditional_edges("compute", _should_expand, {"expand": "expand", "refine": "refine"})
_shelf_graph.add_edge("expand", "compute")
_shelf_graph.add_edge("refine", END)
shelf_mix_graph = _shelf_graph.compile()


def generate_shelf_mix(target_name: str, target_hex: str, shelf_tubes: list[dict]) -> dict:
    """
    Mix target_hex from shelf_tubes using KM optimisation + AI refinement.
    shelf_tubes: [{tube: str, hex: str}, ...]
    """
    target_lower = target_name.lower().strip()
    target_base = re.sub(r'\s*\d+\s*$', '', target_lower).strip()
    # Direct tube match — exact name or matching base name (ignoring catalogue number)
    for t in shelf_tubes:
        tube_lower = t.get("tube", "").lower().strip()
        tube_base = re.sub(r'\s*\d+\s*$', '', tube_lower).strip()
        if tube_lower == target_lower or (target_base and tube_base == target_base):
            return {
                "mixRecipe": [{"tube": t["tube"], "tubeHex": t.get("hex", "#888"), "grams": 1}],
                "steps": [f"You already have {t['tube']} — use it directly from the tube. No mixing needed."],
                "notes": "Direct tube match — no mixing required.",
                "targetHex": target_hex,
                "predictedHex": t.get("hex", target_hex),
                "deltaE": 0.0,
                "warning": "",
            }

    result = shelf_mix_graph.invoke({
        "target_name": target_name,
        "target_hex": target_hex,
        "shelf_tubes": shelf_tubes,
        "max_components": 3,
        "recipe": [],
        "fractions": {},
        "delta_e": 999.0,
        "predicted_hex": target_hex,
        "steps": [],
        "notes": "",
        "warning": "",
    })
    return {
        "mixRecipe": result["recipe"],
        "steps": result["steps"],
        "notes": result["notes"],
        "targetHex": target_hex,
        "predictedHex": result["predicted_hex"],
        "deltaE": round(result["delta_e"], 1),
        "warning": result["warning"],
    }


def generate_primary_mix(target_tube: str, target_hex: str = "") -> dict:
    recipe = hex_to_primaries(target_hex or "#888888")
    total_raw = sum(ing["grams"] for ing in recipe)
    if total_raw > 0:
        recipe_desc = ", ".join(
            f"{ing['tube']} (~{round(ing['grams'] / total_raw * 100)}%)"
            for ing in recipe
        )
    else:
        recipe_desc = "Titanium White 105 (100%)"
    try:
        ai = primaries_notes_chain.invoke({"target_tube": target_tube, "recipe_desc": recipe_desc})
        if not isinstance(ai, dict):
            ai = {}
    except Exception:
        ai = {}
    steps = ai.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    return {
        "mixRecipe": recipe,
        "steps": [str(s) for s in steps if s],
        "notes": str(ai.get("notes") or ""),
        "targetHex": target_hex,
        "warning": _specialty_warning(target_tube),
    }
