from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from palette_service import generate_palette, mix_colors
from datetime import datetime, date

app = FastAPI()

# Simple daily rate limit: 1 generate + 1 mix per IP per day
usage_log = {}

def check_rate_limit(ip: str, action: str):
    today = date.today().isoformat()
    key = f"{ip}:{action}:{today}"
    if key in usage_log:
        raise HTTPException(status_code=429, detail="Daily limit reached. Come back tomorrow!")
    usage_log[key] = True

class PaletteRequest(BaseModel):
    prompt: str

class Color(BaseModel):
    hex_code: str
    name: str
    description: str

class PaletteResponse(BaseModel):
    prompt: str
    colors: list[Color]

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

@app.post("/palette/generate")
def create_palette(request: PaletteRequest, req: Request):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    check_rate_limit(req.client.host, "generate")
    
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate palette: {str(e)}")

@app.post("/palette/mix")
def mix_palette_colors(request: MixRequest, req: Request):
    if not request.color1.strip() or not request.color2.strip():
        raise HTTPException(status_code=400, detail="Both colors are required")
    
    check_rate_limit(req.client.host, "mix")
    
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mix colors: {str(e)}")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")