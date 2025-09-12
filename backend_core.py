import os
import csv
import random
import re
from datetime import datetime

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

        # Route queries
        ("show all routes", "route_query"),
        ("show routes", "route_query"),
        ("list routes", "route_query"),
        ("route 101 details", "route_query"),
        ("tell me about bus 202", "route_query"),
        ("bus 303 schedule", "route_query"),
        ("route one zero one details", "route_query"),
        ("tell me the route for bus", "route_query"),
        
        # Next bus queries
        ("next bus from andheri to borivali", "next_bus_query"),
        ("is there a bus from bandra to dadar", "next_bus_query"),
        ("when is the next bus from virar to churchgate", "next_bus_query"),
        ("what bus can i take from dadar to andheri", "next_bus_query"),

        # Fare queries
        ("fare from bandra to dadar", "fare_query"),
        ("ticket price from cst to andheri", "fare_query"),
        ("how much is fare between andheri and borivali", "fare_query"),
        ("how much is the ticket from dadar to virar", "fare_query"),
        ("cost from borivali to andheri", "fare_query"),
        ("what is the fare from", "fare_query"),
        ("price of a ticket from", "fare_query"),

        # Track queries
        ("track bus 101", "track_query"),
        ("where is bus 202", "track_query"),
        ("bus 404 location", "track_query"),
        ("where is bus one zero one", "track_query"),
        ("track bus two zero two", "track_query"),
        ("where is bus 404", "track_query"),
        
        # Recommend queries
        ("recommend me a route", "recommend_query"),
        ("best route from bandra to cst", "recommend_query"),
        ("suggest a route from dadar to andheri", "recommend_query"),
        ("recommend a route from", "recommend_query"),
        ("suggest a route for me", "recommend_query"),

        # Admin CRUD queries
        ("add a station", "admin_add_station"),
        ("update a bus", "admin_update_bus"),
        ("add new schedule", "admin_add_schedule"),
        ("update bus route 101", "admin_update_schedule")
    ]

    texts, labels = zip(*training_data)
    intent_vectorizer = TfidfVectorizer()
    X = intent_vectorizer.fit_transform(texts)

    intent_model = LogisticRegression()
    intent_model.fit(X, labels)
    print("✅ Intent classifier trained with", len(training_data), "examples.")

def predict_intent(query: str):
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
        # The station query doesn't need parameters
        pass
    elif intent == "route_query" or intent == "track_query":
        # Check for specific bus numbers, handling both digits and spelled-out numbers
        match = re.search(r"(?:bus|route)\s+(\d+|one zero one|two oh two|two zero two)", query)
        if match:
            raw_bus_number = match.group(1)
            # Normalize the number if it's in text format
            bus_number = _text_to_num(raw_bus_number) if not raw_bus_number.isdigit() else raw_bus_number
            parsed_cmd["params"]["bus_number"] = bus_number
    elif intent in ["next_bus_query", "fare_query", "recommend_query"]:
        # Extract source and destination stations using regex
        match = re.search(r"from (\w+)\s+to (\w+)", query)
        if match:
            parsed_cmd["params"]["source"] = match.group(1).title()
            parsed_cmd["params"]["destination"] = match.group(2).title()
    else:
        parsed_cmd["intent"] = "unknown"

    return parsed_cmd

# ---------------- DB & Mock Handlers ----------------
def get_connection():
    """Return Oracle DB connection (if available)."""
    if cx_Oracle is None:
        return None
    try:
        dsn = cx_Oracle.makedsn("localhost", 1521, service_name="XE")
        conn = cx_Oracle.connect(user="system", password="oracle", dsn=dsn)
        return conn
    except Exception as e:
        print("⚠️ Oracle connection failed:", e)
        return None

def handle_command_core(cmd: dict, mode="mock", conn=None):
    """Main query handler (mock or Oracle)"""
    if mode == "oracle" and conn:
        return _handle_with_oracle(conn, cmd)
    return _handle_with_mock(cmd)

# ---------------- MOCK MODE ----------------
def _handle_with_mock(cmd: dict):
    intent = cmd["intent"]
    params = cmd["params"]

    # Load station names mapping
    station_map = {}
    try:
        with open(os.path.join(MOCK_DIR, "stations.csv")) as f:
            reader = csv.DictReader(f)
            for r in reader:
                station_map[r["station_id"]] = r["station_name"]
    except FileNotFoundError:
        return {"type":"text","text":"Mock data files not found. Please check the 'mock_data' folder."}


    if intent == "station_query":
        with open(os.path.join(MOCK_DIR, "stations.csv")) as f:
            reader = csv.DictReader(f)
            rows = [[r["station_name"]] for r in reader]
        return {"type":"table","headers":["Station Name"],"rows":rows}

    if intent == "route_query":
        bus_number = params.get("bus_number")
        if not bus_number:
            with open(os.path.join(MOCK_DIR, "schedule.csv")) as f:
                reader = csv.DictReader(f)
                # Correctly map station IDs to names
                rows = [
                    [r["bus_id"], station_map.get(r["source_station_id"], "Unknown"), 
                    station_map.get(r["dest_station_id"], "Unknown"), r["departure_time"], r["arrival_time"]] 
                    for r in reader
                ]
            return {"type":"table","headers":["Bus","Source","Dest","Departure","Arrival"],"rows":rows}
        else:
            found_route = False
            details_rows = []
            with open(os.path.join(MOCK_DIR, "schedule.csv")) as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r["bus_id"] == bus_number:
                        source_name = station_map.get(r["source_station_id"], "Unknown")
                        dest_name = station_map.get(r["dest_station_id"], "Unknown")
                        details_rows.append([r["bus_id"], source_name, dest_name, r["departure_time"], r["arrival_time"]])
                        found_route = True
            
            if found_route:
                return {"type": "table", "headers": ["Bus", "Source", "Dest", "Departure", "Arrival"], "rows": details_rows}
            else:
                return {"type": "text", "text": f"Details for Bus {bus_number} not found in mock data."}

    if intent == "next_bus_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            return {"type":"text","text":f"The next bus from {src} to {dst} is Bus 101, arriving in 15 minutes."}
        return {"type":"text","text":"I couldn't find a bus for that route."}

    if intent == "fare_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            found_fare = None
            with open(os.path.join(MOCK_DIR, "fare.csv")) as f:
                reader = csv.DictReader(f)
                for r in reader:
                    # Check for fare in both directions
                    if (r["source"] == src and r["destination"] == dst) or \
                       (r["source"] == dst and r["destination"] == src):
                        found_fare = r["amount"]
                        break # Exit the loop once a match is found
            if found_fare:
                return {"type":"text","text":f"The fare from {src} to {dst} is ₹{found_fare}"}
            else:
                return {"type":"text","text":f"Fare not found for route from {src} to {dst}."}
        return {"type":"text","text":"Fare not found."}

    if intent == "track_query":
        bus_no = params.get("bus_number")
        if bus_no:
            with open(os.path.join(MOCK_DIR, "buses.csv")) as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r["route_no"] == bus_no:
                        url = f"https://maps.google.com/?q={r['current_latitude']},{r['current_longitude']}"
                        return {"type":"map","url":url}
        return {"type":"text","text":f"Bus {bus_no or ''} not found."}

    if intent == "recommend_query":
        src = params.get("source")
        dst = params.get("destination")
        if src and dst:
            options = [f"Take Bus 101 from {src} to {dst}", f"Try Bus 202 from {src} to {dst}"]
            return {"type":"text","text":random.choice(options)}
        else:
            options = ["Take Bus 101 from Andheri to Borivali", "Take Bus 202 from Bandra to Dadar"]
            return {"type":"text","text":random.choice(options)}

    return {"type":"text","text":f"Sorry, I couldn't understand your request."}

# ---------------- ORACLE MODE (skeleton) ----------------
def _handle_with_oracle(conn, cmd):
    cur = conn.cursor()
    if cmd["intent"] == "stations":
        cur.execute("SELECT station_name FROM stations ORDER BY station_name")
        rows = cur.fetchall()
        return {"type":"table","headers":["Station Name"],"rows":[[r[0]] for r in rows]}
    return {"type":"text","text":f"Oracle handler not implemented for '{cmd['intent']}'"}

# ---------------- ADMIN PANEL WRITE FUNCTIONS ----------------
def _add_or_update_record(filepath, record, key_field):
    """
    Adds or updates a record in a CSV file.
    Args:
        filepath (str): Path to the CSV file.
        record (dict): A dictionary representing the new or updated record.
        key_field (str): The column name to use as the unique key.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        data = []
        file_exists = os.path.exists(filepath)
        if file_exists:
            with open(filepath, 'r', newline='') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row[key_field] == record[key_field]:
                        # Update the existing record
                        row.update(record)
                        data.append(row)
                    else:
                        data.append(row)
            # If the record was not found, add it
            if not any(r[key_field] == record[key_field] for r in data):
                data.append(record)
        else:
            # If the file doesn't exist, start with the new record
            fieldnames = list(record.keys())
            data.append(record)

        # Write the updated data back to the file
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return True
    except Exception as e:
        print(f"Error updating CSV file: {e}")
        return False

def add_or_update_station(station_id, station_name):
    """Adds or updates a station record in stations.csv."""
    record = {"station_id": station_id, "station_name": station_name}
    filepath = os.path.join(MOCK_DIR, "stations.csv")
    return _add_or_update_record(filepath, record, "station_id")

def add_or_update_bus(bus_id, lat, lon):
    """Adds or updates a bus record in buses.csv."""
    record = {"route_no": bus_id, "current_latitude": lat, "current_longitude": lon, "timestamp": datetime.now().isoformat()}
    filepath = os.path.join(MOCK_DIR, "buses.csv")
    return _add_or_update_record(filepath, record, "route_no")

def add_or_update_schedule(bus_id, source_id, dest_id, dep_time, arr_time):
    """Adds or updates a schedule record in schedule.csv."""
    record = {"bus_id": bus_id, "source_station_id": source_id, "dest_station_id": dest_id, "departure_time": dep_time, "arrival_time": arr_time}
    filepath = os.path.join(MOCK_DIR, "schedule.csv")
    # Using a composite key for schedule to identify unique routes
    return _add_or_update_record(filepath, record, "bus_id")


# ----------------- NEW GET RECORD FUNCTIONS -----------------
def get_station_by_id(station_id):
    """Finds a station record by its ID."""
    filepath = os.path.join(MOCK_DIR, "stations.csv")
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['station_id'] == station_id:
                return row
    return None

def get_bus_by_id(bus_id):
    """Finds a bus record by its ID."""
    filepath = os.path.join(MOCK_DIR, "buses.csv")
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['route_no'] == bus_id:
                return row
    return None

def get_schedule_by_bus_id(bus_id):
    """Finds a schedule record by its bus ID."""
    filepath = os.path.join(MOCK_DIR, "schedule.csv")
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['bus_id'] == bus_id:
                return row
    return None

# NEW: Functions to get all records from CSV files
def get_all_records(filepath):
    """Reads all records from a CSV file."""
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = [list(row.values()) for row in reader]
            return {"headers": headers, "rows": rows}
    except FileNotFoundError:
        return {"headers": [], "rows": []}

def get_all_stations():
    """Gets all stations."""
    return get_all_records(os.path.join(MOCK_DIR, "stations.csv"))

def get_all_buses():
    """Gets all buses."""
    return get_all_records(os.path.join(MOCK_DIR, "buses.csv"))

def get_all_schedules():
    """Gets all schedules."""
    return get_all_records(os.path.join(MOCK_DIR, "schedule.csv"))


# ---------------- Logging ----------------
def log_query_to_csv(query, response):
    """Save queries + responses in a local CSV for debugging."""
    logfile = os.path.join(BASE_DIR, "query_logs.csv")
    write_header = not os.path.exists(logfile)

    with open(logfile, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["query", "response"])
        writer.writerow([query, str(response)])