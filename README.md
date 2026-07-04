# Palette Gen

AI-powered color palette generator for acrylic pour painters. Built around the Royal Talens Amsterdam Standard Series — the full 102-colour set.

**Live demo:** https://palette-gen-heti.onrender.com/

---

## Features

**Generate a palette** — describe a mood, scene, or theme and get a 5-colour palette with hex codes, pour ratios, and Amsterdam tube mixing recipes.

**Mix two colours** — pick any two hex colours and get an AI description of the mixed result, including a pour tip. Colours are randomised from the Amsterdam database on load.

**Pour from my shelf** — select the tubes you own, then get 3 palette suggestions using only those tubes, with full mixing recipes and gram amounts.

- **Flood base mode** (optional, toggled in settings) — designates one colour as the dominant flood layer. You can pick the base yourself or let the AI choose. Accent colours are selected for strong contrast against the base.

**Canvas calculator** — set your canvas size in cm and the app calculates how much paint and medium you need, scaled per colour by pour ratio.

**Light / dark mode** — toggle in the nav bar, preference saved to localStorage.

---

## Tech Stack

- **Frontend** — single-page HTML/CSS/JS, no framework
- **Backend** — Python, FastAPI, Pydantic
- **AI** — Anthropic Claude API (`claude-sonnet-5`) via LangChain + LangGraph (retry/validation loop)
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
| POST | `/palette/mix` | Mix two hex colours |
| GET | `/palette/history` | Last 5 generated palettes |

Rate limited to 5 requests per endpoint per IP per day.

---

Built by Roland Gebe — combining acrylic pour painting with AI.
