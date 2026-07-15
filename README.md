# Palette Gen

AI-powered color palette generator for acrylic pour painters. Built around the Royal Talens Amsterdam Standard Series — the full 102-colour set.

**Live demo:** https://palette-gen-heti.onrender.com/

---

## Features

**Generate a palette** — describe a mood, scene, or theme and get a 3–5 colour palette with hex codes, pour ratios, and Amsterdam tube mixing recipes.

**Mix two tubes** — pick any two Amsterdam tubes and get a KM-predicted mix result with an AI-written pour tip. Tubes are randomised from the database on load.

**Mix from primaries** — pick any Amsterdam tube as a target and get a recipe using only the 5 primaries (Yellow 275, Magenta 369, Cyan 572, White 105, Oxide Black 735).

**Complementary colors** — seed with 1–2 Amsterdam tubes and let the AI suggest more colours that round out the palette, with full mixing recipes.

**Pour from my shelf** — select the tubes you own, then:
- *Palette suggestions* — get 3 AI-generated palette ideas using only tubes from your shelf, with mixing recipes and gram amounts.
- *Mix from shelf* — pick any Amsterdam tube as a target; the Kubelka-Munk physics model finds the best blend from your owned tubes, with exact gram weights.

- **Flood base mode** (optional, toggled in settings) — designates one or more colours as the dominant flood layer. Pick the base yourself or let the AI choose; accent colours are selected for contrast against it.

**Mix it for me** — hover any colour card in a generated palette and click Mix to jump straight to the shelf mix with that colour pre-loaded as the target.

**Canvas calculator** — set your canvas size in cm and the app calculates paint and medium amounts, scaled per colour by pour ratio.

**Pigment analysis** — each palette includes pour order, mudding risk warnings, and per-colour density notes derived from pigment data.

**Light / dark mode** — toggle in the nav bar, preference saved to localStorage.

---

## Tech Stack

- **Frontend** — single-page HTML/CSS/JS, no framework
- **Backend** — Python, FastAPI, Pydantic
- **AI** — Anthropic Claude API (`claude-sonnet-5`) via LangChain + LangGraph (retry/validation loop)
- **Colour mixing** — Kubelka-Munk square-root model (`color_mixing.py`) with Brent optimisation for 2-tube blends and grid search + SLSQP refinement for 3-tube blends
- **Colour data** — complete Amsterdam Standard Series (102 colours), sourced from official Royal Talens colour charts

---

## Setup

```bash
git clone https://github.com/Gerocael/palette-gen.git
cd palette-gen

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file:

```
ANTHROPIC_API_KEY=your-key-here
```

Run the server:

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/palette/generate` | Generate a palette from a text prompt |
| POST | `/palette/suggest` | Suggest palettes from owned tubes |
| POST | `/palette/mix` | Mix two Amsterdam tubes |
| POST | `/palette/complement` | Suggest complementary colours from 1–2 seed tubes |
| POST | `/palette/mix-primaries` | Get a primaries-only recipe for a target tube |
| POST | `/palette/mix-from-shelf` | KM-optimised blend recipe from owned tubes |
| GET  | `/palette/history` | Last 5 generated palettes |

Rate limited to 5 requests per endpoint per IP per day.

---

Built by Roland Gebe — combining acrylic pour painting with AI.
