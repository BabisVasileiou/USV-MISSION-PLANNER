from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import math
import heapq
import requests
import json
import traceback
from datetime import datetime
from shapely.geometry import Point, LineString, Polygon, shape
from shapely.strtree import STRtree

# ═════════════════════════════════════════════════════════════════════════════
# 1. INITIALIZATION & DATA LOADING
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="USV Mission Planner API v3", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

land_polygons = []
spatial_index = None

try:
    with open('../data/greece_coastline.geojson', 'r', encoding='utf-8') as f:
        geo_data = json.load(f)
    for feature in geo_data['features']:
        geom = shape(feature['geometry'])
        if geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms: land_polygons.append(poly)
        elif geom.geom_type == 'Polygon':
            land_polygons.append(geom)
    spatial_index = STRtree(land_polygons)
    print(f"✅ Loaded {len(land_polygons)} geometries from GeoJSON.")
except Exception as e:
    print(f"❌ Map Loading Error: {e}")

# Αντιστοίχιση των νέων UI Platforms στα παλιά Physics Profiles
USV_PROFILES = {
    "Kongsberg Sounder USV (8m)": {"name": "Kongsberg Sounder", "max_wave": 2.75, "speed": 11.0, "base_cost": 17500, "wave_penalty": 0.125},
    "MANTAS T-38 USV":            {"name": "MANTAS T-38", "max_wave": 1.75, "speed": 20.0, "base_cost": 62, "wave_penalty": 0.175},
    "Textron CUSV":               {"name": "Textron CUSV", "max_wave": 4.5, "speed": 12.0, "base_cost": 53000, "wave_penalty": 0.065}
}

GRID_LATS = [34.2, 35.0, 35.8, 36.6, 37.4, 38.2, 39.0, 39.8, 40.6, 41.4]
GRID_LONS = [19.5, 20.5, 21.5, 22.5, 23.5, 24.5, 25.5, 26.5, 27.5, 28.5]
WEATHER_GRID_COORDS = [(lat, lon) for lat in GRID_LATS for lon in GRID_LONS]

# ═════════════════════════════════════════════════════════════════════════════
# 2. PYDANTIC MODELS (API SCHEMAS)
# ═════════════════════════════════════════════════════════════════════════════

class Waypoint(BaseModel):
    lat: float
    lon: float
    wp_type: str
    speed_kts: Optional[float] = 12.0

class RouteRequest(BaseModel):
    name: str
    platform: str
    cruise_speed_kts: float
    safety_distance_nm: float
    resolution_nm: float
    no_go_polygons: List[list] = []
    departure_datetime: Optional[str] = None
    waypoints: List[Waypoint]

class ORMRequest(BaseModel):
    wave_height: float
    wind_speed: float
    traffic_count: int
    distance_nm: float
    fuel_pct: int
    comms_type: str
    wave_period: float
    ocean_current_kn: float

# ═════════════════════════════════════════════════════════════════════════════
# 3. CORE LOGIC (PHYSICS, MATH & ORM)
# ═════════════════════════════════════════════════════════════════════════════

def haversine(lat1, lon1, lat2, lon2):
    R = 3440.065 # Nautical Miles
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def intersects_land(lat1, lon1, lat2, lon2, standoff_nm=1.0, dyn_obstacles=[]):
    line = LineString([(lon1, lat1), (lon2, lat2)])
    standoff_deg = standoff_nm * 0.0166 # 1 NM is roughly 0.0166 degrees
    
    if spatial_index:
        search_area = line.buffer(standoff_deg)
        for idx in spatial_index.query(search_area):
            poly = land_polygons[idx]
            if poly.distance(line) < standoff_deg: 
                return True
            
    if dyn_obstacles:
        for obs in dyn_obstacles:
            if Point(lon2, lat2).within(obs) or line.intersects(obs): 
                return True
    return False

def get_live_weather_grid():
    lats_param = ",".join([str(c[0]) for c in WEATHER_GRID_COORDS])
    lons_param = ",".join([str(c[1]) for c in WEATHER_GRID_COORDS])
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lats_param}&longitude={lons_param}&current=wave_height,wave_direction,wind_speed_10m,wind_direction_10m"
    grid_results = []
    try:
        res = requests.get(url, timeout=3).json()
        if isinstance(res, list):
            for idx, item in enumerate(res):
                curr = item.get("current", {})
                grid_results.append({
                    "lat": WEATHER_GRID_COORDS[idx][0], 
                    "lon": WEATHER_GRID_COORDS[idx][1], 
                    "wave_height": curr.get("wave_height", 0.5), 
                    "wave_direction": curr.get("wave_direction", 180.0),
                    "wind_speed": curr.get("wind_speed_10m", 10.0) * 1.94384, # km/h to knots
                    "wind_direction": curr.get("wind_direction_10m", 180.0)
                })
        return grid_results
    except Exception:
        return [{"lat": c[0], "lon": c[1], "wave_height": 0.5, "wave_direction": 180.0, "wind_speed": 10.0} for c in WEATHER_GRID_COORDS]

class ORMAssessor:
    @staticmethod
    def calculate(data: dict):
        wh = data.get('wave_height', 0)
        ws = data.get('wind_speed', 0)
        fp = data.get('fuel_pct', 100)
        
        w_score = 10 if wh < 1.0 else 40 if wh < 2.5 else 80 if wh < 4.0 else 100
        wind_score = 10 if ws < 15 else 30 if ws < 25 else 70 if ws < 35 else 100
        f_score = 100 if fp < 20 else 60 if fp < 40 else 15
        c_score = {'SATCOM': 10, '4G_LTE': 30, 'UHF': 50, 'DEGRADED': 80, 'LOST': 100}.get(data.get('comms_type', 'SATCOM'), 50)
        t_score = 10 if data.get('traffic_count', 0) < 2 else 40 if data.get('traffic_count', 0) < 5 else 80

        max_r = max(w_score, wind_score, f_score, c_score, t_score)
        avg_r = (w_score + wind_score + f_score + c_score + t_score) / 5
        tot = int((max_r * 0.7) + (avg_r * 0.3))

        if tot < 33: lvl, rec = "GREEN", "GO - Conditions Optimal."
        elif tot < 66: lvl, rec = "YELLOW", "CAUTION - Degraded Conditions."
        else: lvl, rec = "RED", "NO-GO - Exceeds Safety Parameters."

        return {"total_score": tot, "risk_level": lvl, "recommendation": rec, 
                "factors": {"sea_state": {"value": f"{wh}m", "score": w_score},
                            "wind_speed": {"value": f"{ws}kn", "score": wind_score},
                            "energy": {"value": f"{fp}%", "score": f_score},
                            "comms": {"value": data.get('comms_type','SATCOM'), "score": c_score},
                            "traffic": {"value": str(data.get('traffic_count',0)), "score": t_score}}}

# ═════════════════════════════════════════════════════════════════════════════
# 4. A* PATHFINDING ALGORITHM
# ═════════════════════════════════════════════════════════════════════════════

def calculate_route(start_node, goal_node, step, usv, standoff_nm, live_grid=None, dyn_obstacles=[], is_weather_aware=False):
    def get_wave_at(lat, lon):
        if not live_grid: return 0.0, 0.0
        closest = min(live_grid, key=lambda w: (w['lat']-lat)**2 + (w['lon']-lon)**2)
        return closest['wave_height'], closest['wave_direction']

    if intersects_land(start_node[0], start_node[1], start_node[0], start_node[1], standoff_nm, dyn_obstacles):
        return [], 0, 0

    frontier = []
    heapq.heappush(frontier, (0, start_node))
    came_from = {start_node: None}
    cost_so_far = {start_node: 0}
    found = False
    iterations = 0
    
    while frontier:
        iterations += 1
        if iterations > 30000: break 

        _, current = heapq.heappop(frontier)
        
        if haversine(current[0], current[1], goal_node[0], goal_node[1]) < 3.0:
            if not intersects_land(current[0], current[1], goal_node[0], goal_node[1], standoff_nm, dyn_obstacles):
                came_from[goal_node] = current
                found = True
                break
                
        dirs = [(step,0), (-step,0), (0,step), (0,-step), (step,step), (step,-step), (-step,step), (-step,-step)]
        for dlat, dlon in dirs:
            next_node = (round(current[0] + dlat, 3), round(current[1] + dlon, 3))
            if not (34.0 <= next_node[0] <= 42.0 and 19.0 <= next_node[1] <= 29.5): continue
            if intersects_land(current[0], current[1], next_node[0], next_node[1], standoff_nm, dyn_obstacles): continue
            
            distance = haversine(current[0], current[1], next_node[0], next_node[1])
            step_energy = distance * usv['base_cost']
            
            if is_weather_aware and live_grid:
                w_h, w_d = get_wave_at(next_node[0], next_node[1])
                if w_h > usv["max_wave"]: continue 
                
                heading = (math.degrees(math.atan2(next_node[1] - current[1], next_node[0] - current[0])) + 360) % 360
                rel_angle = math.radians(abs(w_d - heading))
                frontal_factor = max(0, math.cos(rel_angle))
                penalty = 1 + ((w_h / 0.5) * usv['wave_penalty'] * frontal_factor)
                step_energy *= penalty
            
            new_cost = cost_so_far[current] + step_energy
            if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                cost_so_far[next_node] = new_cost
                # ADMISSIBLE HEURISTIC: Using base cost ONLY, without wave penalty.
                heuristic = haversine(next_node[0], next_node[1], goal_node[0], goal_node[1]) * usv['base_cost']
                heapq.heappush(frontier, (new_cost + heuristic, next_node))
                came_from[next_node] = current
                
    if not found: return [], 0, 0
    
    path = []
    curr = goal_node
    while curr is not None:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    
    final_cost = cost_so_far.get(goal_node, 0)
    dist_total = sum(haversine(path[i][0], path[i][1], path[i+1][0], path[i+1][1]) for i in range(len(path)-1))
    
    return path, dist_total, final_cost

# ═════════════════════════════════════════════════════════════════════════════
# 5. API ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health_check():
    return {"status": "online", "land_polygons_loaded": len(land_polygons)}

@app.get("/api/weather")
def get_weather(lat: float = 38.0, lon: float = 24.0):
    grid = get_live_weather_grid()
    closest = min(grid, key=lambda w: (w['lat']-lat)**2 + (w['lon']-lon)**2)
    return {
        "wave_height": closest["wave_height"],
        "wave_direction": closest["wave_direction"],
        "wind_speed": closest.get("wind_speed", 10.0),
        "wind_direction": closest.get("wind_direction", 180.0),
        "wave_period": 6.5,
        "ocean_current_kn": 1.1,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "open-meteo-live"
    }

@app.get("/api/weather/grid")
def get_weather_grid(lat_min: float, lat_max: float, lon_min: float, lon_max: float, cells: int = 6):
    grid = get_live_weather_grid()
    filtered = [p for p in grid if lat_min <= p['lat'] <= lat_max and lon_min <= p['lon'] <= lon_max]
    return {"grid": filtered}

@app.post("/api/orm/assess")
def assess_risk(req: ORMRequest):
    return ORMAssessor.calculate(req.dict())

@app.post("/api/route/compute")
def route_compute(req: RouteRequest):
    try:
        usv = USV_PROFILES.get(req.platform, USV_PROFILES["Kongsberg Sounder USV (8m)"])
        live_grid = get_live_weather_grid()
        
        full_geo_path, full_wea_path = [], []
        dist_geo, dist_wea, en_geo, en_wea = 0, 0, 0, 0
        
        dyn_obstacles = [Polygon(zone) for zone in req.no_go_polygons if len(zone) >= 3]

        # Chain all waypoints together
        for i in range(len(req.waypoints)-1):
            s_node = (req.waypoints[i].lat, req.waypoints[i].lon)
            g_node = (req.waypoints[i+1].lat, req.waypoints[i+1].lon)
            
            p_geo, d_geo, e_geo = calculate_route(s_node, g_node, 0.05, usv, req.safety_distance_nm, dyn_obstacles=dyn_obstacles, is_weather_aware=False)
            p_wea, d_wea, e_wea = calculate_route(s_node, g_node, 0.05, usv, req.safety_distance_nm, live_grid, dyn_obstacles, is_weather_aware=True)
            
            if not p_wea: raise Exception(f"No valid path found between WP{i} and WP{i+1}")
            
            full_geo_path.extend(p_geo if i == 0 else p_geo[1:])
            full_wea_path.extend(p_wea if i == 0 else p_wea[1:])
            dist_geo += d_geo; dist_wea += d_wea
            en_geo += e_geo; en_wea += e_wea

        # Assess Risk based on route
        avg_lat, avg_lon = full_wea_path[len(full_wea_path)//2][0], full_wea_path[len(full_wea_path)//2][1]
        closest_w = min(live_grid, key=lambda w: (w['lat']-avg_lat)**2 + (w['lon']-avg_lon)**2)
        orm_res = ORMAssessor.calculate({
            "wave_height": closest_w["wave_height"], "wind_speed": closest_w.get("wind_speed", 10),
            "fuel_pct": 100, "comms_type": "SATCOM", "traffic_count": 3
        })

        return {
            "optimal_route": [{"lat": p[0], "lon": p[1]} for p in full_geo_path],
            "wave_route": [{"lat": p[0], "lon": p[1]} for p in full_wea_path],
            "distance_nm": dist_geo,
            "optimal_distance_nm": dist_geo,
            "wave_distance_nm": dist_wea,
            "eta_hrs": dist_geo / usv['speed'],
            "wave_eta_hrs": dist_wea / usv['speed'],
            "energy": {"final_energy_wh": en_geo, "wave_penalty_pct": 0},
            "wave_energy": {
                "final_energy_wh": en_wea, 
                "wave_penalty_pct": ((en_wea - en_geo) / en_geo * 100) if en_geo > 0 else 0
            },
            "orm": orm_res,
            "weather": {
                "wave_height": closest_w["wave_height"], "wave_direction": closest_w["wave_direction"],
                "wind_speed": closest_w.get("wind_speed", 10), "source": "open-meteo"
            }
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
