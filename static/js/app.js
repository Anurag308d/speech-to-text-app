// ---------- Tabs ----------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => showView(tab.dataset.view));
});

function showView(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  document.dispatchEvent(new CustomEvent("viewchange", { detail: name }));
}

// ---------- Live transcription ----------
// The mic is recorded in short segments. A segment ends at a pause in speech (after at least
// MIN_SEG_MS) or at MAX_SEG_MS, so words are rarely cut in half. Each segment is a complete
// audio file that is sent to /api/transcribe, and the text is appended as it comes back.
const MIN_SEG_MS = 1500;
const MAX_SEG_MS = 6000;
const SILENCE_MS = 450;
const SILENCE_LEVEL = 0.015; // RMS below this counts as silence
const VOICE_LEVEL = 0.03;    // a segment must peak above this to be sent

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusEl = document.getElementById("status");
const liveEl = document.getElementById("live-text");

const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
  .find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
const ext = mimeType.includes("mp4") ? "mp4" : mimeType.includes("ogg") ? "ogg" : "webm";

let stream, audioCtx, analyser, levelTimer;
let recorder = null;
let recording = false;
let segStart = 0, silentSince = 0, segPeak = 0;
let sessionStart = 0;
let pieces = [];
let languages = [];
let queue = Promise.resolve();
let pending = 0;

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
}

function renderLive() {
  liveEl.textContent = pieces.join(" ");
  if (pending > 0) {
    const dots = document.createElement("span");
    dots.className = "typing";
    dots.textContent = " …";
    liveEl.appendChild(dots);
  }
  liveEl.scrollTop = liveEl.scrollHeight;
}

function currentLevel() {
  const buf = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(buf);
  let sum = 0;
  for (const v of buf) sum += v * v;
  return Math.sqrt(sum / buf.length);
}

function startSegment() {
  const chunks = [];
  const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.onstop = () => {
    const voiced = segPeak >= VOICE_LEVEL;
    if (recording) startSegment();
    if (voiced && chunks.length) sendSegment(new Blob(chunks, { type: rec.mimeType }));
  };
  recorder = rec;
  segStart = performance.now();
  silentSince = 0;
  segPeak = 0;
  rec.start();
}

function sendSegment(blob) {
  pending++;
  renderLive();
  queue = queue.then(async () => {
    try {
      const form = new FormData();
      form.append("audio", blob, `chunk.${ext}`);
      const res = await fetch("/api/transcribe", { method: "POST", body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`);
      if (data.text) {
        pieces.push(data.text);
        if (data.language) languages.push(data.language.toLowerCase());
      }
      if (recording) setStatus("Listening…");
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      pending--;
      renderLive();
    }
  });
}

function watchLevel() {
  const now = performance.now();
  const level = currentLevel();
  segPeak = Math.max(segPeak, level);
  if (level < SILENCE_LEVEL) {
    if (!silentSince) silentSince = now;
  } else {
    silentSince = 0;
  }
  const elapsed = now - segStart;
  const pausedLongEnough = silentSince && now - silentSince >= SILENCE_MS;
  if (recorder && recorder.state === "recording" &&
      ((elapsed >= MIN_SEG_MS && pausedLongEnough && segPeak >= VOICE_LEVEL) || elapsed >= MAX_SEG_MS)) {
    recorder.stop(); // onstop starts the next segment
  }
}

async function startRecording() {
  if (!window.MediaRecorder) {
    setStatus("This browser can't record audio. Try Chrome or Edge.", true);
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
    });
  } catch {
    setStatus("Microphone permission was denied.", true);
    return;
  }
  audioCtx = new AudioContext();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;
  audioCtx.createMediaStreamSource(stream).connect(analyser);

  pieces = [];
  languages = [];
  sessionStart = performance.now();
  recording = true;
  startSegment();
  levelTimer = setInterval(watchLevel, 100);

  btnStart.disabled = true;
  btnStop.disabled = false;
  liveEl.textContent = "";
  setStatus("Listening…");
}

async function stopRecording() {
  recording = false;
  btnStop.disabled = true;
  clearInterval(levelTimer);
  setStatus("Finishing…");

  // Wait for the last segment to be handed off, then for all requests to finish.
  if (recorder && recorder.state === "recording") {
    await new Promise((resolve) => {
      recorder.addEventListener("stop", () => setTimeout(resolve, 0), { once: true });
      recorder.stop();
    });
  }
  await queue;
  stream.getTracks().forEach((t) => t.stop());
  audioCtx.close();

  const text = pieces.join(" ").trim();
  const duration = (performance.now() - sessionStart) / 1000;
  btnStart.disabled = false;
  if (!text) {
    setStatus("No speech detected, nothing saved.");
    return;
  }
  try {
    const res = await fetch("/api/transcripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: makeTitle(text),
        text,
        language: mostCommon(languages),
        duration_seconds: Math.round(duration * 10) / 10,
      }),
    });
    if (!res.ok) throw new Error(`Save failed (${res.status})`);
    setStatus("Saved to history.");
  } catch (err) {
    setStatus(err.message, true);
  }
}

function makeTitle(text) {
  const words = text.split(/\s+/).slice(0, 7).join(" ");
  return words.length < text.length ? `${words}…` : words;
}

function mostCommon(list) {
  if (!list.length) return null;
  const counts = {};
  list.forEach((x) => (counts[x] = (counts[x] || 0) + 1));
  const langs = Object.keys(counts);
  return langs.length > 1 ? langs.sort((a, b) => counts[b] - counts[a]).join(", ") : langs[0];
}

btnStart.addEventListener("click", startRecording);
btnStop.addEventListener("click", stopRecording);

// ---------- History dashboard (CRUD) ----------
const listEl = document.getElementById("history-list");
const searchEl = document.getElementById("search");
let searchTimer;

document.addEventListener("viewchange", (e) => e.detail === "history" && loadHistory());
searchEl.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadHistory, 250);
});

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res;
}

async function loadHistory() {
  const q = searchEl.value.trim();
  try {
    const res = await api(`/api/transcripts${q ? `?q=${encodeURIComponent(q)}` : ""}`);
    renderHistory(await res.json());
  } catch (err) {
    listEl.innerHTML = "";
    listEl.append(el("li", { className: "empty error" }, err.message));
  }
}

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  children.forEach((c) => node.append(c));
  return node;
}

function formatDate(iso) {
  // SQLite returns times without a zone; they are stored in UTC.
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function renderHistory(items) {
  listEl.innerHTML = "";
  if (!items.length) {
    listEl.append(el("li", { className: "empty" },
      searchEl.value ? "No transcripts match your search." : "No transcripts yet. Record one first."));
    return;
  }
  items.forEach((t) => listEl.append(renderItem(t)));
}

function renderItem(t) {
  const li = el("li", { className: "item" });
  const meta = [formatDate(t.created_at), t.language, t.duration_seconds && `${t.duration_seconds}s`]
    .filter(Boolean).join(" · ");

  const view = () => {
    li.innerHTML = "";
    const playBtn = el("button", { textContent: "Play" });
    const editBtn = el("button", { textContent: "Edit" });
    const delBtn = el("button", { textContent: "Delete", className: "danger" });
    playBtn.onclick = () => speak(t.text, playBtn);
    editBtn.onclick = edit;
    delBtn.onclick = () => confirmDelete(delBtn);
    li.append(
      el("div", { className: "item-head" },
        el("div", {}, el("h3", { textContent: t.title }), el("div", { className: "meta", textContent: meta })),
        el("div", { className: "actions" }, playBtn, editBtn, delBtn)),
      el("p", { className: "item-text", textContent: t.text }));
  };

  const edit = () => {
    li.innerHTML = "";
    const title = el("input", { value: t.title, maxLength: 200 });
    const text = el("textarea", { value: t.text, rows: 5 });
    const save = el("button", { textContent: "Save", className: "primary" });
    const cancel = el("button", { textContent: "Cancel" });
    save.onclick = async () => {
      save.disabled = true;
      try {
        const res = await api(`/api/transcripts/${t.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: title.value.trim() || "Untitled", text: text.value }),
        });
        Object.assign(t, await res.json());
        view();
      } catch (err) {
        save.disabled = false;
        alertInline(li, err.message);
      }
    };
    cancel.onclick = view;
    li.append(el("div", { className: "edit-form" }, title, text, el("div", { className: "actions" }, save, cancel)));
    text.focus();
  };

  const confirmDelete = (btn) => {
    if (btn.dataset.armed) {
      api(`/api/transcripts/${t.id}`, { method: "DELETE" })
        .then(() => { li.remove(); if (!listEl.children.length) renderHistory([]); })
        .catch((err) => alertInline(li, err.message));
      return;
    }
    btn.dataset.armed = "1";
    btn.textContent = "Confirm delete";
    setTimeout(() => { delete btn.dataset.armed; btn.textContent = "Delete"; }, 3000);
  };

  view();
  return li;
}

function alertInline(li, message) {
  li.querySelector(".inline-error")?.remove();
  li.append(el("p", { className: "inline-error", textContent: message }));
}

// ---------- Text to speech ----------
// Uses the server's open-source Piper voices. If the server can't speak (for example the voices
// are still downloading), it falls back to the browser's built-in speech.
let currentAudio = null;

async function speak(text, btn) {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
    document.querySelectorAll("button.playing").forEach((b) => { b.classList.remove("playing"); b.textContent = "Play"; });
    if (btn.dataset.playing) { delete btn.dataset.playing; return; }
  }
  speechSynthesis.cancel();
  btn.textContent = "Loading…";
  btn.disabled = true;
  try {
    const res = await api("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const url = URL.createObjectURL(await res.blob());
    const audio = new Audio(url);
    currentAudio = audio;
    btn.dataset.playing = "1";
    btn.classList.add("playing");
    btn.textContent = "Stop";
    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      delete btn.dataset.playing;
      btn.classList.remove("playing");
      btn.textContent = "Play";
    };
    await audio.play();
  } catch {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = /[\u0900-\u097F]/.test(text) ? "hi-IN" : "en-IN";
    speechSynthesis.speak(u);
    btn.textContent = "Play";
  } finally {
    btn.disabled = false;
  }
}
