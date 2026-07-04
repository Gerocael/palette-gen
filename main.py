from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from palette_service import generate_palette, mix_colors, suggest_from_shelf, suggest_complementary_colors, generate_mix_guide
from pigment_analysis import analyze_palette_pigments
from datetime import datetime, date, timezone

app = FastAPI()

usage_log = {}
palette_history = []

def check_rate_limit(ip: str, action: str):
    today = date.today().isoformat()
    key = f"{ip}:{action}:{today}"
    count = usage_log.get(key, 0)
    if count >= 5:
        raise HTTPException(status_code=429, detail="Daily limit reached. Come back tomorrow!")
    usage_log[key] = count + 1

class PaletteRequest(BaseModel):
    prompt: str
    num_colors: int = 5

class MixIngredient(BaseModel):
    tube: str
    tube_hex: str
    grams: float

class Color(BaseModel):
    hex_code: str
    name: str
    description: str
    pour_ratio: int | None = None
    mix_recipe: list[MixIngredient] | None = None
    role: str | None = None

class Technique(BaseModel):
    name: str
    reason: str
    tip: str

class PigmentColorNote(BaseModel):
    color_name: str
    hex_code: str
    density: str
    behavior: str
    mudding_risk: str | None = None

class PigmentAnalysis(BaseModel):
    pour_order: list[str]
    notes: list[PigmentColorNote]
    warnings: list[str]

class PaletteResponse(BaseModel):
    prompt: str
    colors: list[Color]
    technique: Technique | None = None
    pigment_analysis: PigmentAnalysis | None = None

class ShelfRequest(BaseModel):
    tubes: list[str]
    base_tube: str | None = None
    flood_mode: bool = False

class SuggestedPalette(BaseModel):
    name: str
    mood: str
    colors: list[Color]
    technique: Technique | None = None
    pigment_analysis: PigmentAnalysis | None = None

class SuggestResponse(BaseModel):
    palettes: list[SuggestedPalette]

class MixRequest(BaseModel):
    color1: str
    color2: str

class MixResponse(BaseModel):
    color1: str
    color2: str
    result_hex: str
    result_name: str
    description: str
    pour_tip: str

class ComplementRequest(BaseModel):
    colors: list[str]
    shelf_tubes: list[str] = []

class ComplementResponse(BaseModel):
    colors: list[Color]

class MixGuideRequest(BaseModel):
    target_color: str

class MixGuideResponse(BaseModel):
    target_hex: str
    color_name: str
    mix_recipe: list[MixIngredient]
    steps: list[str]
    notes: str


def build_colors(raw_colors):
    colors = []
    for c in raw_colors:
        mix_recipe = None
        raw_recipe = c.get("mixRecipe") or c.get("mix_recipe") or []
        if raw_recipe:
            ingredients = []
            for ing in raw_recipe:
                if isinstance(ing, str):
                    continue
                tube = ing.get("tube") or ing.get("name") or ""
                tube_hex = ing.get("tubeHex") or ing.get("tube_hex") or "#888888"
                grams = ing.get("grams") or ing.get("amount") or 0
                try:
                    grams = float(grams)
                except (ValueError, TypeError):
                    grams = 0
                if tube and tube != "Unknown" and grams > 0:
                    ingredients.append(MixIngredient(tube=tube, tube_hex=tube_hex, grams=grams))
            if ingredients:
                mix_recipe = ingredients

        hex_code = c.get("hexCode") or c.get("hex_code") or "#888888"
        name = c.get("colorName") or c.get("color_name") or c.get("name") or "Unknown"
        description = c.get("emotionalDescription") or c.get("emotional_description") or c.get("description") or ""
        pour_ratio = c.get("pourRatio") or c.get("pour_ratio")
        if pour_ratio is not None:
            try:
                pour_ratio = int(pour_ratio)
            except (ValueError, TypeError):
                pour_ratio = None

        role = c.get("role")

        colors.append(Color(
            hex_code=hex_code,
            name=name,
            description=description,
            pour_ratio=pour_ratio,
            mix_recipe=mix_recipe,
            role=role
        ))
    return colors


def build_technique(raw_technique):
    if raw_technique and isinstance(raw_technique, dict):
        return Technique(
            name=raw_technique.get("name", ""),
            reason=raw_technique.get("reason", ""),
            tip=raw_technique.get("tip", "")
        )
    return None


@app.get("/palette/history")
def get_history():
    return {"history": list(reversed(palette_history))}

@app.post("/palette/generate")
def create_palette(request: PaletteRequest, req: Request):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    check_rate_limit(req.client.host, "generate")
    try:
        result = generate_palette(request.prompt, num_colors=max(3, min(5, request.num_colors)))
        colors = build_colors(result["colors"])
        technique = build_technique(result.get("technique"))
        pigment_analysis = analyze_palette_pigments(colors)
        response = PaletteResponse(prompt=request.prompt, colors=colors, technique=technique, pigment_analysis=pigment_analysis)
        palette_history.append({
            "prompt": request.prompt,
            "palette": [c.model_dump() for c in colors],
            "technique": technique.model_dump() if technique else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        palette_history[:] = palette_history[-5:]
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate palette: {str(e)}")

@app.post("/palette/suggest")
def suggest_palettes(request: ShelfRequest, req: Request):
    if not request.tubes or len(request.tubes) < 2:
        raise HTTPException(status_code=400, detail="Please add at least 2 tubes to your shelf")
    check_rate_limit(req.client.host, "suggest")
    try:
        result = suggest_from_shelf(request.tubes, base_tube=request.base_tube, flood_mode=request.flood_mode)
        palettes = []
        for p in result.get("palettes", []):
            colors = build_colors(p.get("colors", []))
            technique = build_technique(p.get("technique"))
            palettes.append(SuggestedPalette(
                name=p.get("name", "Untitled"),
                mood=p.get("mood", ""),
                colors=colors,
                technique=technique,
                pigment_analysis=analyze_palette_pigments(colors)
            ))
        return SuggestResponse(palettes=palettes)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest palettes: {str(e)}")

@app.post("/palette/mix")
def mix_palette_colors(request: MixRequest, req: Request):
    if not request.color1.strip() or not request.color2.strip():
        raise HTTPException(status_code=400, detail="Both colors are required")
    check_rate_limit(req.client.host, "mix")
    try:
        result = mix_colors(request.color1, request.color2)
        return MixResponse(
            color1=request.color1, color2=request.color2,
            result_hex=result["resultHex"], result_name=result["resultName"],
            description=result["description"], pour_tip=result["pourTip"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mix colors: {str(e)}")

@app.post("/palette/complement")
def complement_colors(request: ComplementRequest, req: Request):
    colors = [c.strip() for c in request.colors if c and c.strip()]
    if not colors or len(colors) > 2:
        raise HTTPException(status_code=400, detail="Provide 1 or 2 seed colors")
    check_rate_limit(req.client.host, "complement")
    try:
        result = suggest_complementary_colors(colors, shelf_tubes=request.shelf_tubes)
        return ComplementResponse(colors=build_colors(result.get("colors", [])))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest complementary colors: {str(e)}")

@app.post("/palette/mix-guide")
def mix_guide(request: MixGuideRequest, req: Request):
    target = request.target_color.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target color is required")
    check_rate_limit(req.client.host, "mix_guide")
    try:
        result = generate_mix_guide(target)
        color = build_colors([{
            "hexCode": target,
            "colorName": result.get("colorName", "Unknown"),
            "mixRecipe": result.get("mixRecipe", [])
        }])[0]
        steps = result.get("steps") or []
        if not isinstance(steps, list):
            steps = []
        steps = [str(s) for s in steps if s]
        return MixGuideResponse(
            target_hex=target,
            color_name=color.name,
            mix_recipe=color.mix_recipe or [],
            steps=steps,
            notes=str(result.get("notes") or "")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate mixing guide: {str(e)}")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")
