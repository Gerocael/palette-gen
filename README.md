Palette Generator API
A REST API that uses AI to generate color palettes for artists, especially acrylic pour painters. Give it a mood, theme, or description and it returns a thoughtful palette with hex codes, names, and emotional descriptions.
Tech Stack

Python
FastAPI
Anthropic Claude API (claude-sonnet-4-6)
Pydantic for data validation

Setup

Clone the repository:

git clone https://github.com/gerocael/palette-gen.git
cd palette-gen

Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

Install dependencies:

pip install -r requirements.txt

Create a .env file with your Anthropic API key:

ANTHROPIC_API_KEY=your-key-here

Run the server:

uvicorn main:app --reload

Open http://127.0.0.1:8000/docs to explore the API.

Endpoints
POST /palette/generate
Generates a 5-color palette based on a mood or theme.
Request:
json{
  "prompt": "autumn forest at sunset"
}
Response:
json{
  "prompt": "autumn forest at sunset",
  "colors": [
    {
      "hex_code": "#8B4513",
      "name": "Saddle Brown",
      "description": "Deep woody warmth of ancient bark"
    },
    {
      "hex_code": "#DAA520",
      "name": "Goldenrod",
      "description": "Rich amber glow of fading sunlight"
    },
    {
      "hex_code": "#CD853F",
      "name": "Peru",
      "description": "Soft warmth of scattered leaves"
    },
    {
      "hex_code": "#8B0000",
      "name": "Dark Red",
      "description": "Bold crimson of turning maples"
    },
    {
      "hex_code": "#2F4F4F",
      "name": "Dark Slate",
      "description": "Cool shadow beneath the canopy"
    }
  ]
}
POST /palette/mix
Takes two hex colors and describes what they would produce when mixed in acrylic pouring.
Request:
json{
  "color1": "#8B4513",
  "color2": "#DAA520"
}
Response:
json{
  "color1": "#8B4513",
  "color2": "#DAA520",
  "result_hex": "#B27419",
  "result_name": "Burnt Amber",
  "description": "A rich, warm brown-gold that creates beautiful organic cells in acrylic pours",
  "pour_tip": "Use as a base layer with a lighter gold on top for natural tree-bark patterns"
}
About
Built as a personal tool combining my interest in acrylic pour painting with AI development. The prompt engineering ensures consistent, artist-friendly palette suggestions grounded in color theory and emotional context.