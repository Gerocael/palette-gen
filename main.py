from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from palette_service import generate_palette
from palette_service import generate_palette, mix_colors

app = FastAPI()

class PaletteRequest(BaseModel):
    prompt: str

class Color(BaseModel):
    hex_code: str
    name: str
    description: str

class PaletteResponse(BaseModel):
    prompt: str
    colors: list[Color]

@app.post("/palette/generate")
def create_palette(request: PaletteRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    try:
        raw_colors = generate_palette(request.prompt)
        colors = [
            Color(
                hex_code=c["hexCode"],
                name=c["colorName"],
                description=c["emotionalDescription"]
            )
            for c in raw_colors
        ]
        return PaletteResponse(prompt=request.prompt, colors=colors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate palette: {str(e)}")
    
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

@app.post("/palette/mix")
def mix_palette_colors(request: MixRequest):
    if not request.color1.strip() or not request.color2.strip():
        raise HTTPException(status_code=400, detail="Both colors are required")
    
    try:
        result = mix_colors(request.color1, request.color2)
        return MixResponse(
            color1=request.color1,
            color2=request.color2,
            result_hex=result["resultHex"],
            result_name=result["resultName"],
            description=result["description"],
            pour_tip=result["pourTip"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mix colors: {str(e)}")