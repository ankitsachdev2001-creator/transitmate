import os
import csv
import random
import re
from datetime import datetime

# MongoDB imports
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# NLP + ML imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Oracle DB (optional)
try:
    import cx_Oracle
except ImportError:
    cx_Oracle = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_DIR = os.path.join(BASE_DIR, "mock_data")

# IMPORTANT: Replace "YOUR_API_KEY_HERE" with the actual key you generated
GOOGLE_MAPS_API_KEY = "AIzaSyCzLuWRy11sTBEICYq355QULOhyuoAohEw"

# ---------------- MongoDB Connection ----------------
mongo_client = None
db = None
def get_mongo_connection():
    global mongo_client, db
    uri = "mongodb+srv://transitmate:Dummy%40112233@cluster0.lfrl0k3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    try:
        mongo_client = MongoClient(uri, server_api=ServerApi('1'))
        # Using a fixed database name 'test' for clarity, assuming this is correct
        db = mongo_client.get_database('test')
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        return db
    except Exception as e:
        print("⚠️ MongoDB connection failed:", e)
        return None

# ---------------- NLP Intent Classifier ----------------
intent_model = None
intent_vectorizer = None

def _text_to_num(text):
    """Converts common spoken numbers (e.g., "one zero one") to digits."""
    num_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "zero": "0", "oh": "0"}
    words = text.lower().split()
    converted_num = "".join([num_map.get(word, word) for word in words])
    return converted_num

def train_intent_classifier():
    """Train simple intent classifier on demo data"""
    global intent_model, intent_vectorizer
    training_data = [
        # Station queries
        ("list all stations", "station_query"),
        ("show stations", "station_query"),
        ("what are the stations", "station_query"),
        ("stations list", "station_query"),
        ("show me the stations", "station_query"),
        ("tell me all the stations", "station_query"),
        ("where are the bus stops", "station_query"),
        ("display all stops", "station_query"),
        ("can you show me the station list", "station_query"),
        ("what bus stations are there", "station_query"),

        # Route queries
        ("show all routes", "route_query"),
        ("show routes", "route_query"),
        ("list routes", "route_query"),
        ("route 101 details", "route_query"),
        ("tell me about bus 202", "route_query"),
        ("bus 303 schedule", "route_query"),
        ("route one zero one details", "route_query"),
        ("tell me the route for bus", "route_query"),
        ("which routes are available", "route_query"),
        ("can you give me the route details for bus 101", "route_query"),
        ("what is the schedule for bus 202", "route_query"),
        ("how does bus 303 travel", "route_query"),
        ("which stops does bus 404 make", "route_query"),
        
        # Next bus queries
        ("next bus from andheri to borivali", "next_bus_query"),
        ("is there a bus from bandra to dadar", "next_bus_query"),
        ("when is the next bus from virar to churchgate", "next_bus_query"),
        ("what bus can i take from dadar to andheri", "next_bus_query"),
        ("bus schedule from bandra to dadar", "next_bus_query"),
        ("what's the earliest bus from cst to borivali", "next_bus_query"),
        ("show me buses from virar to churchgate", "next_bus_query"),
        ("when's the next bus to andheri from dadar", "next_bus_query"),
        ("find a bus from andheri to borivali", "next_bus_query"),
        ("is there any bus from bandra to dadar", "next_bus_query"),

        # Fare queries
        ("fare from bandra to dadar", "fare_query"),
        ("ticket price from cst to andheri", "fare_query"),
        ("how much is fare between andheri and borivali", "fare_query"),
        ("how much is the ticket from dadar to virar", "fare_query"),
        ("cost from borivali to andheri", "fare_query"),
        ("what is the fare from", "fare_query"),
        ("price of a ticket from", "fare_query"),
        ("how much does it cost to get from borivali to andheri", "fare_query"),
        ("calculate fare from bandra to dadar", "fare_query"),
        ("fare price from virar to churchgate", "fare_query"),

        # Track queries
        ("track bus 101", "track_query"),
        ("where is bus 202", "track_query"),
        ("bus 404 location", "track_query"),
        ("where is bus one zero one", "track_query"),
        ("track bus two zero two", "track_query"),
        ("where is bus 404", "track_query"),
        ("show me the location of bus 101", "track_query"),
        ("can you track bus 202", "track_query"),
        ("is bus 303 on the way", "track_query"),
        ("live location of bus 404", "track_query"),
        
        # Recommend queries
        ("recommend me a route", "recommend_query"),
        ("best route from bandra to cst", "recommend_query"),
        ("suggest a route from dadar to andheri", "recommend_query"),
        ("recommend a route from", "recommend_query"),
        ("suggest a route for me", "recommend_query"),
        ("find the best route from virar to churchgate", "recommend_query"),
        ("what is the fastest route from cst to borivali", "recommend_query"),
        ("can you suggest a bus from andheri to borivali", "recommend_query"),
    ]

    texts, labels = zip(*training_data)
    intent_vectorizer = TfidfVectorizer()
    X = intent_vectorizer.fit_transform(texts)

    intent_model = LogisticRegression()
    intent_model.fit(X, labels)
    print("✅ Intent classifier trained with", len(training_data), "examples.")

# Initialize the NLP model upon script start
train_intent_classifier()

def predict_intent(query: str):
    """Parse natural language query using intent classifier and extract entities."""
    global intent_model, intent_vectorizer
    if not intent_model:
        train_intent_classifier()
    X = intent_vectorizer.transform([query.lower()])
    pred = intent_model.predict(X)[0]
    return pred

def parse_query_nlp(query: str):
    """Parse natural language query using intent classifier and extract entities."""
    intent = predict_intent(query)
    query = query.lower().strip()

    # Create a structured command with intent and parameters
    parsed_cmd = {"intent": intent, "params": {}}

    if intent == "station_query":
        if "station" not in query and "stop" not in query:
            parsed_cmd["intent"] = "unknown"
            return parsed_cmd
        
    elif intent == "route_query" or intent == "track_query":
        # Capture the bus number (e.g., 103, 404, or spoken numbers)
        match = re.search(r"(?:bus|route)\s+(\d+|one zero one|two oh two|two zero two)", query)
        if match:
            raw_bus_number = match.group(1)
            bus_number = _text_to_num(raw_bus_number) if not raw_bus_number.isdigit() else raw_bus_number
            parsed_cmd["params"]["bus_number"] = bus_number
        else:
            if "route" not in query and "bus" not in query:
                parsed_cmd["intent"] = "unknown"
                return parsed_cmd

    elif intent in ["next_bus_query", "fare_query", "recommend_query"]:
        match = re.search(r"from (\w+)\s+to (\w+)", query)
        if match:
            parsed_cmd["params"]["source"] = match.group(1).title()
            parsed_cmd["params"]["destination"] = match.group(2).title()
        else:
            parsed_cmd["intent"] = "unknown"
            return parsed_cmd
    else:
        parsed_cmd["intent"] = "unknown"

    return parsed_cmd

# ---------------- DB & Mock Handlers ----------------
def get_connection():
    """Return Oracle DB connection (if available) or MongoDB connection."""
    mongo_conn = get_mongo_connection()
    if mongo_conn is not None:
        return mongo_conn
    if cx_Oracle is None:
        return None
    try:
        # NOTE: Dummy DSN and credentials for Oracle skeleton
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE")
        conn = cx_Oracle.connect(user="system", password="oracle", dsn=dsn)
        return conn
    except Exception as e:
        print("⚠️ Oracle connection failed:", e)
        return None

def handle_command_core(cmd: dict, mode="mongo"):
    """Main query handler (mock, mongo or Oracle)"""
    if mode == "mongo":
        mongo_conn = get_mongo_connection()
        if mongo_conn is not None:
            return _handle_with_mongo(mongo_conn, cmd)
    
    if mode == "oracle" and cx_Oracle:
        conn = None
        try:
            conn = get_connection()
            if conn is not None:
                return _handle_with_oracle(conn, cmd)
        finally:
            if conn is not None:
                conn.close()

    return _handle_with_mock(cmd)

# ---------------- MONGODB MODE ----------------
def _handle_with_mongo(db, cmd):
    intent = cmd["intent"]
    params = cmd["params"]

    if intent == "station_query":
        stations = list(db.stations.find({}))
        if not stations:
            return {"type": "text", "text": "No stations found in the database."}
        rows = [[s["station_name"]] for s in stations]
        return {"type": "table", "headers": ["Station Name"], "rows": rows, "text": f"Found {len(stations)} bus stations."}

    if intent == "route_query":
        bus_number_str = params.get("bus_number")
        schedule_collection = db.schedule
        
        # Handle listing all routes
        if not bus_number_str:
            rows = []
            for r in schedule_collection.find():
                source_station = db.stations.find_one({"station_id": r["source_station_id"]})
                dest_station = db.stations.find_one({"station_id": r["dest_station_id"]})
                source_name = source_station["station_name"] if source_station else r["source_station_id"]
                dest_name = dest_station["station_name"] if dest_station else r["dest_station_id"]
                rows.append([r["bus_id"], source_name, dest_name, r["departure_time"], r["arrival_time"]])
            return {"type": "table", "headers": ["Bus", "Source", "Dest", "Departure", "Arrival"], "rows": rows, "text": f"Found {len(rows)} bus schedules."}
        
        # Handle specific route query
        else:
            # NOTE: Searching by bus_id (string) in schedule collection
            found_routes = schedule_collection.find({"bus_id": bus_number_str})
            details_rows = []
            for r in found_routes:
                source_station = db.stations.find_one({"station_id": r["source_station_id"]})
                dest_station = db.stations.find_one({"station_id": r["dest_station_id"]})
                source_name = source_station["station_name"] if source_station else r["source_station_id"]
                dest_name = dest_station["station_name"] if dest_station else r["dest_station_id"]
                details_rows.append([r["bus_id"], source_name, dest_name, r["departure_time"], r["arrival_time"]])
            
            if details_rows:
                return {"type": "table", "headers": ["Bus", "Source", "Dest", "Departure", "Arrival"], "rows": details_rows, "text": f"Found {len(details_rows)} schedules for Bus {bus_number_str}."}
            else:
                return {"type": "text", "text": f"Details for Bus {bus_number_str} not found."}

    if intent == "next_bus_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            # NOTE: Searching for schedule based on station names (which are assumed to be station IDs in this context)
            schedule = db.schedule.find_one({
                "source_station_id": src, 
                "dest_station_id": dst
            })
            if schedule:
                return {"type":"text","text":f"The next bus from {src} to {dst} is Bus {schedule['bus_id']}, departing at {schedule['departure_time']}."}
            return {"type":"text","text":f"I couldn't find a direct bus schedule from {src} to {dst}."}
        return {"type":"text","text":"Please specify both source and destination stations."}

    if intent == "fare_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            # Check for both A->B and B->A routes
            fare = db.fare.find_one({"$or": [{"source": src, "destination": dst}, {"source": dst, "destination": src}]})
            if fare:
                return {"type": "text", "text": f"The fare from {src} to {dst} is ₹{fare['amount']}"}
            else:
                return {"type": "text", "text": f"Fare not found for route from {src} to {dst}."}
        return {"type": "text", "text": "Please provide both source and destination stations for the fare query."}

    # ------------------ UPDATED TRACK QUERY (FOR LEAFLET MAP) ------------------
    if intent == "track_query":
        bus_no_str = params.get("bus_number")
        if not bus_no_str:
            return {"type": "text", "text": "Please provide a bus number to track."}
            
        try:
            # CRITICAL: Use the integer route_no for searching the 'buses' collection
            bus_no_int = int(bus_no_str)
        except ValueError:
            return {"type": "text", "text": f"Invalid bus number format: '{bus_no_str}'. Please use a numeric bus number."}

        # 1. Get Bus Location
        bus = db.buses.find_one({"route_no": bus_no_int})
        if not bus:
            return {"type": "text", "text": f"Bus {bus_no_str} not found in the 'buses' collection."}
            
        try:
            # Current location fields in 'buses' are expected to be strings convertible to float
            bus_lat = float(bus.get('current_latitude', 0.0))
            bus_lon = float(bus.get('current_longitude', 0.0))
        except (TypeError, ValueError):
             return {"type": "text", "text": f"Bus {bus_no_str} location data is corrupt (lat/lon not convertible to numbers)."}

        # Simulate movement
        new_lat = bus_lat + random.uniform(-0.001, 0.001)
        new_lon = bus_lon + random.uniform(-0.001, 0.001)
        
        # Update DB with new location
        db.buses.update_one(
            {"route_no": bus_no_int}, 
            {"$set": {
                "current_latitude": str(new_lat), 
                "current_longitude": str(new_lon), 
                "timestamp": datetime.now().isoformat()
            }}
        )
        
        # 2. Get Route (Source and Destination Stations)
        # FIX: Searching the 'schedule' collection by converted bus_id (integer)
        schedule = db.schedule.find_one({"bus_id": bus_no_int}) 
        if not schedule:
             return {"type": "text", "text": f"Live location found, but no schedule found for Bus {bus_no_str}. Cannot determine the route to draw on the map."}
        
        src_id = schedule.get("source_station_id")
        dest_id = schedule.get("dest_station_id")
        
        # 3. Get Station Locations (Source and Destination)
        source_station = db.stations.find_one({"station_id": src_id})
        dest_station = db.stations.find_one({"station_id": dest_id})
        
        if not source_station or not dest_station:
            return {"type": "text", "text": f"Source or Destination station details missing for Bus {bus_no_str} route. Check 'stations' collection."}

        try:
            # 'stations' collection has 'latitude' and 'longitude' fields
            src_lat = float(source_station.get('latitude', 0.0))
            src_lon = float(source_station.get('longitude', 0.0))
            dest_lat = float(dest_station.get('latitude', 0.0))
            dest_lon = float(dest_station.get('longitude', 0.0))
        except (TypeError, ValueError):
            return {"type": "text", "text": f"Station location data is corrupt for Bus {bus_no_str} route."}

        # 4. Construct the new response object for Leaflet
        response_data = {
            "bus": {"lat": round(new_lat, 5), "lon": round(new_lon, 5), "label": f"Bus {bus_no_str} (Live)"},
            "source": {"lat": src_lat, "lon": src_lon, "label": source_station.get("station_name", src_id)},
            "destination": {"lat": dest_lat, "lon": dest_lon, "label": dest_station.get("station_name", dest_id)},
            # Center the map on the bus
            "center": {"lat": new_lat, "lon": new_lon} 
        }
        
        text_response = f"Live route for Bus {bus_no_str} from {response_data['source']['label']} to {response_data['destination']['label']} is shown on the map."
        
        # Return the new response type
        return {"type": "map_route", "data": response_data, "text": text_response}

    # ------------------ END UPDATED TRACK QUERY ------------------

    if intent == "recommend_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            options = [f"Take Bus 101 from {src} to {dst}", f"Try Bus 202 from {src} to {dst}"]
            return {"type":"text","text":random.choice(options)}
        else:
            options = ["Take Bus 101 from Andheri to Borivali", "Take Bus 202 from Bandra to Dadar"]
            return {"type":"text","text":random.choice(options)}
            
    if intent == "unknown":
        return {"type":"text","text":"Sorry, I couldn't understand your request. Please be more specific."}

    return {"type":"text","text":f"Sorry, I couldn't understand your request."}


# ---------------- MOCK MODE (fallback) ----------------
def _handle_with_mock(cmd: dict):
    # This is the fallback handler if MongoDB connection fails.
    return {"type": "text", "text": "Error: MongoDB connection failed. Falling back to mock data. Please check your connection string."}

# ---------------- ORACLE MODE (skeleton) ----------------
def _handle_with_oracle(conn, cmd):
    # This remains as a skeleton handler for Oracle DB.
    cur = conn.cursor()
    if cmd["intent"] == "stations":
        cur.execute("SELECT station_name FROM stations ORDER BY station_name")
        rows = cur.fetchall()
        return {"type":"table","headers":["Station Name"],"rows":[[r[0]] for r in rows]}
    return {"type":"text","text":f"Oracle handler not implemented for '{cmd['intent']}'"}

# ---------------- ADMIN PANEL WRITE FUNCTIONS (FIXED) ----------------

def add_or_update_station(station_id, name, latitude, longitude):
    if db is None: return False
    try:
        # CRITICAL FIX: Convert latitude and longitude to float to prevent 400 BAD REQUEST from ValueError
        lat_float = float(latitude)
        lon_float = float(longitude)
        
        db.stations.update_one(
            {"station_id": station_id},
            {"$set": {"station_name": name, "latitude": lat_float, "longitude": lon_float}},
            upsert=True
        )
        return True
    except ValueError:
        print(f"⚠️ Data Type Error: Could not convert latitude/longitude ({latitude}, {longitude}) to float.")
        return False
    except Exception as e:
        print(f"⚠️ MongoDB Error in station update: {e}")
        return False

def add_or_update_bus(route_no, license_plate, current_latitude, current_longitude):
    if db is None: return False
    try:
        # NOTE: Using 'route_no' (integer) as the main key for buses
        # CRITICAL FIX: Convert route_no to integer
        route_no_int = int(route_no)
        
        db.buses.update_one(
            {"route_no": route_no_int},
            {"$set": {
                "license_plate": license_plate, 
                # Keeping lat/lon as strings here as they may be updated frequently, 
                # but they must be valid numbers for the client-side/query functions to work.
                "current_latitude": str(current_latitude), 
                "current_longitude": str(current_longitude), 
                "timestamp": datetime.now().isoformat()
            }},
            upsert=True
        )
        return True
    except ValueError:
        print(f"⚠️ Data Type Error: Could not convert route_no ({route_no}) to integer.")
        return False
    except Exception as e:
        print(f"⚠️ MongoDB Error in bus update: {e}")
        return False

def add_or_update_schedule(bus_id, source_station_id, dest_station_id, departure_time, arrival_time):
    if db is None: return False
    try:
        # CRITICAL FIX: Convert bus_id to integer to match 'buses' collection data type
        bus_id_int = int(bus_id)

        db.schedule.update_one(
            # Search by converted integer ID
            {"bus_id": bus_id_int, "source_station_id": source_station_id, "dest_station_id": dest_station_id},
            {"$set": {
                "departure_time": departure_time, 
                "arrival_time": arrival_time
            }},
            upsert=True
        )
        return True
    except ValueError:
        print(f"⚠️ Data Type Error: Could not convert bus_id ({bus_id}) to integer.")
        return False
    except Exception as e:
        print(f"⚠️ MongoDB Error in schedule update: {e}")
        return False

def add_or_update_fare(source, destination, amount):
    """
    Add or update fare details between two stations.
    Always ensures that source, destination, and amount are stored properly.
    """
    if db is None:
        print("⚠️ Database connection not available.")
        return False

    try:
        amount_float = float(amount)

        # Fare record update or insert (both source & destination included)
        db.fare.update_one(
            {
                "$or": [
                    {"source": source, "destination": destination},
                    {"source": destination, "destination": source}
                ]
            },
            {
                "$set": {
                    "source": source,
                    "destination": destination,
                    "amount": amount_float
                }
            },
            upsert=True
        )

        print(f"✅ Fare updated: {source} → {destination} = ₹{amount_float}")
        return True

    except ValueError:
        print(f"⚠️ Invalid amount: {amount} (must be numeric)")
        return False
    except Exception as e:
        print(f"⚠️ MongoDB Error in add_or_update_fare(): {e}")
        return False

# ----------------- GET RECORD FUNCTIONS -----------------
def get_station_by_id(station_id):
    """Finds a station record by its ID from MongoDB."""
    if db is None: return None
    return db.stations.find_one({"station_id": station_id}, {'_id': 0})

def get_bus_by_id(bus_id):
    """Finds a bus record by its ID from MongoDB. Uses confirmed key 'route_no'."""
    if db is None: return None
    try:
        bus_id_int = int(bus_id)
    except (ValueError, TypeError):
        return None
        
    return db.buses.find_one({"route_no": bus_id_int}, {'_id': 0})

def get_schedule_by_bus_id(bus_id):
    """Finds a schedule record by its bus ID from MongoDB."""
    if db is None: return None
    # Assuming bus_id is stored as an integer in schedule collection
    try:
        bus_id_int = int(bus_id)
    except (ValueError, TypeError):
        return None
        
    return db.schedule.find_one({"bus_id": bus_id_int}, {'_id': 0})

def get_all_stations():
    """Gets all stations from MongoDB."""
    if db is None: return {"headers": ["station_id", "station_name", "latitude", "longitude"], "rows": []}
    stations = list(db.stations.find({}, {'_id': 0}))
    if not stations: return {"headers": ["station_id", "station_name", "latitude", "longitude"], "rows": []}
    # Ensure consistent order and inclusion of keys
    headers = ["station_id", "station_name", "latitude", "longitude"]
    rows = [[s.get(h, '') for h in headers] for s in stations]
    return {"headers": headers, "rows": rows}

def get_all_buses():
    """Gets all buses from MongoDB. Uses confirmed keys."""
    headers = ["route_no", "license_plate", "current_latitude", "current_longitude", "timestamp"]
    if db is None: return {"headers": headers, "rows": []}
    buses = list(db.buses.find({}, {'_id': 0}))
    if not buses: return {"headers": headers, "rows": []}
    
    rows = []
    for b in buses:
        rows.append([
            b.get('route_no', ''), 
            b.get('license_plate', ''), # Assuming 'license_plate' exists or is added by admin
            b.get('current_latitude', ''), 
            b.get('current_longitude', ''), 
            b.get('timestamp', '')
        ])
        
    return {"headers": headers, "rows": rows}

def get_all_schedules():
    """Gets all schedules from MongoDB."""
    if db is None: return {"headers": ["bus_id", "source_station_id", "dest_station_id", "departure_time", "arrival_time"], "rows": []}
    schedules = list(db.schedule.find({}, {'_id': 0}))
    if not schedules: return {"headers": ["bus_id", "source_station_id", "dest_station_id", "departure_time", "arrival_time"], "rows": []}
    
    headers = ["bus_id", "source_station_id", "dest_station_id", "departure_time", "arrival_time"]
    rows = [[s.get(h, '') for h in headers] for s in schedules]
    return {"headers": headers, "rows": rows}

def get_all_fares():
    """Gets all fares from MongoDB."""
    if db is None: return {"headers": ["source", "destination", "amount"], "rows": []}
    fares = list(db.fare.find({}, {'_id': 0}))
    if not fares: return {"headers": ["source", "destination", "amount"], "rows": []}
    
    headers = ["source", "destination", "amount"]
    rows = [[f.get(h, '') for h in headers] for f in fares]
    return {"headers": headers, "rows": rows}

# ---------------- Logging ----------------
def log_query_to_csv(query, response):
    """Save queries + responses in a local CSV for debugging."""
    log_dir = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logfile = os.path.join(log_dir, "query_logs.csv")
    write_header = not os.path.exists(logfile)

    with open(logfile, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "query", "response"])
        writer.writerow([datetime.now().isoformat(), query, str(response)])