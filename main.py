from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from palette_service import generate_palette

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