import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/dust-collector-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0").strip()
CUSTOM_DUST = os.environ.get("CUSTOM_DUST", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_collectors.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Machine / Collector Model Name, Port Dia Inches, Target FPM, Rec Motor HP, Static Loss in.WG, Voltage Spec)
SEED_COLLECTORS = [
    ("SawStop PCS 10-Inch Cabinet Table Saw (4\" + Overarm)", 5.0, 4000, 2.0, 5.8, "240V / 120V Dual"),
    ("DeWalt DW735X 13-Inch Thickness Planer Chip Ejection", 4.0, 4000, 1.5, 4.9, "120V 15A / 20A"),
    ("Jet JDC-1.5 (1.5 HP) Cyclone Dust Collector", 6.0, 4000, 1.5, 6.2, "115V / 230V"),
    ("Jet DC-1100VX-CK (1.5 HP) Vortex Cone Canister Collector", 6.0, 4000, 1.5, 5.5, "115V / 230V"),
    ("Laguna B|Flux 1HP & C|Flux 1.5HP Cyclone Collector", 6.0, 4000, 1.5, 6.0, "115V / 230V"),
    ("Laguna P|Flux 3HP HEPA Cyclone Cabinet Shop Collector", 8.0, 4000, 3.0, 8.5, "230V Single-Phase"),
    ("Grizzly G0860 1.5 HP Portable Cyclone Dust Collector", 6.0, 4000, 1.5, 6.1, "120V / 240V"),
    ("Grizzly G0710 / G0861 2 HP Wall-Mount Cyclone Collector", 6.0, 4000, 2.0, 7.2, "240V 15A"),
    ("Oneida Air Systems Supercell High-Pressure Collector", 4.0, 4500, 2.5, 12.5, "240V High-Vacuum"),
    ("Oneida Dust Deputy 2.5 & Deluxe Cyclone Separator", 2.5, 4200, 1.0, 3.8, "120V Shop Vac / 4\" Port"),
    ("Powermatic PM1300TX-CK (1.75 HP) TurboCone Canister", 6.0, 4000, 1.75, 5.9, "115V / 230V"),
    ("Rikon 10-326 14-Inch Deluxe Bandsaw Dual-Port Setup", 4.0, 4000, 1.5, 5.2, "120V / 240V"),
    ("SuperMax 19-38 & 16-32 Open-End Drum Sander", 4.0, 4500, 2.0, 6.4, "120V / 240V"),
    ("8-Inch Helical-Head Jointer Heavy Chip Extraction", 4.0, 4000, 1.5, 5.0, "240V / 120V"),
    ("15-Inch Helical-Head Floor Planer (6-Inch Port)", 6.0, 4000, 2.5, 6.8, "240V Single-Phase"),
    ("3HP Spindle Shaper & Router Table Dual-Port Extraction", 5.0, 4000, 2.0, 5.6, "240V / 120V"),
    ("4x4 & 4x8 CNC Router Table Dust Boot (4-Inch Hose)", 4.0, 4200, 1.5, 5.4, "120V / 240V"),
    ("12-Inch Sliding Compound Miter Saw Dust Hood", 4.0, 3800, 1.5, 4.8, "120V 15A"),
    ("WEN DC1300 (1,300 CFM) & 3410 Ambient Air Cleaner", 6.0, 3800, 1.5, 4.9, "120V 15A"),
    ("Shop Fox W1666 2 HP 1,550 CFM Dust Collector", 6.0, 4000, 2.0, 6.2, "240V 15A"),
    ("Harvey G700 Gyro Air 2 HP Axial Centrifuge Collector", 6.0, 4200, 2.0, 7.8, "240V Single-Phase"),
    ("Rockler Dust Right 650 CFM & 1250 CFM Wall-Mount", 4.0, 4000, 1.5, 5.1, "120V 15A"),
    ("6-Inch PVC Main Trunk Line (2-Car Garage Woodshop)", 6.0, 4000, 2.0, 6.8, "240V 20A"),
    ("5-Inch Spiral Metal Ducting Small Shop Main Line", 5.0, 4000, 1.75, 5.9, "120V / 240V"),
    ("4-Inch Single-Machine Direct Flex Hose Setup", 4.0, 4000, 1.5, 5.2, "120V 15A"),
    ("7-Inch / 8-Inch Two-Machine Simultaneous Shop Trunk", 7.0, 4000, 3.0, 8.2, "240V 30A"),
    ("Wynn Environmental 35A / MERV-15 Canister Upgrade", 6.0, 4000, 2.0, 6.0, "120V / 240V"),
    ("Clear Vue Cyclones CV1800 (5 HP) Bill Pentz Spec", 6.0, 4200, 3.0, 8.8, "240V 30A"),
    ("Festool CT 36 E & Fein Turbo I HEPA Extractor", 2.5, 4500, 1.2, 4.2, "120V Tool-Triggered"),
    ("1,000 CFM Ceiling Air Filtration System (20x24 Garage)", 6.0, 4000, 1.5, 5.0, "120V Remote Timer")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=4.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_dust_queries():
    discovered = []
    seeds = [
        "dust collector cfm calculator for ",
        "what size dust collector for ",
        "jet dust collector ",
        "oneida dust deputy "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref or "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|cfm|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        is_six = "6 inch" in cleaned or "2 hp" in cleaned or "3 hp" in cleaned or "cyclone" in cleaned
                        if is_six:
                            discovered.append((cleaned.title(), 6.0, 4000, 2.0, 6.2, "240V / 120V"))
                        else:
                            discovered.append((cleaned.title(), 4.0, 4000, 1.5, 5.2, "120V / 240V"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_dust_data(dust_tuple):
    """Mesin Fisika Ventilasi Industri ACGIH & Persamaan Bill Pentz (100% bebas gagal)."""
    model_name, port_dia_in, target_fpm, rec_hp, sp_wg, volt_spec = dust_tuple

    # Luas Penampang Pipa (Sq Ft): Area = pi * (Radius_in / 12)^2
    radius_ft = (port_dia_in / 2.0) / 12.0
    area_sqft = round(math.pi * (radius_ft ** 2), 4)

    # Debit Udara Aktual (CFM) pada Kecepatan Target (FPM): Q = V * A
    actual_cfm_needed = int(round(target_fpm * area_sqft, -1))
    # Rated Blower Free-Air CFM (kompensasi kehilangan 40% akibat tekanan statis pipa, siku, siklon & filter)
    rated_blower_cfm = int(round(actual_cfm_needed * 1.65, -1))

    # Kecepatan Tekanan (Velocity Pressure VP in. WG) = (FPM / 4005)^2
    vp_wg = round((target_fpm / 4005.0) ** 2, 2)

    return {
        "collector_name": model_name,
        "voltage_spec": volt_spec,
        "seo_title": f"{model_name} CFM, Duct Velocity (FPM) & Static Pressure Calculator (2026)",
        "meta_description": f"Calculate exact dust collection airflow ({actual_cfm_needed} net CFM / {rated_blower_cfm} blower CFM), {port_dia_in}\" duct velocity ({target_fpm} FPM), and static pressure loss ({sp_wg}\" WG) for {model_name}.",
        "specs": {
            "duct_diameter_inches": port_dia_in,
            "duct_area_sqft": area_sqft,
            "target_velocity_fpm": target_fpm,
            "net_required_cfm": actual_cfm_needed,
            "rated_blower_cfm": rated_blower_cfm,
            "recommended_motor_hp": rec_hp,
            "static_pressure_wg": sp_wg,
            "velocity_pressure_wg": vp_wg,
            "voltage_spec": volt_spec
        },
        "aerodynamic_verdict": f"To maintain the ACGIH industrial woodworking standard of {target_fpm:,} FPM (Feet Per Minute) conveying velocity inside a {port_dia_in}-inch diameter duct ({area_sqft:.3f} sq. ft. cross-section), {model_name} requires {actual_cfm_needed:,} actual working CFM at the machine hood. Accounting for {sp_wg} inches of Water Gauge (in. WG) static pressure resistance across flex hose, 90° sweeps, a cyclone separator, and a 1-micron canister filter, pair this setup with a {rec_hp} HP ({volt_spec}) dust collector rated for at least {rated_blower_cfm:,} free-air CFM.",
        "hardware_bundle": [
            {
                "badge": f"{rec_hp} HP / {rated_blower_cfm} CFM Unit",
                "title": f"{rec_hp} HP Cyclone / Canister Woodshop Dust Collector ({rated_blower_cfm}+ CFM)",
                "price_range": "$389 - $1,699",
                "amazon_query": f"{rec_hp} HP Woodworking Cyclone Dust Collector Canister Filter",
                "dust_note": f"Steel radial impeller overcomes {sp_wg}\" WG static pressure while maintaining {actual_cfm_needed}+ real-world CFM."
            },
            {
                "badge": "1-Micron Pleated Canister",
                "title": "1-Micron MERV-15 Spun-Bond Pleated Canister Filter + Molded Cyclone Separator Kit",
                "price_range": "$119 - $389",
                "amazon_query": "1 Micron Canister Filter Dust Collector Oneida Dust Deputy Cyclone",
                "dust_note": "Standard 5-to-30 micron cloth bags pump invisible respiratory dust back into your shop and choke airflow; a pleated canister triples surface area."
            },
            {
                "badge": f"{int(port_dia_in)}\" Hose & Blast Gates",
                "title": f"{int(port_dia_in)}-Inch Clear Heavy-Wall Polyurethane Dust Hose + Self-Cleaning Aluminum Blast Gates",
                "price_range": "$64 - $169",
                "amazon_query": f"{int(port_dia_in)} Inch Clear Polyurethane Dust Collection Hose Aluminum Blast Gate",
                "dust_note": f"Isolates airflow to one active tool at a time to keep main trunk velocity above {target_fpm:,} FPM without chip settling."
            },
            {
                "badge": "Ceiling Shop Air Cleaner",
                "title": "3-Speed Remote-Controlled Ceiling Ambient Shop Air Filtration System (400–1,044 CFM)",
                "price_range": "$159 - $329",
                "amazon_query": "3 Speed Remote Shop Air Filtration System Ceiling Mount Woodworking",
                "dust_note": "Captures airborne 1-to-5 micron sanding dust escaping above the table saw blade guard and router bit."
            }
        ],
        "shop_checklist": [
            f"Keep main horizontal duct velocity above 3,500 FPM and vertical chip riser velocity at {target_fpm:,} FPM ($Q = \\text{{FPM}} \\times \\text{{Area}}$); if airflow drops below 3,200 FPM, heavy planer shavings settle inside horizontal pipes and clog the line.",
            "Minimize flexible ribbed hose to the final 3 to 4 feet at the machine connection: corrugated flex hose creates 3.0x to 3.5x more static pressure loss per foot than smooth Schedule-20/SDR-35 PVC or spiral metal pipe.",
            "Use two 45-degree wyes and long-radius 45-degree elbows instead of sharp 90-degree plumbing tees; a single sharp 90-degree tee adds as much static resistance as 15 feet of straight pipe.",
            "Ground non-metallic PVC ducting only on the exterior or use static-dissipative polyurethane hose connected to your grounded machine frame to prevent static nuisance shocks."
        ],
        "faqs": [
            {
                "q": f"How many actual CFM do I need for a {port_dia_in}-inch dust port on {model_name}?",
                "a": f"A {port_dia_in}-inch duct has an internal cross-sectional area of {area_sqft:.3f} sq. ft. Multiplying by {target_fpm:,} FPM gives {actual_cfm_needed:,} actual working CFM. Because manufacturer 'Free-Air' ratings ignore duct and filter drag, choose a {rec_hp} HP collector advertised at {rated_blower_cfm:,}+ CFM."
            },
            {
                "q": f"Why does a 6-inch duct move more than double the air of a 4-inch duct?",
                "a": f"By circle geometry ($A = \\pi r^2$), a 4-inch pipe has an area of 0.087 sq. ft. (maxing out at ~350 CFM at 4,000 FPM), whereas a 6-inch pipe has an area of 0.196 sq. ft. (2.25x larger), allowing 785 CFM to flow at 4,000 FPM with less than half the friction loss."
            },
            {
                "q": f"How much static pressure loss does a cyclone separator and flex hose add?",
                "a": f"A typical cyclone lid or 2-stage separator adds 1.8\" to 2.5\" WG of static pressure loss, a clean 1-micron canister filter adds ~1.2\" WG, and every 5 feet of 4-inch flex hose adds ~1.1\" WG—totaling {sp_wg}\" WG of system resistance."
            }
        ]
    }


def generate_dust_data(dust_tuple):
    if not GEMINI_API_KEY:
        return build_deterministic_dust_data(dust_tuple)

    model_name, port_dia_in, target_fpm, rec_hp, sp_wg, volt_spec = dust_tuple
    det_fallback = build_deterministic_dust_data(dust_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Industrial Hygienist (CIH) & Woodshop Dust Collection Ventilation Engineer (ACGIH & Bill Pentz Specialist). Create an accurate 2026 CFM airflow, duct velocity (FPM), and static pressure loss (in. WG) guide for: "{model_name}".
Baseline specs: Duct Diameter={port_dia_in} Inches ({sp['duct_area_sqft']} sq ft), Target Velocity={target_fpm} FPM, Net Required Airflow={sp['net_required_cfm']} CFM, Rated Free-Air Blower={sp['rated_blower_cfm']} CFM, Motor={rec_hp} HP ({volt_spec}), Static Pressure={sp_wg} in. WG.
Return ONLY a valid JSON object matching this exact schema:
{{
  "collector_name": "{model_name}",
  "voltage_spec": "{volt_spec}",
  "seo_title": "{model_name} CFM, Duct Velocity (FPM) & Static Pressure Calculator (2026)",
  "meta_description": "Calculate exact dust collector working CFM, duct FPM velocity, static pressure loss (in. WG), and cyclone/canister sizing for {model_name}.",
  "specs": {{
    "duct_diameter_inches": {port_dia_in},
    "duct_area_sqft": {sp['duct_area_sqft']},
    "target_velocity_fpm": {target_fpm},
    "net_required_cfm": {sp['net_required_cfm']},
    "rated_blower_cfm": {sp['rated_blower_cfm']},
    "recommended_motor_hp": {rec_hp},
    "static_pressure_wg": {sp_wg},
    "velocity_pressure_wg": {sp['velocity_pressure_wg']},
    "voltage_spec": "{volt_spec}"
  }},
  "aerodynamic_verdict": "3-sentence technical summary stating duct diameter, cross-sectional area, actual CFM at 4,000 FPM, static pressure loss in inches WG, and required blower HP/free-air CFM.",
  "hardware_bundle": [
    {{
      "badge": "{rec_hp} HP Dust Collector",
      "title": "{rec_hp} HP Woodshop Cyclone / Canister Dust Collector ({sp['rated_blower_cfm']}+ CFM)",
      "price_range": "$389 - $1,699",
      "amazon_query": "{rec_hp} HP Woodworking Cyclone Dust Collector",
      "dust_note": "1-sentence impeller static pressure and CFM note"
    }},
    {{
      "badge": "1-Micron Canister & Cyclone",
      "title": "1-Micron MERV-15 Pleated Canister Filter + Cyclone Separator Kit",
      "price_range": "$119 - $389",
      "amazon_query": "1 Micron Canister Filter Dust Collector Cyclone Separator",
      "dust_note": "1-sentence fine dust filtration and surface area note"
    }},
    {{
      "badge": "{int(port_dia_in)}\" Hose & Blast Gates",
      "title": "{int(port_dia_in)}-Inch Clear Polyurethane Dust Hose + Aluminum Blast Gates",
      "price_range": "$64 - $169",
      "amazon_query": "{int(port_dia_in)} Inch Clear Polyurethane Dust Hose Aluminum Blast Gate",
      "dust_note": "1-sentence FPM velocity and branch isolation note"
    }},
    {{
      "badge": "Ceiling Air Filtration",
      "title": "3-Speed Remote Ceiling Ambient Shop Air Filtration System",
      "price_range": "$159 - $329",
      "amazon_query": "3 Speed Remote Shop Air Filtration System Woodworking",
      "dust_note": "1-sentence airborne 1-micron dust scrubbing note"
    }}
  ],
  "shop_checklist": [
    "Step 1 regarding 4,000 FPM vertical and 3,500 FPM horizontal duct velocity",
    "Step 2 regarding rigid SDR-35 PVC / metal pipe vs corrugated flex hose 3x loss",
    "Step 3 regarding 45-degree wyes and long sweeps instead of 90-degree tees",
    "Step 4 regarding 1-micron pleated canister vs 30-micron cloth bag backpressure"
  ],
  "faqs": [
    {{"q": "How many CFM do I need for {model_name}?", "a": "Exact working CFM at 4,000 FPM vs advertised free-air blower CFM."}},
    {{"q": "Should I run 4-inch or 6-inch ducting for {model_name}?", "a": "Exact sq ft area and CFM comparison between 4-inch and 6-inch pipe."}},
    {{"q": "How much CFM do I lose through flex hose and a cyclone separator?", "a": "Exact inches of water gauge (WG) static pressure breakdown."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")

    return det_fallback


def build_dust_html_page(data, slug, mon_cfg):
    coll_name = data.get("collector_name", "Woodshop Dust Collector")
    sp = data.get("specs", {})
    dia_in = round(safe_float(sp.get("duct_diameter_inches", 6.0), 6.0), 1)
    area_sqft = round(safe_float(sp.get("duct_area_sqft", 0.1963), 0.1963), 4)
    fpm = int(safe_float(sp.get("target_velocity_fpm", 4000), 4000))
    net_cfm = int(safe_float(sp.get("net_required_cfm", 785), 785))
    blower_cfm = int(safe_float(sp.get("rated_blower_cfm", 1300), 1300))
    rec_hp = round(safe_float(sp.get("recommended_motor_hp", 2.0), 2.0), 2)
    sp_wg = round(safe_float(sp.get("static_pressure_wg", 6.2), 6.2), 1)
    volt_s = sp.get("voltage_spec", "120V / 240V")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Woodworking+Cyclone+Dust+Collector+1+Micron+Filter"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{coll_name} CFM, Duct Velocity & Static Pressure Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Woodworking Dust Collector")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Shop Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$99+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🪚 {item.get('dust_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Duct Diameter vs CFM & Static Loss Reference Matrix Table
    duct_tiers = [
        ("2.5-Inch Port (Shop Vac / Sander)", "0.034 sq ft", "136 CFM @ 4,000 FPM", "153 CFM @ 4,500 FPM", "High-Vac Extractor / Dust Deputy"),
        ("4.0-Inch Duct (Single Machine)", "0.087 sq ft", "349 CFM @ 4,000 FPM", "393 CFM @ 4,500 FPM", "1.5 HP Collector (900+ Rated CFM)"),
        ("5.0-Inch Duct (Cabinet Saw / Planer)", "0.136 sq ft", "545 CFM @ 4,000 FPM", "614 CFM @ 4,500 FPM", "1.75–2.0 HP Cyclone (1,250+ CFM)"),
        ("6.0-Inch Main Trunk (Bill Pentz Spec)", "0.196 sq ft", "785 CFM @ 4,000 FPM", "884 CFM @ 4,500 FPM", "2.0–3.0 HP Cyclone (1,550+ CFM)"),
        ("8.0-Inch Commercial Multi-Tool Trunk", "0.349 sq ft", "1,396 CFM @ 4,000 FPM", "1,571 CFM @ 4,500 FPM", "3.0–5.0 HP Cyclone (2,200+ CFM)")
    ]
    matrix_rows_html = ""
    for d_lbl, a_lbl, c40_lbl, c45_lbl, m_lbl in duct_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{d_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{a_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{c40_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{c45_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{m_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("shop_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer dust-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>ACGIH Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', coll_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', coll_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">DUST</span>CFMIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Dust Collectors & Cyclones →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-zinc-950 px-3 py-1 rounded-full">{dia_in}" Duct ({net_cfm} Net CFM)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">{fpm:,} FPM | Static Loss: {sp_wg}" WG</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">{rec_hp} HP ({rated_blower_cfm(net_cfm):,}+ Blower CFM) | {volt_s}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', coll_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>ACGIH & Bill Pentz Aerodynamic Verdict:</strong> {data.get('aerodynamic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE DUCT CFM, FPM VELOCITY & STATIC PRESSURE LOSS CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {coll_name} CFM & Static Pressure Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Select your main duct diameter, target FPM conveying velocity, rigid pipe length, and flex hose length to calculate exact working CFM, static pressure loss (in. WG), and required blower HP.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="diaSelect" class="block text-xs font-medium text-zinc-400 mb-1">Duct / Port Diameter</label>
              <select id="diaSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="2.5" {"selected" if dia_in <= 2.6 else ""}>2.5" Port (Shop Vac / Sander)</option>
                <option value="4.0" {"selected" if 2.6 < dia_in <= 4.2 else ""}>4.0" Single Machine Duct</option>
                <option value="5.0" {"selected" if 4.2 < dia_in <= 5.2 else ""}>5.0" Mid-Size Main Line</option>
                <option value="6.0" {"selected" if 5.2 < dia_in <= 6.5 else ""}>6.0" High-Flow Trunk (Pentz)</option>
                <option value="8.0" {"selected" if dia_in > 6.5 else ""}>8.0" Dual-Machine Trunk</option>
              </select>
            </div>
            <div>
              <label for="fpmSelect" class="block text-xs font-medium text-zinc-400 mb-1">Target Conveying Velocity</label>
              <select id="fpmSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="3500">3,500 FPM (Horizontal Main)</option>
                <option value="4000" selected>4,000 FPM (ACGIH Standard)</option>
                <option value="4500">4,500 FPM (Heavy Wet Planer Chips)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="rigidSlider" class="text-zinc-300">Smooth PVC / Metal Pipe Run + Elbows (Feet)</label>
              <span class="text-amber-400 font-bold"><span id="rigidVal">20</span> ft Rigid</span>
            </div>
            <input id="rigidSlider" type="range" min="0" max="80" step="5" value="20" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="flexSlider" class="text-zinc-300">Corrugated Flex Hose Length (Feet — 3x Friction Loss!)</label>
              <span class="text-amber-400 font-bold"><span id="flexVal">5</span> ft Flex</span>
            </div>
            <input id="flexSlider" type="range" min="2" max="25" step="1" value="5" class="w-full accent-amber-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Actual Working CFM</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="workCfmOut">{net_cfm}</span> <span class="text-xs font-normal text-zinc-400">CFM</span></div>
            <p id="freeAirOut" class="text-xs text-amber-400 font-semibold mt-1">Need {blower_cfm:,}+ Rated Blower CFM</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Static Pressure & HP</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="spWgOut">{sp_wg}</span>" <span class="text-xs font-normal text-zinc-400">WG</span></div>
            <p id="hpSpecOut" class="text-xs text-zinc-300 font-semibold mt-1">Match: {rec_hp} HP Cyclone</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="dustAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicDustBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Dust Collector & Filter on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {coll_name} Cyclone, Canister & Ducting Kit</h2>
        <span class="text-xs text-zinc-400">MERV-15 1-Micron & 4,000 FPM Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- DUCT DIAMETER & CFM MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Woodshop Duct Diameter, Cross-Sectional Area & CFM Velocity Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Duct Diameter</th>
              <th class="py-3.5 px-4">Pipe Area (Sq Ft)</th>
              <th class="py-3.5 px-4 text-amber-400">CFM @ 4,000 FPM</th>
              <th class="py-3.5 px-4 text-emerald-400">CFM @ 4,500 FPM</th>
              <th class="py-3.5 px-4">Recommended Collector Tier</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- SHOP CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ACGIH & Bill Pentz Fine-Dust Ducting & Filtration Checklist</h2>
        <span id="dustBadge" class="text-xs font-bold bg-zinc-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({coll_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} DustCFMIndex. Independent Woodshop Ventilation & Static Pressure Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const diaSelect = document.getElementById('diaSelect');
    const fpmSelect = document.getElementById('fpmSelect');
    const rigidSlider = document.getElementById('rigidSlider');
    const flexSlider = document.getElementById('flexSlider');
    const rigidVal = document.getElementById('rigidVal');
    const flexVal = document.getElementById('flexVal');
    const workCfmOut = document.getElementById('workCfmOut');
    const freeAirOut = document.getElementById('freeAirOut');
    const spWgOut = document.getElementById('spWgOut');
    const hpSpecOut = document.getElementById('hpSpecOut');
    const dustAdviceBanner = document.getElementById('dustAdviceBanner');
    const dynamicDustBtn = document.getElementById('dynamicDustBtn');

    function recalculateDust() {{
      const diaIn = parseFloat(diaSelect.value);
      const targetFpm = parseInt(fpmSelect.value, 10);
      const rigidFt = parseInt(rigidSlider.value, 10);
      const flexFt = parseInt(flexSlider.value, 10);

      rigidVal.textContent = rigidFt;
      flexVal.textContent = flexFt;

      const radiusFt = (diaIn / 2.0) / 12.0;
      const areaSqFt = Math.PI * radiusFt * radiusFt;
      const workingCfm = Math.round(targetFpm * areaSqFt);

      // Static pressure loss in inches WG:
      // Cyclone + 1-Micron Filter base = 3.2" WG
      // Rigid pipe loss per 100ft @ 4000 FPM ~ (14.0 / diaIn)
      const lossPer100FtRigid = (14.5 / diaIn) * Math.pow(targetFpm / 4000.0, 1.85);
      const rigidLossWg = (rigidFt / 100.0) * lossPer100FtRigid;
      const flexLossWg = ((flexFt * 3.2) / 100.0) * lossPer100FtRigid;
      const totalSpWg = 3.2 + rigidLossWg + flexLossWg;

      const freeAirBlowerCfm = Math.ceil((workingCfm * (1.25 + (totalSpWg * 0.065))) / 50) * 50;

      let recHp = "1.5 HP";
      if (diaIn <= 2.5) recHp = "High-Vac Extractor + Dust Deputy";
      else if (workingCfm <= 420 && totalSpWg <= 6.5) recHp = "1.5 HP Canister Collector";
      else if (workingCfm <= 650) recHp = "1.75–2.0 HP Cyclone";
      else if (workingCfm <= 900) recHp = "2.0–3.0 HP Cyclone";
      else recHp = "3.0–5.0 HP Commercial Cyclone";

      workCfmOut.textContent = workingCfm.toLocaleString();
      freeAirOut.textContent = `Need ${{freeAirBlowerCfm.toLocaleString()}}+ Rated Blower CFM`;
      spWgOut.textContent = totalSpWg.toFixed(1);
      hpSpecOut.textContent = `Match: ${{recHp}}`;

      dustAdviceBanner.innerHTML = `🪚 <strong>ACGIH Ventilation Spec:</strong> Moving <strong>${{workingCfm.toLocaleString()}} actual CFM (${{targetFpm.toLocaleString()}} FPM in ${{diaIn}}" duct)</strong> against <strong>${{totalSpWg.toFixed(1)}}" WG static loss</strong> requires a <strong>${{recHp}} (${{freeAirBlowerCfm.toLocaleString()}}+ Free-Air CFM)</strong> with a 1-Micron Pleated Canister Filter.`;
      dynamicDustBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(recHp)}}+Woodworking+Dust+Collector+1+Micron+Canister+Filter&tag=${{amzTag}}`;
    }}

    diaSelect.addEventListener('change', recalculateDust);
    fpmSelect.addEventListener('change', recalculateDust);
    rigidSlider.addEventListener('input', recalculateDust);
    flexSlider.addEventListener('input', recalculateDust);
    recalculateDust();

    const checks = document.querySelectorAll('.dust-check');
    const badge = document.getElementById('dustBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rated_blower_cfm(net_val):
    return int(round(net_val * 1.65, -1))


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Woodworking+Cyclone+Dust+Collector+1+Micron+Filter"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('duct_in', 6.0)}" Duct | {item.get('net_cfm', 785)} CFM</span>
            <span class="text-xs text-zinc-400">{item.get('hp', 2.0)} HP | {item.get('sp_wg', 6.2)}" WG</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['collector_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate CFM, FPM & Static Loss →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DustCFMIndex — Woodshop Dust Collector CFM, Duct Velocity & Static Pressure Calculator (2026)</title>
  <meta name="description" content="Calculate exact woodshop dust collector working CFM at 4,000 FPM duct velocity, static pressure loss (in. WG), and 1-micron canister filter sizing for SawStop, DeWalt, Jet, Laguna, Grizzly, and Oneida setups.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="DustCFMIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">DUST</span>CFMIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Dust Collectors & Cyclones →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Woodshop Dust Collector CFM, Duct FPM & Static Pressure Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your woodworking machine or dust collector model below to calculate 4,000 FPM working CFM, flex-hose static pressure loss (in. WG), and 1-micron canister filter requirements.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search machine or collector (e.g. SawStop, DeWalt DW735, Jet DC-1100VX, Laguna C|Flux, Oneida, 6-Inch Duct...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="dustGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} DustCFMIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('dustGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DustCFMIndex Woodshop Dust Collection & Static Pressure Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Woodshop Dust Collector CFM, 4,000 FPM Duct Velocity & Static Pressure Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_DUST:
        candidates.append((CUSTOM_DUST.strip(), 6.0, 4000, 2.0, 6.2, "240V / 120V"))
    candidates.extend(SEED_COLLECTORS)
    candidates.extend(discover_google_dust_queries())

    new_urls = []
    count = 0

    for dust_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        c_name = dust_tuple[0]
        slug = slugify(f"{c_name}-cfm-static-pressure-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating woodshop dust collector CFM & static pressure calculator for: {c_name}...")
        try:
            data = generate_dust_data(dust_tuple)
            build_dust_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "collector_name": data.get("collector_name", c_name),
                "slug": slug,
                "title": data.get("seo_title", f"{c_name} CFM Calculator"),
                "description": data.get("meta_description", ""),
                "duct_in": round(safe_float(sp.get("duct_diameter_inches", dust_tuple[1]), dust_tuple[1]), 1),
                "net_cfm": int(safe_float(sp.get("net_required_cfm", 785), 785)),
                "hp": round(safe_float(sp.get("recommended_motor_hp", dust_tuple[3]), dust_tuple[3]), 2),
                "sp_wg": round(safe_float(sp.get("static_pressure_wg", dust_tuple[4]), dust_tuple[4]), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {c_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new woodshop dust collector CFM calculator pages.")


if __name__ == "__main__":
    main()
