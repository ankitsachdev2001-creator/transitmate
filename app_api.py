from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os

from backend_core import (
    parse_query_nlp,
    handle_command_core,
    log_query_to_csv,
    add_or_update_station,
    add_or_update_bus,
    add_or_update_schedule,
    add_or_update_fare,
    get_station_by_id,
    get_bus_by_id,
    get_schedule_by_bus_id,
    get_all_stations,
    get_all_buses,
    get_all_schedules,
    get_all_fares
)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# ---------------- ROOT ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- QUERY API ----------------
@app.route("/api/query", methods=["POST"])
def api_query():
    try:
        data = request.get_json(force=True)
        q = data.get("q", "")
        print(f"👉 Incoming query: {q}")

        parsed = parse_query_nlp(q)
        print(f"🔎 Parsed intent: {parsed}")

        result = handle_command_core(parsed, mode="mongo")

        try:
            log_query_to_csv(q, result)
        except Exception as e:
            print("⚠️ Log failed:", e)

        return jsonify({"status": "ok", "parsed": parsed, "result": result})
    except Exception as e:
        print("❌ API error:", e)
        return jsonify({"status": "error", "error": str(e)}), 500


# ---------------- ADMIN APIs ----------------
@app.route("/api/admin/station", methods=["POST"])
def admin_station():
    data = request.get_json(force=True)
    station_id = data.get("station_id")
    station_name = data.get("name")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not station_id or not station_name:
        return jsonify({"status": "error", "message": "Missing station ID or name."}), 400

    if add_or_update_station(station_id, station_name, latitude, longitude):
        return jsonify({"status": "ok", "message": "Station record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update station record."})


@app.route("/api/admin/bus", methods=["POST"])
def admin_bus():
    data = request.get_json(force=True)
    bus_id = data.get("bus_id")
    license_plate = data.get("license_plate")
    lat = data.get("current_latitude")
    lon = data.get("current_longitude")

    if not bus_id or not license_plate or not lat or not lon:
        return jsonify({"status": "error", "message": "Missing bus details."}), 400

    if add_or_update_bus(bus_id, license_plate, lat, lon):
        return jsonify({"status": "ok", "message": "Bus record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update bus record."})


@app.route("/api/admin/schedule", methods=["POST"])
def admin_schedule():
    data = request.get_json(force=True)
    bus = data.get("bus_id")
    src = data.get("source_station_id")
    dest = data.get("dest_station_id")
    dep = data.get("departure_time")
    arr = data.get("arrival_time")

    if not bus or not src or not dest or not dep:
        return jsonify({"status": "error", "message": "Missing schedule details."}), 400

    if add_or_update_schedule(bus, src, dest, dep, arr):
        return jsonify({"status": "ok", "message": "Schedule record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update schedule record."})


@app.route("/api/admin/fare", methods=["POST"])
def admin_fare():
    data = request.get_json(force=True)
    src = data.get("source")
    dest = data.get("destination")
    amount = data.get("amount")

    if not src or not dest or not amount:
        return jsonify({"status": "error", "message": "Missing fare details."}), 400

    if add_or_update_fare(src, dest, amount):
        return jsonify({"status": "ok", "message": "Fare record updated successfully."})
    return jsonify({"status": "error", "message": "Failed to update fare record."})


# ---------------- GET APIs ----------------
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


@app.route("/api/admin/get_all_fares", methods=["GET"])
def get_all_fares_api():
    result = get_all_fares()
    return jsonify({"status": "ok", "result": result})


# ---------------- FALLBACK ----------------
@app.errorhandler(404)
def not_found(e):
    return send_from_directory("static", "index.html")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Running locally on port 5000...")
    app.run(host="0.0.0.0", port=5000)
