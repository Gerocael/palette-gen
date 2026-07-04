# Density / opacity / tinting-strength reference for the Amsterdam Standard Series.
#
# This is a good-faith categorization inferred from each tube's pigment family (e.g. "Phthalo"
# names use phthalocyanine pigments, "Ochre"/"Umber"/"Sienna" use iron oxides, "Titanium" uses
# titanium dioxide) and well-documented general pigment chemistry — NOT lab-measured density data
# for Royal Talens' specific formulations, which Talens does not publish. Treat it as relative
# guidance for pour order and mudding risk, not a precise physical spec.
#
# density: "heavy" (sinks in a pour) / "medium" (suspends) / "light" (floats)
# opacity: "opaque" / "semi-opaque" / "transparent"
# tinting_strength: "high" / "medium" / "low" — how much a little bit of this pigment dominates a mix
# metallic: True for metallic/pearlescent tubes, whose flake structure floats and can dull mixes
#           regardless of raw pigment density

PIGMENT_DATA = {
    "Zinc White 104": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "low"},
    "Titanium White 105": {"density": "heavy", "opacity": "opaque", "tinting_strength": "high"},

    "Permanent Lemon Yellow Light 217": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Naples Yellow Light 222": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Naples Yellow Deep 223": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Naples Yellow Red 224": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Yellow Ochre 227": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Gold Ochre 231": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Raw Sienna 234": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Greenish Yellow 243": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Gold Yellow 253": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Reflex Yellow 256": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Reflex Orange 257": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Azo Yellow Lemon 267": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Azo Yellow Light 268": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Azo Yellow Medium 269": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Azo Yellow Deep 270": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Transparent Yellow Medium 272": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Nickel Titanium Yellow 274": {"density": "heavy", "opacity": "opaque", "tinting_strength": "low"},
    "Primary Yellow 275": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Azo Orange 276": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Naples Yellow Green 282": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Titanium Buff Light 289": {"density": "heavy", "opacity": "opaque", "tinting_strength": "low"},
    "Titanium Buff Deep 290": {"density": "heavy", "opacity": "opaque", "tinting_strength": "low"},
    "Naples Yellow Red Light 292": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},

    "Vermilion 311": {"density": "heavy", "opacity": "opaque", "tinting_strength": "high"},
    "Pyrrole Red 315": {"density": "medium", "opacity": "opaque", "tinting_strength": "high"},
    "Venetian Rose 316": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Transparent Red Medium 317": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Carmine 318": {"density": "medium", "opacity": "transparent", "tinting_strength": "high"},
    "Persian Rose 330": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Caput Mortuum Violet 344": {"density": "heavy", "opacity": "opaque", "tinting_strength": "medium"},
    "Permanent Red Purple 348": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Light Rose 361": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Quinacridone Rose 366": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Primary Magenta 369": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Reflex Rose 384": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Quinacridone Rose Light 385": {"density": "light", "opacity": "transparent", "tinting_strength": "medium"},
    "Naphthol Red Medium 396": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Naphthol Red Light 398": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Naphthol Red Deep 399": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "high"},

    "Vandyke Brown 403": {"density": "medium", "opacity": "transparent", "tinting_strength": "medium"},
    "Raw Umber 408": {"density": "heavy", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Burnt Umber 409": {"density": "heavy", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Burnt Sienna 411": {"density": "medium", "opacity": "transparent", "tinting_strength": "medium"},

    "Ultramarine 504": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Ultramarine Light 505": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Ultramarine Violet 507": {"density": "light", "opacity": "transparent", "tinting_strength": "medium"},
    "Cobalt Blue (Ultramarine) 512": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Ultramarine Violet Light 519": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Turquoise Blue 522": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Sky Blue Light 551": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Lilac 556": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Greenish Blue 557": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Greyish Blue 562": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Brilliant Blue 564": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Prussian Blue (Phthalo) 566": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Permanent Red Violet 567": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Permanent Blue Violet 568": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Phthalo Blue 570": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Primary Cyan 572": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Permanent Red Violet Light 577": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Manganese Blue Phthalo 582": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},

    "Brilliant Green 605": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "high"},
    "Emerald Green 615": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Yellowish Green 617": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Permanent Green Light 618": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Permanent Green Deep 619": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Olive Green Light 621": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Olive Green Deep 622": {"density": "medium", "opacity": "opaque", "tinting_strength": "medium"},
    "Sap Green 623": {"density": "light", "opacity": "transparent", "tinting_strength": "medium"},
    "Turquoise Green Light 660": {"density": "light", "opacity": "transparent", "tinting_strength": "medium"},
    "Turquoise Green 661": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Yellowish Green Light 664": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "medium"},
    "Reflex Green 672": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},
    "Phthalo Green 675": {"density": "light", "opacity": "transparent", "tinting_strength": "high"},

    "Lamp Black 702": {"density": "light", "opacity": "opaque", "tinting_strength": "high"},
    "Neutral Grey 710": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Warm Grey 718": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},
    "Oxide Black 735": {"density": "heavy", "opacity": "opaque", "tinting_strength": "high"},
    "Bluish Grey Light 750": {"density": "medium", "opacity": "opaque", "tinting_strength": "low"},

    "Silver 800": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Light Gold 802": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Deep Gold 803": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Copper 805": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Bronze 811": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Pewter 815": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Pearl White 817": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Pearl Yellow 818": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Pearl Red 819": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Pearl Blue 820": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Pearl Violet 821": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Pearl Green 822": {"density": "light", "opacity": "semi-opaque", "tinting_strength": "low", "metallic": True},
    "Metallic Yellow 831": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Metallic Red 832": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Metallic Blue 834": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Metallic Violet 835": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Metallic Green 836": {"density": "light", "opacity": "opaque", "tinting_strength": "medium", "metallic": True},
    "Graphite 840": {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium", "metallic": True},
    "Metallic Black 850": {"density": "light", "opacity": "opaque", "tinting_strength": "high", "metallic": True},
}


def lookup(tube_name: str) -> dict:
    return PIGMENT_DATA.get(tube_name, {"density": "medium", "opacity": "semi-opaque", "tinting_strength": "medium", "metallic": False})
