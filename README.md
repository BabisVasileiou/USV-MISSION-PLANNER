# USV Mission Planner
### Web-based Mission Planning System for Unmanned Surface Vehicles in the Greek Aegean Sea

> **MSc Project** — Π.Μ.Σ. «Μη Επανδρωμένα Αυτόνομα και Τηλεκατευθυνόμενα Συστήματα»  
> Πανεπιστήμιο Δυτικής Αττικής (UNIWA) — 2026  
> **Χαράλαμπος Βασιλείου**

---

## Περιγραφή / Description

Ένα **web-based εργαλείο υποστήριξης σχεδιασμού αποστολής (mission planner)** για Μη Επανδρωμένα Σκάφη Επιφανείας (USV) στον ελληνικό Αιγαιακό θαλάσσιο χώρο.

A **web-based mission planning tool** for Unmanned Surface Vehicles (USV) in the Greek Aegean Sea, featuring A* pathfinding, live marine weather routing, and Operational Risk Management (ORM) assessment.

---

## Χαρακτηριστικά / Features

### ✅ Υλοποιημένα / Implemented
- **A\* Pathfinding** — Βελτιστοποίηση διαδρομής σε διακριτό γεωγραφικό πλέγμα 0.05° με 8-συνδεσιμότητα και παραδεκτή ευρετική (admissible heuristic)
- **Αποφυγή Ξηράς** — Χωρικός δείκτης STRtree (Shapely) με 695 πολύγωνα ακτογραμμής Ελλάδας (`greece_coastline.geojson`)
- **Weather-Aware Routing** — Ενσωμάτωση ζωντανών δεδομένων Open-Meteo Marine API (wave height/direction, wind speed/direction) με frontal factor penalty και hard-block κελιών
- **ORM Risk Assessment** — Εκτίμηση Επιχειρησιακού Κινδύνου 5 παραγόντων (θάλασσα, άνεμος, ενέργεια, επικοινωνίες, κυκλοφορία) → GREEN / YELLOW / RED
- **Δύο Διαδρομές ανά Αποστολή** — Γεωμετρικά βέλτιστη & weather-aware με σύγκριση ενέργειας (wave_penalty_pct)
- **3 Πλατφόρμες USV** — Kongsberg Sounder (8m), MANTAS T-38, Textron CUSV

### 🔶 Prototype / Εικονική Διεπαφή
- Swarm / MUM-T coordination (στατική διεπαφή)
- Vehicle Health / Telemetry (συνθετικά δεδομένα)
- AIS targets (hardcoded)
- Mission Simulation (animation)
- Αποθήκευση/φόρτωση αποστολών

---

## Αρχιτεκτονική / Architecture

```
USV/
├── backend/
│   ├── main.py              ← FastAPI server (USV Mission Planner API v3)
│   └── requirements.txt
├── data/
│   └── greece_coastline.geojson  ← MultiPolygon GRC, 695 πολύγωνα
├── frontend/
│   └── index.html           ← Single Page Application (Leaflet.js)
├── logs/
├── README.md
├── START.py                 ← Entry point
├── START_MAC_LINUX.sh
└── START_WINDOWS.bat
```

---

## Εγκατάσταση & Εκκίνηση / Installation & Launch

### Απαιτήσεις / Requirements
- Python 3.9+
- Σύνδεση internet (για χάρτη και Open-Meteo API)

### Βήματα / Steps

**Windows:**
```bash
START_WINDOWS.bat
```

**Mac / Linux:**
```bash
chmod +x START_MAC_LINUX.sh
./START_MAC_LINUX.sh
```

**Ή απευθείας / Or directly:**
```bash
pip install -r backend/requirements.txt
python START.py
```

Ο browser ανοίγει αυτόματα στο → **http://localhost:8765**

---

## API Endpoints

| Method | Endpoint | Περιγραφή |
|--------|----------|-----------|
| `GET` | `/api/health` | Έλεγχος υγείας υπηρεσίας |
| `GET` | `/api/weather` | Καιρός nearest-neighbor |
| `GET` | `/api/weather/grid` | Πλέγμα 10×10 καιρικών δεδομένων |
| `POST` | `/api/route/compute` | Υπολογισμός διαδρομής (A*) |
| `POST` | `/api/orm/assess` | Εκτίμηση ORM |

---

## Πλατφόρμες USV / USV Platforms

| Πλατφόρμα | max_wave | Speed | base_cost | wave_penalty |
|-----------|----------|-------|-----------|--------------|
| Kongsberg Sounder (8m) | 2.75m | 11.0 kn | 17,500 Wh/NM | 0.125 |
| MANTAS T-38 | 1.75m | 20.0 kn | 62 Wh/NM | 0.175 |
| Textron CUSV | 4.50m | 12.0 kn | 53,000 Wh/NM | 0.065 |

---

## Τεχνολογίες / Tech Stack

| Επίπεδο | Τεχνολογία |
|---------|-----------|
| Backend | Python 3.x, FastAPI, Uvicorn |
| Γεωχωρική Ανάλυση | Shapely, STRtree |
| Frontend | HTML5, Leaflet.js 1.9.4 |
| Καιρός | Open-Meteo Marine API |
| Pathfinding | A* (heapq, admissible heuristic) |
| HTTP Client | httpx, Requests |

---

## Μοντέλο Κόστους / Energy Model

```
step_energy  = distance × base_cost
penalty      = 1 + (wave_height / 0.5) × wave_penalty × max(0, cos(Δθ))
step_energy  = step_energy × penalty   # weather-aware mode
```

**Frontal factor** `max(0, cos(Δθ))`: μεγιστοποιεί ποινή για μετωπικά κύματα (head seas), μηδενίζει για ακολουθητικά (following seas).

---

## Μοντέλο ORM / ORM Model

```
total_score = 0.7 × max(factors) + 0.3 × avg(factors)

GREEN  (GO)      → total < 33
YELLOW (CAUTION) → 33 ≤ total < 66
RED    (NO-GO)   → total ≥ 66
```

---

## Γνωστοί Περιορισμοί / Known Limitations

- Σταθερό βήμα πλέγματος 0.05° (μη παραμετροποιήσιμο)
- Open-Meteo: τρέχουσες τιμές (current), όχι ωριαία πρόγνωση
- haversine: σφαιρική Γη (R=3440.065 NM), προσέγγιση ±0.3% vs WGS84
- Δεν υπάρχει δυναμικό/υδροδυναμικό μοντέλο σκάφους

---

## Άδεια / License

Για ακαδημαϊκή χρήση — UNIWA AMSS 2026.  
Academic use only — UNIWA MSc in Autonomous and Remotely Piloted Systems 2026.
