from fastapi import FastAPI
from pydantic import BaseModel

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
def generate_palette(request: PaletteRequest):
    # Hardcoded response for now, we'll add Claude later
    return PaletteResponse(
        prompt=request.prompt,
        colors=[
            Color(hex_code="#8B4513", name="Saddle Brown", description="Warm earthy grounding tone"),
            Color(hex_code="#DAA520", name="Goldenrod", description="Rich autumn warmth"),
            Color(hex_code="#2E8B57", name="Sea Green", description="Deep forest calm"),
            Color(hex_code="#CD853F", name="Peru", description="Soft sandy warmth"),
            Color(hex_code="#556B2F", name="Dark Olive", description="Quiet natural depth"),
        ]
    )