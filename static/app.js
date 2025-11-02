const ADMIN_PASSWORD = "admin";

// Helper: show/hide modal
function showModal(id) { document.getElementById(id).classList.add("show"); }
function closeModal(id) { document.getElementById(id).classList.remove("show"); }

document.querySelectorAll(".close-btn").forEach(btn => {
  btn.addEventListener("click", e => closeModal(e.target.closest(".modal").id));
});
document.querySelectorAll(".modal").forEach(modal => {
  modal.addEventListener("click", e => { if (e.target.classList.contains("modal")) closeModal(modal.id); });
});

// Buttons → Open Modals
document.getElementById("track-btn").onclick = () => showModal("track-modal");
document.getElementById("fare-btn").onclick = () => showModal("fare-modal");
document.getElementById("admin-btn").onclick = () => showModal("admin-modal");

// NEW BUTTON HANDLER: All Routes
document.getElementById("all-routes-btn").onclick = () => postQuery('show all routes');

// Admin Panel login
document.getElementById("admin-login").onclick = () => {
  const pass = document.getElementById("admin-pass").value;
  if (pass === ADMIN_PASSWORD) {
    closeModal("admin-modal");
    document.getElementById("admin-panel").classList.add("open");
  } else {
    alert("Wrong password!");
  }
};
document.querySelector(".admin-close-btn").onclick = () => {
  document.getElementById("admin-panel").classList.remove("open");
  document.getElementById("admin-pass").value = ""; // Clear the password field
};

// --- API Calls ---

async function postQuery(q) {
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Processing...";
  // Hide fullscreen button at the start of a new query
  document.getElementById("fullscreen-map-btn").classList.add("hidden");
  
  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: q }),
    });
    const res = await response.json();
    if (res.status === "ok") {
      renderResult(res.result);
    } else {
      renderResult({ type: "text", text: `Error: ${res.message}` });
    }
  } catch (error) {
    console.error("Query Error:", error);
    renderResult({ type: "text", text: "A network error occurred. Please check the server." });
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit";
  }
}

// --- Submit Handlers ---

document.getElementById("submit-btn").onclick = () => {
  const query = document.getElementById("query-input").value;
  if (query) {
    postQuery(query);
  }
};

document.getElementById("track-submit").onclick = () => {
  const busNo = document.getElementById("track-input").value;
  if (busNo) {
    postQuery(`track bus ${busNo}`);
    closeModal("track-modal");
  }
};

document.getElementById("fare-submit").onclick = () => {
  const src = document.getElementById("fare-src").value;
  const dest = document.getElementById("fare-dest").value;
  if (src && dest) {
    postQuery(`fare from ${src} to ${dest}`);
    closeModal("fare-modal");
  }
};

// --- Mute Toggle ---
let isMuted = false;
let lastSpokenText = "";

document.getElementById("mute-btn").onclick = function() {
  isMuted = !isMuted;
  this.textContent = isMuted ? "🔊 Unmute" : "🔇 Mute";
  if (isMuted) {
    window.speechSynthesis.cancel();
  } else if (lastSpokenText) {
    speak(lastSpokenText); // Re-speak the last message if unmuting
  }
};

// --- Render Results ---
function renderResult(res) {
  const resultDiv = document.getElementById("result");
  const fullscreenBtn = document.getElementById("fullscreen-map-btn");
  
  // Always clear the previous content, especially the map
  resultDiv.innerHTML = ""; 
  // Re-add the button placeholder and hide it
  resultDiv.appendChild(fullscreenBtn);
  fullscreenBtn.classList.add("hidden"); 

  // Add the text response first
  resultDiv.innerHTML += `<p class="mb-3">${res.text}</p>`;

  if (res.type === "text") {
    lastSpokenText = res.text; // Ensure lastSpokenText is set for text-only responses
  } else if (res.type === "table") {
    // Generate Table HTML
    const headers = res.headers; // Fixed: Accessing headers directly from res object
    const rows = res.rows;       // Fixed: Accessing rows directly from res object
    let tableHtml = '<div class="overflow-x-auto"><table class="w-full text-sm data-table">';
    
    // Table Headers
    tableHtml += '<thead class="bg-gray-200"><tr>';
    headers.forEach(h => { tableHtml += `<th class="p-3">${h}</th>`; });
    tableHtml += '</tr></thead>';
    
    // Table Rows
    tableHtml += '<tbody>';
    rows.forEach(r => {
      tableHtml += '<tr class="border-b hover:bg-gray-100">';
      r.forEach(d => { tableHtml += `<td class="p-3">${d}</td>`; });
      tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table></div>';
    
    resultDiv.innerHTML += tableHtml;

    // --- NEW UPDATED Spoken Text Logic for Tables ---
    let spokenText = res.text + ". ";
    if (rows.length > 0) {
        // Normalize headers to lowercase for easier checking
        const normalizedHeaders = headers.map(h => h.toLowerCase().replace(/_/g, ' '));
        
        // Find the indices for key data points
        const busIdx = normalizedHeaders.findIndex(h => h.includes('bus') || h.includes('route'));
        const nameIdx = normalizedHeaders.findIndex(h => h.includes('name') || h.includes('station'));
        const depIdx = normalizedHeaders.findIndex(h => h.includes('departure'));
        const arrIdx = normalizedHeaders.findIndex(h => h.includes('arrival')); // NEW: Arrival Index
        const amountIdx = normalizedHeaders.findIndex(h => h.includes('amount') || h.includes('fare'));

        
        if (depIdx !== -1 && busIdx !== -1) {
            // Case 1: Route Schedule (All Routes/Specific Route)
            spokenText += "Here are the details for all routes: ";
            rows.forEach(row => {
                const bus = row[busIdx] || 'N/A';
                const source = row[normalizedHeaders.findIndex(h => h.includes('source'))] || 'Source N/A';
                const dest = row[normalizedHeaders.findIndex(h => h.includes('dest'))] || 'Destination N/A';
                const departure = row[depIdx] || 'Time N/A';
                const arrival = arrIdx !== -1 ? (row[arrIdx] || 'Time N/A') : ''; // Use arrival index if found
                
                let routeText = `Bus ${bus} from ${source} to ${dest} departs at ${departure}`;
                if (arrival) {
                    routeText += ` and arrives at ${arrival}. `;
                } else {
                    routeText += ". ";
                }
                spokenText += routeText;
            });
        } else if (nameIdx !== -1 && headers.length === 1) {
            // Case 2: All Stations List (Single column: Station Name)
            // Speak ALL station names
            const stationNames = rows.map(r => r[nameIdx]).join(', ');
            spokenText += `The stations are: ${stationNames}.`;
        } else if (amountIdx !== -1) {
             // Case 3: Fare Query
             const srcIdx = normalizedHeaders.findIndex(h => h.includes('source'));
             const destIdx = normalizedHeaders.findIndex(h => h.includes('destination'));
             
             if (srcIdx !== -1 && destIdx !== -1) {
                 // For fare, we assume only one result is relevant for a specific query
                 const firstRow = rows[0];
                 spokenText += `The fare from ${firstRow[srcIdx]} to ${firstRow[destIdx]} is ${firstRow[amountIdx]} rupees.`;
             }
        }
    }
    lastSpokenText = spokenText;
    // --- END NEW UPDATED Spoken Text Logic ---

  } else if (res.type === "map_route") { // NEW: Handle the map_route type
    renderMapRoute(res.data, resultDiv);
    lastSpokenText = res.text; // Use the descriptive text from the backend
  } else if (res.type === "map") {
    // Legacy Google Maps logic - keeping for compatibility, though map_route is the new standard
    // If you remove this, ensure you remove 'GOOGLE_MAPS_API_KEY' from backend_core.py as well
    const mapContainer = document.createElement("div");
    mapContainer.id = "result-map-container";
    mapContainer.classList.add("w-full", "h-[400px]", "rounded-2xl");
    resultDiv.appendChild(mapContainer);

    const data = res.data.data;
    const map = new google.maps.Map(mapContainer, {
      center: data.center,
      zoom: 15,
      mapId: "DEMO_MAP_ID"
    });
    new google.maps.Marker({
        position: data.location,
        map: map,
        title: "Bus Location",
    });
    lastSpokenText = res.text;
  }
  
  // Speak the final text
  speak(lastSpokenText);
}


// --- NEW: Leaflet Map Rendering Function ---
let currentMap = null; // Variable to hold the map instance
let currentMapData = null; // **NEW:** Variable to hold map data for fullscreen view

/**
 * Renders the Leaflet map with Source, Bus, and Destination markers, 
 * and a polyline connecting them.
 * @param {object} mapData - Contains source, bus, destination, and center coordinates.
 * @param {HTMLElement} targetDiv - The container element to append the map to.
 */
function renderMapRoute(mapData, targetDiv) {
    currentMapData = mapData; // **NEW:** Store data for fullscreen view

    // 1. Clear previous map instance if it exists
    if (currentMap) {
        currentMap.remove();
        currentMap = null;
    }
    
    // 2. Setup map container
    const mapId = "leaflet-map-container";
    const mapContainer = document.createElement("div");
    mapContainer.id = mapId;
    mapContainer.classList.add("w-full", "h-[400px]", "rounded-xl", "shadow-lg", "mt-4");
    targetDiv.appendChild(mapContainer);
    
    // 3. Initialize Leaflet Map
    const centerCoords = [mapData.center.lat, mapData.center.lon];
    const map = L.map(mapId).setView(centerCoords, 14);
    currentMap = map;

    // 4. Add Tile Layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 5. Define Icon URLs (Using Leaflet default colored markers)
    // Leaflet does not have built-in colored markers, so we use a popular CDN set.
    const ICON_BASE_URL = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-';
    const SHADOW_URL = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png';
    const ICON_SETTINGS = {
        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
    };
    
    // Ensure SHADOW_URL is correct if not using a specific CDN
    // The previous code had a slight error in SHADOW_URL, fixing it here to be reliable.
    
    const redIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'red.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS }); // Destination
    const greenIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'green.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS }); // Source
    const blueIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'blue.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS }); // Bus (Live)

    // 6. Add Markers
    const sourceMarker = L.marker([mapData.source.lat, mapData.source.lon], {icon: greenIcon}).addTo(map)
        .bindPopup(`<b>Source:</b> ${mapData.source.label}`);
        
    const destMarker = L.marker([mapData.destination.lat, mapData.destination.lon], {icon: redIcon}).addTo(map)
        .bindPopup(`<b>Destination:</b> ${mapData.destination.label}`);

    const busMarker = L.marker([mapData.bus.lat, mapData.bus.lon], {icon: blueIcon}).addTo(map)
        .bindPopup(`<b>Bus Location:</b> ${mapData.bus.label}`).openPopup();
        
    // 7. Add Polyline (A simple route connecting the three points in order)
    const routeCoordinates = [
        [mapData.source.lat, mapData.source.lon],
        [mapData.bus.lat, mapData.bus.lon],
        [mapData.destination.lat, mapData.destination.lon]
    ];

    L.polyline(routeCoordinates, {color: '#6366f1', weight: 5, opacity: 0.8}).addTo(map); // Indigo color for the route
    
    // 8. Adjust map view to fit all markers
    const bounds = L.latLngBounds(routeCoordinates);
    map.fitBounds(bounds, {padding: [50, 50]});
    
    // **NEW:** Show the fullscreen button and attach handler
    document.getElementById("fullscreen-map-btn").classList.remove("hidden");
    document.getElementById("fullscreen-map-btn").onclick = () => openFullscreenMap(currentMapData);
}


// **NEW:** Fullscreen map function
function openFullscreenMap(mapData) {
    if (!mapData) return;

    // Stringify the data for injection into the new window's HTML
    const mapDataString = JSON.stringify(mapData);
    
    // HTML content for the new window
    const newWindowContent = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TransitMate - Fullscreen Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
            <style>
                body { margin: 0; padding: 0; background: #f0f4ff; }
                #fullscreen-map { height: 100vh; width: 100vw; }
                .leaflet-top.leaflet-left { z-index: 1000 !important; } /* Ensure controls are visible */
            </style>
        </head>
        <body>
            <div id="fullscreen-map"></div>
            <script>
                const mapData = ${mapDataString};
                
                function initFullscreenMap() {
                    const centerCoords = [mapData.center.lat, mapData.center.lon];
                    const map = L.map('fullscreen-map').setView(centerCoords, 14);

                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    }).addTo(map);
                    
                    const ICON_BASE_URL = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-';
                    const SHADOW_URL = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png';
                    const ICON_SETTINGS = {
                        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
                    };

                    const redIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'red.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS });
                    const greenIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'green.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS });
                    const blueIcon = new L.Icon({ iconUrl: ICON_BASE_URL + 'blue.png', shadowUrl: SHADOW_URL, ...ICON_SETTINGS });

                    const sourceMarker = L.marker([mapData.source.lat, mapData.source.lon], {icon: greenIcon}).addTo(map)
                        .bindPopup(\`<b>Source:</b> \${mapData.source.label}\`);
                        
                    const destMarker = L.marker([mapData.destination.lat, mapData.destination.lon], {icon: redIcon}).addTo(map)
                        .bindPopup(\`<b>Destination:</b> \${mapData.destination.label}\`);

                    const busMarker = L.marker([mapData.bus.lat, mapData.bus.lon], {icon: blueIcon}).addTo(map)
                        .bindPopup(\`<b>Bus Location:</b> \${mapData.bus.label}\`).openPopup();
                        
                    const routeCoordinates = [
                        [mapData.source.lat, mapData.source.lon],
                        [mapData.bus.lat, mapData.bus.lon],
                        [mapData.destination.lat, mapData.destination.lon]
                    ];

                    L.polyline(routeCoordinates, {color: '#6366f1', weight: 5, opacity: 0.8}).addTo(map);
                    
                    const bounds = L.latLngBounds(routeCoordinates);
                    map.fitBounds(bounds, {padding: [50, 50]});
                    
                    // Force map resize after a small delay to ensure it renders correctly on a new tab
                    setTimeout(() => {
                        map.invalidateSize();
                    }, 100);
                }

                // Run the map initialization when the window loads
                window.onload = initFullscreenMap;
            </script>
        </body>
        </html>
    `;

    // Open the new window and write the content
    const newWindow = window.open();
    newWindow.document.write(newWindowContent);
    newWindow.document.close();
}


// --- Voice Output (Text-to-Speech) ---
function speak(text) {
// ... (rest of the speak function is unchanged)
  if (isMuted) {
    return;
  }
  if ("speechSynthesis" in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  } else {
    console.warn("Text-to-speech not supported!");
  }
}


// --- Voice Recognition ---
function startVoiceInput(callback) {
// ... (rest of the startVoiceInput function is unchanged)
  if (!("webkitSpeechRecognition" in window)) {
    alert("Speech recognition not supported!");
    return;
  }
  const recognition = new webkitSpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.onresult = e => callback(e.results[0][0].transcript);
  recognition.start();
}

document.getElementById("voice-btn").onclick = () => {
    startVoiceInput(transcript => {
        document.getElementById("query-input").value = transcript;
        postQuery(transcript);
    });
};

// --- Admin CRUD Panel Logic ---

async function adminApiCall(endpoint, method = 'GET', data = null) {
// ... (rest of the adminApiCall function is unchanged)
    const statusMsg = document.getElementById("admin-status-msg");
    statusMsg.textContent = "Loading...";
    try {
        const options = { method: method };
        if (data) {
            options.headers = { "Content-Type": "application/json" };
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        const res = await response.json();
        
        if (res.status === "ok") {
            statusMsg.textContent = "Success!";
            statusMsg.classList.remove("text-red-500", "text-blue-500");
            statusMsg.classList.add("text-green-500");
            setTimeout(() => statusMsg.textContent = "", 3000);
            return res;
        } else {
            statusMsg.textContent = `Error: ${res.message}`;
            statusMsg.classList.remove("text-green-500", "text-blue-500");
            statusMsg.classList.add("text-red-500");
            return null;
        }
    } catch (error) {
        statusMsg.textContent = `Network Error: ${error.message}`;
        statusMsg.classList.remove("text-green-500", "text-blue-500");
        statusMsg.classList.add("text-red-500");
        return null;
    }
}

function renderAdminTable(data, type) {
// ... (rest of the renderAdminTable function is unchanged)
    const viewDiv = document.getElementById("admin-data-view");
    viewDiv.innerHTML = "";
    
    if (data.rows.length === 0) {
        viewDiv.innerHTML = `<p class="text-sm text-gray-400 italic">No ${type} records found.</p>`;
        return;
    }

    const headers = data.headers;
    const rows = data.rows;
    
    let tableHtml = '<table class="w-full text-sm data-table relative">';
    
    // Headers
    tableHtml += '<thead class="bg-gray-200"><tr>';
    headers.forEach(h => { tableHtml += `<th class="p-2">${h}</th>`; });
    tableHtml += `<th class="p-2">Action</th>`; // Edit column
    tableHtml += '</tr></thead>';
    
    // Rows
    tableHtml += '<tbody>';
    rows.forEach((r, index) => {
        tableHtml += `<tr class="border-b hover:bg-gray-100" data-row-index="${index}">`;
        r.forEach(d => { tableHtml += `<td class="p-2">${d}</td>`; });
        tableHtml += `<td class="p-2"><button class="text-indigo-600 hover:text-indigo-800 edit-row-btn" data-row-index="${index}">Edit</button></td>`;
        tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';
    
    viewDiv.innerHTML = tableHtml;

    // Attach event listeners for edit buttons
    const rowElements = viewDiv.querySelectorAll('.edit-row-btn');
    const rowDataArray = rows.map(r => r.reduce((obj, value, i) => {
        obj[headers[i]] = value;
        return obj;
    }, {}));
    
    setupEditButtons(type, rowDataArray, headers);
}

function setupEditButtons(type, rows, headers) {
// ... (rest of the setupEditButtons function is unchanged)
  const rowElements = document.getElementById("admin-data-view").querySelectorAll('.edit-row-btn');
  rowElements.forEach(btn => {
    btn.addEventListener('click', () => {
        const rowIndex = btn.dataset.rowIndex;
        const rowData = rows[rowIndex];
        fillAdminFormFromRow(type, rowData, headers);
    });
  });
}

function fillAdminFormFromRow(type, rowData, headers) {
// ... (rest of the fillAdminFormFromRow function is unchanged)
    // Helper to map generic header names to form element IDs
    const mappings = {
        'stations': { 'station_id': 'sta-id', 'station_name': 'sta-name', 'latitude': 'sta-lat', 'longitude': 'sta-lon' },
        'buses': { 'route_no': 'bus-id', 'license_plate': 'bus-license', 'current_latitude': 'bus-lat', 'current_longitude': 'bus-lon' },
        'schedules': { 'bus_id': 'sch-bus-id', 'source_station_id': 'sch-src', 'dest_station_id': 'sch-dest', 'departure_time': 'sch-dep', 'arrival_time': 'sch-arr' },
        'fares': { 'source': 'fare-admin-src', 'destination': 'fare-admin-dest', 'amount': 'fare-admin-amount' }
    };

    if (!mappings[type]) return;

    // Clear previous form data
    Object.values(mappings[type]).forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    // Populate the form
    headers.forEach(header => {
        const id = mappings[type][header];
        if (id) {
            const el = document.getElementById(id);
            if (el) el.value = rowData[header];
        }
    });

    document.getElementById("admin-status-msg").textContent = `Form loaded for ${type} ID: ${rowData[headers[0]]}`;
    document.getElementById("admin-status-msg").classList.remove("text-red-500");
    document.getElementById("admin-status-msg").classList.add("text-blue-500");
}

async function showAllStations() {
// ... (rest of the showAllStations function is unchanged)
    const res = await adminApiCall("/api/admin/get_all_stations");
    if (res) renderAdminTable(res.result, 'stations');
}

async function showAllBuses() {
// ... (rest of the showAllBuses function is unchanged)
    const res = await adminApiCall("/api/admin/get_all_buses");
    if (res) renderAdminTable(res.result, 'buses');
}

async function showAllSchedules() {
// ... (rest of the showAllSchedules function is unchanged)
    const res = await adminApiCall("/api/admin/get_all_schedules");
    if (res) renderAdminTable(res.result, 'schedules');
}

async function showAllFares() {
// ... (rest of the showAllFares function is unchanged)
    const res = await adminApiCall("/api/admin/get_all_fares");
    if (res) renderAdminTable(res.result, 'fares');
}


// --- Admin Panel Listeners ---

// Station CRUD
document.getElementById("add-sta").onclick = async () => {
// ... (rest of the Station CRUD listener is unchanged)
    const data = {
        station_id: document.getElementById("sta-id").value,
name: document.getElementById("sta-name").value,
        latitude: document.getElementById("sta-lat").value,
        longitude: document.getElementById("sta-lon").value
    };
console.log (data);
    // Basic validation check
    if (data.station_id && data.name && data.latitude && data.longitude) { 
        const res = await adminApiCall("/api/admin/station", "POST", data);
        if (res) showAllStations();
    } else {
        document.getElementById("admin-status-msg").textContent = "Please fill all Station fields to add/update.";
        document.getElementById("admin-status-msg").classList.remove("text-green-500", "text-blue-500");
        document.getElementById("admin-status-msg").classList.add("text-red-500");
    }
};

// **FIXED:** Bus CRUD
document.getElementById("add-bus").onclick = async () => {
// ... (rest of the Bus CRUD listener is unchanged)
    const data = {
        bus_id: document.getElementById("bus-id").value, // Correctly using bus-id for the route/bus identifier
        license_plate: document.getElementById("bus-license").value,
        current_latitude: document.getElementById("bus-lat").value,
        current_longitude: document.getElementById("bus-lon").value
    };
    // Basic validation check
    if (data.bus_id && data.license_plate && data.current_latitude && data.current_longitude) {
        const res = await adminApiCall("/api/admin/bus", "POST", data);
        if (res) showAllBuses();
    } else {
        document.getElementById("admin-status-msg").textContent = "Please fill all Bus fields to add/update.";
        document.getElementById("admin-status-msg").classList.remove("text-green-500", "text-blue-500");
        document.getElementById("admin-status-msg").classList.add("text-red-500");
    }
};

// Schedule CRUD
document.getElementById("add-sch").onclick = async () => {
// ... (rest of the Schedule CRUD listener is unchanged)
    const data = {
        bus_id: document.getElementById("sch-bus-id").value,
        source_station_id: document.getElementById("sch-src").value,
        dest_station_id: document.getElementById("sch-dest").value,
        departure_time: document.getElementById("sch-dep").value,
        arrival_time: document.getElementById("sch-arr").value
    };
    // Basic validation check
    if (data.bus_id && data.source_station_id && data.dest_station_id && data.departure_time) {
        const res = await adminApiCall("/api/admin/schedule", "POST", data);
        if (res) showAllSchedules();
    } else {
        document.getElementById("admin-status-msg").textContent = "Please fill all Schedule fields to add/update.";
        document.getElementById("admin-status-msg").classList.remove("text-green-500", "text-blue-500");
        document.getElementById("admin-status-msg").classList.add("text-red-500");
    }
};

// Fare CRUD
document.getElementById("add-fare").onclick = async () => {
// ... (rest of the Fare CRUD listener is unchanged)
    const data = {
        source: document.getElementById("fare-admin-src").value,
        destination: document.getElementById("fare-admin-dest").value,
        amount: document.getElementById("fare-admin-amount").value
    };
    // Basic validation check
    if (data.source && data.destination && data.amount) {
        const res = await adminApiCall("/api/admin/fare", "POST", data);
        if (res) showAllFares();
    } else {
        document.getElementById("admin-status-msg").textContent = "Please fill all Fare fields to add/update.";
        document.getElementById("admin-status-msg").classList.remove("text-green-500", "text-blue-500");
        document.getElementById("admin-status-msg").classList.add("text-red-500");
    }
};


document.getElementById("view-stations-btn").onclick = showAllStations;
document.getElementById("view-buses-btn").onclick = showAllBuses;
document.getElementById("view-schedules-btn").onclick = showAllSchedules;
document.getElementById("view-fares-btn").onclick = showAllFares;

// --- Voice Recognition ---
function startVoiceInput(callback) {
// ... (rest of the startVoiceInput function is unchanged)
  if (!("webkitSpeechRecognition" in window)) {
    alert("Speech recognition not supported!");
    return;
  }
  const recognition = new webkitSpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.onresult = e => callback(e.results[0][0].transcript);
  recognition.start();
}

// --- Voice Output (Text-to-Speech) ---
function speak(text) {
// ... (rest of the speak function is unchanged)
  if (isMuted) {
    return;
  }
  if ("speechSynthesis" in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  } else {
    console.warn("Text-to-speech not supported!");
  }
}

// Ensure speech is cancelled when navigating away
window.addEventListener('beforeunload', () => {
    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
});