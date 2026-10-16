const fileInput = document.getElementById("csv-file");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");
const profile = document.getElementById("profile");
const chat = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const status = document.getElementById("status");
const sendButton = document.getElementById("send-button");

let sessionId = localStorage.getItem("dataAgentSession");

if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem("dataAgentSession", sessionId);
}

function addMessage(role, text) {
  const element = document.createElement("div");
  element.className = `message ${role}`;
  element.textContent = text;
  chat.appendChild(element);
  chat.scrollTop = chat.scrollHeight;
}

function showProfile(data) {
  const tableRows = data.preview.map((row) => {
    const cells = data.columns.map(
      (column) => `<td>${String(row[column] ?? "")}</td>`
    ).join("");
    return `<tr>${cells}</tr>`;
  }).join("");

  const headers = data.columns.map(
    (column) => `<th>${column}</th>`
  ).join("");

  profile.innerHTML = `
    <strong>${data.rows} rows</strong>
    <p>Columns: ${data.columns.join(", ")}</p>
    <p>Missing values: ${JSON.stringify(data.missing_values)}</p>
    <table>
      <thead><tr>${headers}</tr></thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

uploadButton.addEventListener("click", async () => {
  const file = fileInput.files[0];

  if (!file) {
    uploadStatus.textContent = "Choose a CSV file first.";
    return;
  }

  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);

  uploadStatus.textContent = "Uploading...";
  uploadButton.disabled = true;

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Upload failed.");
    }

    showProfile(data);
    uploadStatus.textContent = "CSV uploaded. Ask a question below.";
    addMessage("assistant", "Dataset loaded. What would you like to know?");
  } catch (error) {
    uploadStatus.textContent = error.message;
  } finally {
    uploadButton.disabled = false;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) return;

  addMessage("user", message);
  messageInput.value = "";
  status.textContent = "Analyzing...";
  sendButton.disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Request failed.");
    }

    addMessage("assistant", data.reply);
    status.textContent = "Ready";
  } catch (error) {
    addMessage("assistant", `Error: ${error.message}`);
    status.textContent = "Could not complete the request.";
  } finally {
    sendButton.disabled = false;
  }
});

document.getElementById("reset-button").addEventListener("click", async () => {
  await fetch("/reset", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      session_id: sessionId,
      message: "",
    }),
  });

  chat.replaceChildren();
  addMessage("assistant", "Conversation cleared. Your uploaded dataset remains available.");
});