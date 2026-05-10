import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def generate_palette(prompt: str) -> list:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""You are a color palette expert for artists, especially acrylic pour painters. 
When given a mood, theme, or description, respond ONLY with a JSON array of exactly 5 colors. 
No other text, no markdown, no explanation. Just the JSON array.
Each color must have: hexCode, colorName, and emotionalDescription.
Example format:
[{"hexCode": "#8B4513", "colorName": "Saddle Brown", "emotionalDescription": "Warm earthy grounding tone"}]""",
        messages=[
            {"role": "user", "content": f"Generate a color palette for: {prompt}"}
        ]
    )
    
    response_text = message.content[0].text
    colors = json.loads(response_text)
    return colors