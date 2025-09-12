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
};

// --- API Calls ---
async function callAPI(query) {
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = `<em>Processing: ${query}</em>`;
  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: query })
    });
    const data = await res.json();
    if (data.status === "ok") renderResult(data.result);
    else resultDiv.innerHTML = `<p style="color:red">${data.message}</p>`;
  } catch (err) {
    resultDiv.innerHTML = `<p style="color:red">Error: ${err}</p>`;
  }
}

// --- Mute Toggle ---
let isMuted = false;
let lastSpokenText = ""; // Variable to store the last text to be spoken

document.getElementById("mute-btn").onclick = () => {
  isMuted = !isMuted;
  const muteIcon = document.getElementById("mute-icon");
  if (isMuted) {
    muteIcon.innerText = "🔇";
    document.getElementById("mute-btn").innerHTML = "<span id='mute-icon'>🔇</span> Unmute";
    window.speechSynthesis.cancel(); // Cancel any ongoing speech when muting
  } else {
    muteIcon.innerText = "🔊";
    document.getElementById("mute-btn").innerHTML = "<span id='mute-icon'>🔊</span> Mute";
    replayLastSpokenText(); // Speak the last text when unmuted
  }
};

// --- Render Results ---
function renderResult(res) {
  const resultDiv = document.getElementById("result");
  if (res.type === "text") {
    resultDiv.innerHTML = `<p>${res.text}</p>`;
    lastSpokenText = res.text; // Store the text
    speak(lastSpokenText);
  } else if (res.type === "table") {
    let html = "<table border='1' class='w-full text-left border-collapse'><tr>";
    res.headers.forEach(h => html += `<th class='border px-2 py-1'>${h}</th>`);
    html += "</tr>";
    res.rows.forEach(r => {
      html += "<tr>";
      r.forEach(c => html += `<td class='border px-2 py-1'>${c}</td>`);
      html += "</tr>";
    });
    html += "</table>";
    resultDiv.innerHTML = html;

    // 🔊 Prepare table content to be spoken
    let spokenText = `Here are ${res.rows.length} records. `;
    // Read all rows
    res.rows.forEach((row, idx) => {
      spokenText += `Record ${idx + 1}: `;
      row.forEach((cell, i) => {
        spokenText += `${res.headers[i]} ${cell}, `;
      });
    });
    lastSpokenText = spokenText; // Store the text
    speak(lastSpokenText);
  } else if (res.type === "map") {
    resultDiv.innerHTML = `<a href="${res.url}" target="_blank">Open in Maps</a>`;
    lastSpokenText = "The map link is ready. You can open it in a new tab."; // Store the text
    speak(lastSpokenText);
  }
}

// --- Query Box + Ask Button ---
document.getElementById("ask-btn").onclick = () => {
  const q = document.getElementById("queryInput").value.trim();
  if (q) callAPI(q);
};

// --- Mic Button ---
document.getElementById("mic-btn").onclick = () => {
  startVoiceInput(transcript => {
    document.getElementById("queryInput").value = transcript;
    callAPI(transcript);
  });
};

// --- Quick Action Buttons ---
document.getElementById("stations-btn").onclick = () => callAPI("list all stations");
document.getElementById("routes-btn").onclick = () => callAPI("show all routes");

// --- Modal Submit Handlers ---
document.getElementById("track-submit").onclick = () => {
  const bus = document.getElementById("track-input").value.trim();
  if (bus) {
    callAPI(`track bus ${bus}`);
    closeModal("track-modal");
  }
};
document.getElementById("fare-submit").onclick = () => {
  const src = document.getElementById("fare-src").value.trim();
  const dst = document.getElementById("fare-dest").value.trim();
  if (src && dst) {
    callAPI(`fare from ${src} to ${dst}`);
    closeModal("fare-modal");
  }
};

// --- ADMIN PANEL CRUD HANDLERS ---
async function adminAPI(endpoint, data) {
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    return res.json();
}

async function getRecord(endpoint, id) {
    const res = await fetch(`${endpoint}/${id}`);
    return res.json();
}

// Function to handle fetching and populating station data
document.getElementById("station-id").onchange = async () => {
    const id = document.getElementById("station-id").value;
    if (id) {
        const result = await getRecord('/api/admin/get_station', id);
        if (result.status === 'ok' && result.data) {
            document.getElementById("station-name").value = result.data.station_name;
        } else {
            document.getElementById("station-name").value = ''; // Clear if not found
        }
    }
};

// Function to handle fetching and populating bus data
document.getElementById("bus-id").onchange = async () => {
    const id = document.getElementById("bus-id").value;
    if (id) {
        const result = await getRecord('/api/admin/get_bus', id);
        if (result.status === 'ok' && result.data) {
            document.getElementById("lat").value = result.data.current_latitude;
            document.getElementById("lon").value = result.data.current_longitude;
        } else {
            document.getElementById("lat").value = '';
            document.getElementById("lon").value = '';
        }
    }
};

// Function to handle fetching and populating schedule data
document.getElementById("sch-bus").onchange = async () => {
    const id = document.getElementById("sch-bus").value;
    if (id) {
        const result = await getRecord('/api/admin/get_schedule', id);
        if (result.status === 'ok' && result.data) {
            document.getElementById("sch-src").value = result.data.source_station_id;
            document.getElementById("sch-dest").value = result.data.dest_station_id;
            document.getElementById("sch-dep").value = result.data.departure_time;
            document.getElementById("sch-arr").value = result.data.arrival_time;
        } else {
            document.getElementById("sch-src").value = '';
            document.getElementById("sch-dest").value = '';
            document.getElementById("sch-dep").value = '';
            document.getElementById("sch-arr").value = '';
        }
    }
};

document.getElementById("add-station").onclick = async () => {
    const id = document.getElementById("station-id").value;
    const name = document.getElementById("station-name").value;
    if (id && name) {
        const result = await adminAPI('/api/admin/station', { id, name });
        alert(result.message);
    } else {
        alert("Please fill in both fields.");
    }
};

document.getElementById("add-bus").onclick = async () => {
    const id = document.getElementById("bus-id").value;
    const lat = document.getElementById("lat").value;
    const lon = document.getElementById("lon").value;
    if (id && lat && lon) {
        const result = await adminAPI('/api/admin/bus', { id, lat, lon });
        alert(result.message);
    } else {
        alert("Please fill in all fields.");
    }
};

document.getElementById("add-sch").onclick = async () => {
    const bus = document.getElementById("sch-bus").value;
    const src = document.getElementById("sch-src").value;
    const dest = document.getElementById("sch-dest").value;
    const dep = document.getElementById("sch-dep").value;
    const arr = document.getElementById("sch-arr").value;
    if (bus && src && dest && dep && arr) {
        const result = await adminAPI('/api/admin/schedule', { bus, src, dest, dep, arr });
        alert(result.message);
    } else {
        alert("Please fill in all fields.");
    }
};

// NEW: Functions to fetch and display all records for the admin
async function showAllStations() {
  const resultDiv = document.getElementById("admin-results");
  resultDiv.innerHTML = "<em>Loading stations...</em>";
  const res = await fetch("/api/admin/get_all_stations");
  const data = await res.json();
  if (data.status === "ok") {
    renderAdminTable("stations", data.result.headers, data.result.rows, resultDiv);
  } else {
    resultDiv.innerHTML = `<p style="color:red">${data.message}</p>`;
  }
}

async function showAllBuses() {
  const resultDiv = document.getElementById("admin-results");
  resultDiv.innerHTML = "<em>Loading buses...</em>";
  const res = await fetch("/api/admin/get_all_buses");
  const data = await res.json();
  if (data.status === "ok") {
    renderAdminTable("buses", data.result.headers, data.result.rows, resultDiv);
  } else {
    resultDiv.innerHTML = `<p style="color:red">${data.message}</p>`;
  }
}

async function showAllSchedules() {
  const resultDiv = document.getElementById("admin-results");
  resultDiv.innerHTML = "<em>Loading schedules...</em>";
  const res = await fetch("/api/admin/get_all_schedules");
  const data = await res.json();
  if (data.status === "ok") {
    renderAdminTable("schedules", data.result.headers, data.result.rows, resultDiv);
  } else {
    resultDiv.innerHTML = `<p style="color:red">${data.message}</p>`;
  }
}

function fillAdminFormFromRow(type, rowData, headers) {
    if (type === "stations") {
        const idIndex = headers.indexOf("station_id");
        const nameIndex = headers.indexOf("station_name");
        document.getElementById("station-id").value = rowData[idIndex];
        document.getElementById("station-name").value = rowData[nameIndex];
    } else if (type === "buses") {
        const idIndex = headers.indexOf("route_no");
        const latIndex = headers.indexOf("current_latitude");
        const lonIndex = headers.indexOf("current_longitude");
        document.getElementById("bus-id").value = rowData[idIndex];
        document.getElementById("lat").value = rowData[latIndex];
        document.getElementById("lon").value = rowData[lonIndex];
    } else if (type === "schedules") {
        const busIndex = headers.indexOf("bus_id");
        const srcIndex = headers.indexOf("source_station_id");
        const destIndex = headers.indexOf("dest_station_id");
        const depIndex = headers.indexOf("departure_time");
        const arrIndex = headers.indexOf("arrival_time");
        document.getElementById("sch-bus").value = rowData[busIndex];
        document.getElementById("sch-src").value = rowData[srcIndex];
        document.getElementById("sch-dest").value = rowData[destIndex];
        document.getElementById("sch-dep").value = rowData[depIndex];
        document.getElementById("sch-arr").value = rowData[arrIndex];
    }
}

function renderAdminTable(type, headers, rows, targetDiv) {
  let html = "<table class='w-full text-left border-collapse admin-table'><tr>";
  headers.forEach(h => html += `<th class='border px-2 py-1'>${h}</th>`);
  html += "</tr>";
  rows.forEach((r, rowIndex) => {
    // Add a unique ID for each row to retrieve data later
    html += `<tr data-row-index="${rowIndex}" class="cursor-pointer hover:bg-gray-100">`;
    r.forEach(c => html += `<td class='border px-2 py-1'>${c}</td>`);
    html += "</tr>";
  });
  html += "</table>";
  targetDiv.innerHTML = html;

  // Add event listeners to the new table rows
  targetDiv.querySelectorAll('tr[data-row-index]').forEach(row => {
    row.addEventListener('click', () => {
        const rowIndex = row.dataset.rowIndex;
        const rowData = rows[rowIndex];
        fillAdminFormFromRow(type, rowData, headers);
    });
  });
}


// Add event listeners for the new "view all" buttons
document.getElementById("view-stations-btn").onclick = showAllStations;
document.getElementById("view-buses-btn").onclick = showAllBuses;
document.getElementById("view-schedules-btn").onclick = showAllSchedules;

// --- Voice Recognition ---
function startVoiceInput(callback) {
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
  if (isMuted) {
    return; // Do nothing if muted
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

function replayLastSpokenText() {
    if ("speechSynthesis" in window && lastSpokenText) {
        speak(lastSpokenText);
    }
}

// --- Bug Fix: Stop speech on page load
window.addEventListener('beforeunload', () => {
    window.speechSynthesis.cancel();
});