# USV SWARM PLANNER
## Maritime Mission Planning System v2.4

---

## ΕΓΚΑΤΑΣΤΑΣΗ & ΕΚΚΙΝΗΣΗ (Ελληνικά)

### Απαιτήσεις
- Python 3.9 ή νεότερο (https://python.org)
- Σύνδεση internet (για τον χάρτη και το Open-Meteo API)

### Βήματα
1. Αποσυμπίεσε τον φάκελο `usv_swarm_planner` στην Επιφάνεια Εργασίας σου.
2. Κάνε διπλό κλικ στο `START.py` (ή τρέξε: `python START.py`)
3. Ο browser ανοίγει αυτόματα στο http://localhost:8765
4. Για τερματισμό: **Ctrl+C** στο terminal

### Αν το START.py δεν ανοίγει με διπλό κλικ:
- Windows: Δεξί κλικ → "Open with" → Python
- ή άνοιξε Terminal/CMD, πήγαινε στον φάκελο και γράψε: `python START.py`

---

## INSTALLATION & LAUNCH (English)

### Requirements
- Python 3.9+ (https://python.org)
- Internet connection (for maps and weather API)

### Steps
1. Extract `usv_swarm_planner` folder to your Desktop.
2. Double-click `START.py` (or run: `python START.py`)
3. Browser opens automatically at http://localhost:8765
4. To stop: **Ctrl+C** in the terminal window

---

## ΛΕΙΤΟΥΡΓΙΕΣ / FEATURES

### 🗺 Mission Planning
- Κλικ στον χάρτη για Departure / Destination / Waypoints
- Αυτόματος υπολογισμός διαδρομής (Baseline + Optimized)
- Real-time ETA, Distance, Energy consumption
- Save missions to SQLite database

### ⛵ Maritime Awareness
- Live weather από Open-Meteo Marine API
- Wave height / direction / period
- Wind speed & direction
- AIS targets με CPA / TCPA alerts
- Wave height forecast chart (24h)

### 💊 Vehicle Health
- Live fuel gauge με BINGO FUEL alert (<20%)
- Telemetry polling (speed, heading, RPM, roll)
- 9 system status indicators
- Comms loss simulation → RTB / LOITER

### 🔷 Swarm / MUM-T
- 5 USV management
- 6 formation types (Line Ahead, Echelon, Diamond, etc.)
- UAV (Schiebel S-100) MUM-T integration
- Shared COP, Sensor Fusion, MAVLink

### ⚡ ORM Risk Assessment
- 6 risk factors με interactive sliders
- Real-time risk calculation (GREEN/YELLOW/RED)
- API-backed risk assessment engine
- Automatic recommendations

### 📊 Analytics
- Mission statistics & summaries
- Energy consumption charts
- Route efficiency comparison
- Risk distribution pie chart

### ▶ Mission Replay
- Playback με ×1/×2/×4/×8 speed
- Event log timeline
- Seek bar navigation

---

## API ENDPOINTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | System status |
| GET | /api/weather?lat=X&lon=Y | Marine weather |
| POST | /api/route/compute | Compute route + energy |
| POST | /api/orm/assess | ORM risk assessment |
| POST | /api/missions | Save mission |
| GET | /api/missions | List missions |
| GET | /api/missions/{id} | Get mission details |
| GET | /api/telemetry/live | Live telemetry |
| GET | /api/ais/targets | AIS targets |
| GET | /api/swarm/status | Swarm status |
| GET | /api/analytics/summary | Analytics data |

---

## PROJECT STRUCTURE

```
usv_swarm_planner/
├── START.py              ← Entry point — run this
├── README.md
├── backend/
│   ├── main.py           ← FastAPI server + all API logic
│   └── requirements.txt
├── frontend/
│   └── index.html        ← Full UI (Leaflet + Canvas charts)
├── data/
│   └── usv_swarm.db      ← SQLite (auto-created)
└── logs/                 ← (reserved for telemetry logs)
```

---

## PLATFORM DATABASE

| Platform | Length | Cruise Speed | Max Wave | Base Consumption |
|----------|--------|-------------|----------|-----------------|
| Kongsberg Sounder | 8m | 6-8 kts | 3.5m | 5000 Wh/NM |
| MANTAS T-38 | 3.8m | 4-6 kts | 2.0m | 3500 Wh/NM |
| Textron CUSV | 7.3m | 8-12 kts | 3.0m | 6500 Wh/NM |

---

## ENERGY MODEL

```
Base Energy    = Distance × 5000 Wh/NM
Wave Penalty   = floor(WaveHeight / 0.5) × 15% per step
Wind Penalty   = max(0, (WindSpeed-10) / 10) × 8%
Final Energy   = Base × (1 + WavePenalty + WindPenalty)
Reserve (20%)  = Final × 0.20
```

---

## ΤΕΧΝΟΛΟΓΙΕΣ / TECH STACK

- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Frontend**: HTML5, Vanilla JS, Leaflet 1.9.4
- **Charts**: Canvas 2D API
- **Database**: SQLite3
- **Weather**: Open-Meteo Marine API (free, no key needed)
- **Maps**: OpenStreetMap (Leaflet)
- **Path Planning**: A* (simplified grid, marine)

---

## Επικοινωνία / Contact

Αναπτύχθηκε για ακαδημαϊκή έρευνα MUM-T / USV στο πλαίσιο AMSS — UNIWA
