# 🚁 Thermal Exploration Drone

An AI-powered autonomous drone system for thermal-based area scanning and military object identification using MAVSDK and Gazebo simulation.

---

## 📌 Overview

Automated rectangular area scanning drone with lawnmower (zigzag) flight pattern. Simulates thermal detection with manual target confirmation and evidence capture.

**Tech Stack:** PX4 Autopilot • Gazebo • MAVSDK (Python) • QGroundControl

---

## ✨ Features

- User-defined rectangular scan area (NW & SE coordinates)
- Automatic yaw alignment and zigzag flight pattern
- Simulated thermal detection at each waypoint
- Manual military target confirmation
- Automatic photo capture on confirmation
- Precision return-to-home and mission logging

---

## 🚀 Quick Start
```bash
# Launch PX4 SITL with Gazebo
cd PX4-Autopilot
make px4_sitl gazebo

# Run the drone script
python thermal_exploration_drone.py
```

---

## 📊 Mission Output
```
🛰️ Scan WP 5 | lat=47.397, lon=8.545 | Yaw: 124.5°
[ARRIVED] Holding 3s...
🚩 Is the detected object MILITARY? (y/n): y
✅ FLAG=True | 📸 Photo captured

═══════════════════════════════
📊 MISSION SUMMARY
═══════════════════════════════
Total points visited : 18
Military detected    : 3
Clear (non-military) : 15
═══════════════════════════════
```

---

## 🔮 Future Enhancements

- Real thermal camera integration (FLIR)
- YOLO-based automatic object detection
- Multi-drone cooperative scanning
- Real-time dashboard with live streaming

---

## ⚠️ Disclaimer

Educational and simulation purposes only. Not for real-world military operations.

---

## 👨‍💻 Author

**Basel Felemban** - AI Specialist


---

⭐ Star this repo if you found it useful!
