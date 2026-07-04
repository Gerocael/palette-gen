import os
import re
import random
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict

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

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
REQUIRED_KEYS = {"hexCode", "colorName", "emotionalDescription"}


class PaletteState(TypedDict):
    prompt: str
    num_colors: int
    colors: list
    is_valid: bool
    error: str
    attempts: int


def generate(state: PaletteState) -> dict:
    nc = state.get("num_colors", 5)
    try:
        if state["attempts"] == 0:
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


def generate_palette(prompt: str, num_colors: int = 5) -> dict:
    result = palette_graph.invoke({
        "prompt": prompt,
        "num_colors": num_colors,
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
- "colors": an array of exactly 5 colors, each with:
  - hexCode: a valid hex color
  - colorName: if the mixRecipe uses only one tube, MUST be exactly that tube's name. When mixing, use a recognized color name.
  - emotionalDescription: the mood this color evokes
  - pourRatio: percentage in the pour as a whole number (all 5 add to 100)
  - mixRecipe: array of ingredients using ONLY tubes from the user's list. Each has tube, tubeHex, grams (totaling 15-25g).
- "technique": an object with name, reason, and tip
No other text, no markdown. Just the JSON object."""),
    ("human", "I own these Amsterdam Standard Series tubes: {tubes}. Suggest 3 palettes I can make. Creative direction: {direction}. Be adventurous and avoid obvious or generic combinations.")
])

suggest_flood_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert for acrylic pour painters who use a flood-and-accent technique.
The user floods their entire canvas with one dominant base color first, then adds 4 accent colors on top for contrast and interest.
The user gives you a list of Royal Talens Amsterdam Standard Series tubes they own.
Suggest exactly 3 distinct pour palettes using ONLY those tubes. Each palette MUST explore a completely different mood, style, and color range.
IMPORTANT RULES:
- Each palette has exactly 5 colors: 1 base and 4 accents.
- The base color floods the entire canvas first — it must be a strong, intentional color.
- The 4 accent colors must contrast strongly against the base. No accent should visually disappear into the base.
- Every palette must span at least 3 clearly distinct hue families.
- Mix 2-4 tubes per color for interesting intermediary tones. Only use a single tube when it is a perfect match.
- Every tube in every mixRecipe MUST come from the user's provided list. Do not invent tubes they do not own.
Respond ONLY with a JSON object containing a "palettes" array of 3 palettes. Each palette has:
- "name": a short evocative name
- "mood": one short sentence describing the feeling
- "colors": an array of exactly 5 colors, each with:
  - hexCode: a valid hex color
  - colorName: if the mixRecipe uses only one tube, MUST be exactly that tube's name. If mixed, use a recognized color name.
  - emotionalDescription: the mood this color evokes
  - role: "base" for the flood color (exactly one per palette), "accent" for all others
  - pourRatio: percentage in the pour as a whole number (all 5 add to 100). Base must be 50-70%. Accents share the remainder.
  - mixRecipe: array of ingredients using ONLY tubes from the user's list. Each has tube, tubeHex, grams. Base totals 40-60g, each accent totals 10-20g.
- "technique": an object with name, reason, and tip specific to the flood-and-accent style
No other text, no markdown. Just the JSON object."""),
    ("human", "I own these Amsterdam Standard Series tubes: {tubes}. Suggest 3 palettes. {base_instruction} Creative direction: {direction}. Be adventurous and avoid obvious combinations.")
])

suggest_standard_chain = suggest_standard_prompt | suggest_llm | parser
suggest_flood_chain = suggest_flood_prompt | suggest_llm | parser

suggest_retry_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color palette expert. Your previous response was invalid JSON.
Respond ONLY with a valid JSON object (no markdown, no code blocks, no extra text) containing a "palettes" array of 3 palettes.
Each palette: name, mood, colors (array of 5), technique.
Each color: hexCode (#RRGGBB), colorName, emotionalDescription, pourRatio (int, all 5 sum to 100), mixRecipe (array of {{tube, tubeHex, grams}}).
IMPORTANT: Every tube in every mixRecipe MUST come from the user's tube list. Do not invent tubes."""),
    ("human", "Tubes: {tubes}. Suggest 3 palettes. Previous error: {error}")
])

suggest_retry_chain = suggest_retry_prompt | suggest_llm | parser


def suggest_from_shelf(tubes: list, base_tube: str | None = None, flood_mode: bool = False) -> dict:
    tube_list = ", ".join(tubes)
    direction = random.choice(CREATIVE_DIRECTIONS)

    for attempt in range(3):
        try:
            if attempt == 0:
                if flood_mode:
                    if base_tube:
                        base_instruction = (
                            f"I want to use '{base_tube}' as my flood base — it covers the entire canvas first. "
                            f"Choose 4 accent colors from my remaining tubes that contrast strongly against it. "
                            f"Mark '{base_tube}' with role 'base' and all other colors with role 'accent'."
                        )
                    else:
                        base_instruction = (
                            "You choose which of my tubes works best as the flood base color for each palette. "
                            "Mark it with role 'base' and the other 4 colors with role 'accent'. "
                            "Choose accents that contrast strongly against the base."
                        )
                    result = suggest_flood_chain.invoke({"tubes": tube_list, "direction": direction, "base_instruction": base_instruction})
                else:
                    result = suggest_standard_chain.invoke({"tubes": tube_list, "direction": direction})
            else:
                result = suggest_retry_chain.invoke({"tubes": tube_list, "error": last_error})

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
The user has chosen {num_seed} seed color(s) for a pour palette and wants you to suggest exactly 3 additional colors that complement them (via contrast, harmony, or accent) to round out the palette.
Respond ONLY with a JSON object containing a "colors" array of exactly 3 colors, each with:
- hexCode: a valid hex color
- colorName: if the mixRecipe uses only one tube, colorName MUST be exactly that tube's name (e.g. "Titanium White 105"). When mixing two or more tubes, use a commonly recognized color name for the mix.
- emotionalDescription: one short sentence on why this color complements the seed color(s)
- mixRecipe: an array of ingredients to mix using Royal Talens Amsterdam Standard Series acrylic tubes to approximate this color. Each ingredient has tube, tubeHex, grams (realistic amounts totaling 15-25g).
{shelf_instruction}
The 3 suggestions should not be near-duplicates of each other or of the seed color(s) — offer real variety.
No other text, no markdown, no explanation. Just the JSON object."""),
    ("human", "Seed color(s): {seed_colors}. Suggest 3 colors that complement them well for an acrylic pour palette.")
])

complement_chain = complement_prompt | llm | parser


def suggest_complementary_colors(seed_colors: list, shelf_tubes: list | None = None) -> dict:
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
        "seed_colors": seed_list,
        "shelf_instruction": shelf_instruction
    })
    if isinstance(result, dict) and "colors" in result:
        return {"colors": result["colors"][:3]}
    return {"colors": []}


# --- Color mixing guide: reverse-engineer a target color from Amsterdam tubes ---

mix_guide_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a color mixing expert for acrylic pour painters using the Royal Talens Amsterdam Standard Series.
Given a target color (either an Amsterdam tube name like "Phthalo Blue 570" or a hex code), work out the best mixing recipe to approximate it using Amsterdam Standard Series tubes.
Respond ONLY with a JSON object containing:
- colorName: if a single tube is a near-perfect match, use exactly that tube's name (e.g. "Titanium White 105"). Otherwise use a common descriptive name for the mixed result.
- mixRecipe: an array of 2-4 ingredients (only use 1 if it's a near-perfect single-tube match) to combine, each with tube, tubeHex, grams. Use realistic relative proportions totaling around 20 — these are ratios the app will rescale to the user's desired batch size, so getting the proportions right matters more than the literal total.
- steps: an array of 3-5 short, plain-English instructions for physically mixing this recipe in order (e.g. start with the dominant/base color, add tinting colors gradually, when to test on a scrap surface, how to judge when it's ready).
- notes: one sentence on how close this recipe gets to the target and an adjustment tip (e.g. add a touch more of X if it reads too warm).
No other text, no markdown, no explanation. Just the JSON object."""),
    ("human", "Target color: {target_color}. Give me a mixing recipe and step-by-step instructions to achieve this exact color with Amsterdam Standard Series acrylics.")
])

mix_guide_chain = mix_guide_prompt | llm | parser


def generate_mix_guide(target_color: str) -> dict:
    result = mix_guide_chain.invoke({"target_color": target_color})
    return result if isinstance(result, dict) else {}
