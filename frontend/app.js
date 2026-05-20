const timeline = document.querySelector("#timeline");
const composer = document.querySelector("#composer");
const messageInput = document.querySelector("#messageInput");
const statusPill = document.querySelector("#statusPill");
const modelName = document.querySelector("#modelName");
const voiceStatus = document.querySelector("#voiceStatus");
const screenButton = document.querySelector("#screenButton");
const screenImage = document.querySelector("#screenImage");
const screenFrame = document.querySelector(".screen-frame");
const uplinkStatus = document.querySelector("#uplinkStatus");
const localTime = document.querySelector("#localTime");
const quickChips = document.querySelectorAll(".quick-chip");

let sessionId = localStorage.getItem("eva-session-id") || null;

function addMessage(role, content = "") {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.innerHTML = `<span>${role === "user" ? "You" : "Eva"}</span><p></p>`;
  node.querySelector("p").textContent = content;
  timeline.appendChild(node);
  timeline.scrollTop = timeline.scrollHeight;
  return node;
}

function setMessage(node, content) {
  node.querySelector("p").textContent = content;
  timeline.scrollTop = timeline.scrollHeight;
}

function updateClock() {
  if (!localTime) return;
  localTime.textContent = new Intl.DateTimeFormat([], {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    statusPill.textContent = data.ok ? "Online" : "Degraded";
    uplinkStatus.textContent = data.ok ? "Live" : "Degraded";
    modelName.textContent = data.fast_model && data.deep_model
      ? `${data.fast_model} / ${data.deep_model}`
      : data.model || "Unknown";
    voiceStatus.textContent = data.voice_enabled ? "Enabled" : "Modular";
  } catch {
    statusPill.textContent = "Offline";
    uplinkStatus.textContent = "Offline";
    modelName.textContent = "Unavailable";
  }
}

async function sendStreamingChat(message) {
  const evaNode = addMessage("eva", "");
  evaNode.classList.add("streaming");
  let reply = "";

  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message, session_id: sessionId}),
  });

  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Eva stream failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      if (event.type === "meta") {
        if (event.session_id) {
          sessionId = event.session_id;
          localStorage.setItem("eva-session-id", sessionId);
        }
        statusPill.textContent = event.source === "fast-command" ? "Instant" : "Streaming";
        uplinkStatus.textContent = "Linked";
      }
      if (event.type === "planning") {
        statusPill.textContent = "Planning";
        setMessage(evaNode, event.message || "Planning...");
      }
      if (event.type === "tool") {
        statusPill.textContent = "Tool";
        const label = event.tool === "web_search" ? "Searching web with Tavily..." : `Tool: ${event.tool}`;
        addMessage("eva", label);
      }
      if (event.type === "tool_result") {
        if (event.tool === "web_search" && event.result && typeof event.result === "object") {
          const count = Array.isArray(event.result.results) ? event.result.results.length : 0;
          if (event.result.ok && event.result.provider === "tavily") {
            addMessage("eva", `Tavily returned ${count} result${count === 1 ? "" : "s"}.`);
          } else if (event.result.fallback === "browser") {
            addMessage("eva", "Tavily failed, opening browser search instead.");
          } else {
            addMessage("eva", `Result: ${event.tool} ${event.ok ? "ok" : "failed"}.`);
          }
        } else {
          const detail = event.ok ? JSON.stringify(event.result) : event.error;
          addMessage("eva", `Result: ${event.tool} ${event.ok ? "ok" : "failed"}. ${detail || ""}`);
        }
      }
      if (event.type === "confirmation_required") {
        statusPill.textContent = "Confirm";
        uplinkStatus.textContent = "Waiting";
      }
      if (event.type === "token") {
        reply += event.text;
        setMessage(evaNode, reply);
      }
      if (event.type === "error") {
        reply = event.message;
        setMessage(evaNode, reply);
        statusPill.textContent = "Model issue";
        uplinkStatus.textContent = "Issue";
      }
      if (event.type === "done") {
        reply = event.reply || reply;
        setMessage(evaNode, reply);
      }
    }
  }

  evaNode.classList.remove("streaming");
  statusPill.textContent = "Online";
  uplinkStatus.textContent = "Live";
}

async function submitCommand(message) {
  if (!message) return;
  addMessage("user", message);
  statusPill.textContent = "Thinking";
  uplinkStatus.textContent = "Routing";

  try {
    await sendStreamingChat(message);
  } catch (error) {
    addMessage("eva", `I hit a local error: ${error.message}`);
    statusPill.textContent = "Error";
    uplinkStatus.textContent = "Issue";
  }
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  messageInput.value = "";
  await submitCommand(message);
});

quickChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt || chip.textContent.trim();
    submitCommand(prompt);
  });
});

screenButton.addEventListener("click", async () => {
  screenButton.disabled = true;
  screenButton.textContent = "Capturing...";
  try {
    const response = await fetch(`/api/screen/snapshot?t=${Date.now()}`);
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Screen capture failed");
    }
    const blob = await response.blob();
    screenImage.src = URL.createObjectURL(blob);
    screenFrame.classList.add("has-image");
  } catch (error) {
    addMessage("eva", `Screen preview failed: ${error.message}`);
  } finally {
    screenButton.disabled = false;
    screenButton.textContent = "Capture screen";
  }
});

updateClock();
setInterval(updateClock, 1000);
loadHealth();




