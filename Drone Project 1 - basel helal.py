import asyncio
import math
from datetime import datetime
from mavsdk import System


ALTITUDE_ABOVE_HOME = 10.0
DWELL_SECONDS_PER_POINT = 3
ARM_TAKEOFF_SETTLE_SEC = 8
ARRIVAL_RADIUS_M = 2.0

shared_pos = {"lat": None, "lon": None}

# Functions

def calculate_yaw_deg(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points in degrees."""
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def haversine_m(lat1, lon1, lat2, lon2):
    """Calculate distance between coordinates in meters."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def lerp_latlon(a, b, t):
    """Interpolate between two points."""
    return (a[0] + t*(b[0]-a[0]), a[1] + t*(b[1]-a[1]))

async def position_listener(drone: System):
    """Continuously update shared position."""
    try:
        async for pos in drone.telemetry.position():
            if pos.latitude_deg and pos.longitude_deg:
                shared_pos["lat"] = pos.latitude_deg
                shared_pos["lon"] = pos.longitude_deg
            await asyncio.sleep(0)
    except (asyncio.CancelledError, Exception):
        return

async def wait_until_reached(tgt_lat, tgt_lon, radius_m=ARRIVAL_RADIUS_M, timeout_s=120.0):
    """Wait until drone reaches target."""
    start = asyncio.get_event_loop().time()
    while True:
        if shared_pos["lat"]:
            dist = haversine_m(shared_pos["lat"], shared_pos["lon"], tgt_lat, tgt_lon)
            print(f"[WAIT] Distance to target: {dist:.1f} m", end="\r")
            if dist <= radius_m:
                print()
                return True
        
        if asyncio.get_event_loop().time() - start > timeout_s:
            print("\n[WAIT] Timeout reached — continuing.")
            return False
        
        await asyncio.sleep(0.1)

def log_event(note: str):
    """Log event to file with timestamp."""
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    with open("detections.log", "a", encoding="utf-8") as f:
        f.write(f"{ts} | {note}\n")

async def capture_evidence(drone: System, note: str):
    """Capture photo and log event."""
    try:
        await drone.camera.take_photo()
        print(f"[📸 CAPTURE] Photo request sent.")
    except Exception as e:
        print(f"[⚠️ CAPTURE] Camera error: {e}")
    log_event(note)

def ask_if_military(label):
    """Prompt user for military detection."""
    ans = input(f"\n🚩 At {label}: Is the detected object MILITARY? (y/n): ").strip().lower()
    return ans in ("y", "yes")

def generate_lawnmower_waypoints(corners, line_spacing_m):
    """Generate zigzag scan pattern waypoints."""
    SW, SE, NE, NW = corners
    width_m = haversine_m(SW[0], SW[1], SE[0], SE[1])
    n_steps = max(1, math.ceil(width_m / line_spacing_m))
    
    waypoints = []
    for k in range(n_steps + 1):
        t = min(1.0, k / n_steps)
        south_pt = lerp_latlon(SW, SE, t)
        north_pt = lerp_latlon(NW, NE, t)
        
        if k % 2 == 0:
            waypoints.extend([("Scan line", north_pt[0], north_pt[1]),
                            ("Scan line", south_pt[0], south_pt[1])])
        else:
            waypoints.extend([("Scan line", south_pt[0], south_pt[1]),
                            ("Scan line", north_pt[0], north_pt[1])])
    return waypoints

async def goto_and_check(drone, prev_lat, prev_lon, lat, lon, alt, label, stats):
    """Navigate to point, wait for arrival, then check for military objects."""
    yaw_deg = calculate_yaw_deg(prev_lat, prev_lon, lat, lon)
    
    print(f"\n{'='*60}")
    print(f"🛰️  NAVIGATION | {label}")
    print(f" → Coordinates: lat={lat:.6f}, lon={lon:.6f}, alt={alt:.1f} m")
    print(f" → Yaw direction: {yaw_deg:.1f}°")
    print('='*60)
    
    await drone.action.goto_location(lat, lon, alt, yaw_deg)
    await wait_until_reached(lat, lon)
    
    print(f"[ARRIVED] {label} reached. Holding {DWELL_SECONDS_PER_POINT}s…")
    await asyncio.sleep(DWELL_SECONDS_PER_POINT)
    
    if ask_if_military(label):
        print("✅ FLAG=True (Military target confirmed by user)")
        await capture_evidence(drone, f"FLAG=True at {label} ({lat:.6f},{lon:.6f})")
        stats["detected"] += 1
    else:
        print("❌ FLAG=False (Non-military target)")
        log_event(f"FLAG=False at {label} ({lat:.6f},{lon:.6f})")
        stats["clear"] += 1

async def run():
    drone = System()
    print("🔗 Connecting to PX4…")
    await drone.connect(system_address="udp://:14540")
    print("Drone connected.\n")
    
    pos_task = asyncio.create_task(position_listener(drone))
    
    print("Arming…")
    await drone.action.arm()
    print(" Armed.\n")
    
    print("Taking off…")
    await drone.action.takeoff()
    await asyncio.sleep(ARM_TAKEOFF_SETTLE_SEC + 10)
    
    print("Getting home location…")
    home = await anext(drone.telemetry.home())
    home_lat, home_lon = home.latitude_deg, home.longitude_deg
    flying_alt = home.absolute_altitude_m + ALTITUDE_ABOVE_HOME
    print(f"Flight altitude (MSL): {flying_alt:.2f} m\n")
    
    # Get scan area input
    print("⬛ Enter scan area:")
    nw_str = input("\n   TOP-LEFT (NW) corner (lat,lon): ").strip()
    se_str = input("   BOTTOM-RIGHT (SE) corner (lat,lon): ").strip()
    nw_lat, nw_lon = map(float, nw_str.replace(" ", "").split(","))
    se_lat, se_lon = map(float, se_str.replace(" ", "").split(","))
    
    # Calculate remaining corners
    corners = [(se_lat, nw_lon), (se_lat, se_lon), (nw_lat, se_lon), (nw_lat, nw_lon)]
    
    spacing_m = float(input("Line spacing between scan stripes (meters): ").strip())
    scan_waypoints = generate_lawnmower_waypoints(corners, spacing_m)
    print(f"\n Generated {len(scan_waypoints)} waypoints for rectangular scan.")
    
    # Execute scan
    stats = {"detected": 0, "clear": 0}
    prev_lat, prev_lon = home_lat, home_lon
    
    for i, (_, lat, lon) in enumerate(scan_waypoints, start=1):
        await goto_and_check(drone, prev_lat, prev_lon, lat, lon, flying_alt, 
                           f"Scan WP {i}", stats)
        prev_lat, prev_lon = lat, lon
    
    # Return home and land
    print("\n Returning to exact Home…")
    yaw_back = calculate_yaw_deg(prev_lat, prev_lon, home_lat, home_lon)
    await drone.action.goto_location(home_lat, home_lon, flying_alt, yaw_back)
    await wait_until_reached(home_lat, home_lon)
    
    print("Landing at Home…")
    await drone.action.land()
    
    pos_task.cancel()
    try:
        await pos_task
    except asyncio.CancelledError:
        pass
    
    total = stats["detected"] + stats["clear"]
    print(f"\n{'-'*60}")
    print(" MISSION SUMMARY")
    print(f" • Total points visited  : {total}")
    print(f" • Military detected     : {stats['detected']}")
    print(f" • Clear (non-military)  : {stats['clear']}")
    print('-'*60)
    log_event(f"SUMMARY | total={total} | detected={stats['detected']} | clear={stats['clear']}")
    print(" Mission complete at Home!")

if __name__ == "__main__":
    asyncio.run(run())