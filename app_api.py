from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from backend_core import (
    parse_query_nlp, 
    handle_command_core, 
    log_query_to_csv,
    add_or_update_station,
    add_or_update_bus,
    add_or_update_schedule,
    get_station_by_id,
    get_bus_by_id,
    get_schedule_by_bus_id,
    get_all_stations,
    get_all_buses,
    get_all_schedules
)

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/query", methods=["POST"])
def api_query():
    try:
        data = request.get_json(force=True)
        q = data.get("q", "")
        print(f"👉 Incoming query: {q}")

        # Step 1: NLP parse
        parsed = parse_query_nlp(q)
        print(f"🔎 Parsed intent: {parsed}")

        # Step 2: Handle command (mock mode for now)
        result = handle_command_core(parsed, mode="mock")

        # Step 3: Log query + response
        try:
            log_query_to_csv(q, result)
        except Exception as e:
            print("⚠️ Log failed:", e)

        return jsonify({"status": "ok", "parsed": parsed, "result": result})
    except Exception as e:
        print("❌ API error:", e)
        return jsonify({"status": "error", "error": str(e)}), 500

# --- NEW ADMIN API ENDPOINTS ---

@app.route("/api/admin/station", methods=["POST"])
def admin_station():
    data = request.get_json()
    station_id = data.get("id")
    station_name = data.get("name")
    if not station_id or not station_name:
        return jsonify({"status": "error", "message": "Missing station ID or name."}), 400
    
    if add_or_update_station(station_id, station_name):
        return jsonify({"status": "ok", "message": "Station record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update station record."})

@app.route("/api/admin/bus", methods=["POST"])
def admin_bus():
    data = request.get_json()
    bus_id = data.get("id")
    lat = data.get("lat")
    lon = data.get("lon")
    if not bus_id or not lat or not lon:
        return jsonify({"status": "error", "message": "Missing bus ID, latitude, or longitude."}), 400
        
    if add_or_update_bus(bus_id, lat, lon):
        return jsonify({"status": "ok", "message": "Bus record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update bus record."})

@app.route("/api/admin/schedule", methods=["POST"])
def admin_schedule():
    data = request.get_json()
    bus = data.get("bus")
    src = data.get("src")
    dest = data.get("dest")
    dep = data.get("dep")
    arr = data.get("arr")
    if not bus or not src or not dest or not dep or not arr:
        return jsonify({"status": "error", "message": "Missing schedule details."}), 400

    if add_or_update_schedule(bus, src, dest, dep, arr):
        return jsonify({"status": "ok", "message": "Schedule record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update schedule record."})
    
# --- NEW ADMIN API GET ENDPOINTS ---
@app.route("/api/admin/get_station/<station_id>", methods=["GET"])
def get_station_details(station_id):
    record = get_station_by_id(station_id)
    if record:
        return jsonify({"status": "ok", "data": record})
    return jsonify({"status": "error", "message": "Station not found."})

@app.route("/api/admin/get_bus/<bus_id>", methods=["GET"])
def get_bus_details(bus_id):
    record = get_bus_by_id(bus_id)
    if record:
        return jsonify({"status": "ok", "data": record})
    return jsonify({"status": "error", "message": "Bus not found."})

@app.route("/api/admin/get_schedule/<bus_id>", methods=["GET"])
def get_schedule_details(bus_id):
    record = get_schedule_by_bus_id(bus_id)
    if record:
        return jsonify({"status": "ok", "data": record})
    return jsonify({"status": "error", "message": "Schedule not found."})

# NEW: Endpoints to get all records
@app.route("/api/admin/get_all_stations", methods=["GET"])
def get_all_stations_api():
    result = get_all_stations()
    return jsonify({"status": "ok", "result": result})

@app.route("/api/admin/get_all_buses", methods=["GET"])
def get_all_buses_api():
    result = get_all_buses()
    return jsonify({"status": "ok", "result": result})

@app.route("/api/admin/get_all_schedules", methods=["GET"])
def get_all_schedules_api():
    result = get_all_schedules()
    return jsonify({"status": "ok", "result": result})

if __name__ == "__main__":
    print("Starting TransitMate API on port 5000 (mock/oracle mode).")
    app.run(host="0.0.0.0", port=5000, debug=True)