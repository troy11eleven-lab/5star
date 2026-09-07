// Backend base URL — the __PORT_8000__ placeholder is rewritten by the deploy
// pipeline to proxy to the FastAPI server running on port 8000 in the sandbox.
const API_BASE = "__PORT_8000__";

// ---------- Deterministic-looking star field (decorative) ----------
(function renderStars() {
  const field = document.getElementById("starField");
  if (!field) return;
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("viewBox", "0 0 1000 640");

  let seed = 42;
  function rand() {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }

  for (let i = 0; i < 150; i++) {
    const cx = rand() * 1000;
    const cy = rand() * 560;
    const r = rand() * 1.3 + 0.3;
    const opacity = (rand() * 0.6 + 0.25).toFixed(2);
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", cx.toFixed(1));
    circle.setAttribute("cy", cy.toFixed(1));
    circle.setAttribute("r", r.toFixed(2));
    circle.setAttribute("fill", "#F3EFE3");
    circle.setAttribute("opacity", opacity);
    svg.appendChild(circle);
  }
  field.appendChild(svg);
})();

// ---------- Form handling ----------
const form = document.getElementById("reportForm");
const submitBtn = document.getElementById("submitBtn");
const formStatus = document.getElementById("formStatus");

const previewSection = document.getElementById("previewSection");
const previewName = document.getElementById("previewName");
const previewMeta = document.getElementById("previewMeta");
const headlineStats = document.getElementById("headlineStats");
const wheelVisual = document.getElementById("wheelVisual");
const bodygraphVisual = document.getElementById("bodygraphVisual");
const gkVisual = document.getElementById("gkVisual");
const downloadBtn = document.getElementById("downloadBtn");
const downloadStatus = document.getElementById("downloadStatus");

let currentPreviewId = null;
let currentDepth = "comprehensive";
let currentName = "report";

function setStatus(message, type) {
  formStatus.textContent = message || "";
  formStatus.className = "form-status" + (type ? " " + type : "");
}

function setDownloadStatus(message, type) {
  downloadStatus.textContent = message || "";
  downloadStatus.className = "form-status" + (type ? " " + type : "");
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.classList.toggle("loading", isLoading);
}

function setDownloadLoading(isLoading) {
  downloadBtn.disabled = isLoading;
  downloadBtn.classList.toggle("loading", isLoading);
}

function slugify(name) {
  return (name || "report")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "") || "report";
}

async function extractErrorMessage(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length) {
      return data.detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
    }
    return "Something went wrong. Please check your details and try again.";
  } catch (e) {
    return "Something went wrong. Please check your details and try again.";
  }
}

function showChartSkeletons() {
  const skel = '<div class="chart-skel" aria-hidden="true"></div>';
  wheelVisual.innerHTML = skel;
  bodygraphVisual.innerHTML = skel;
  gkVisual.innerHTML = '<div class="chart-skel" aria-hidden="true" style="border-radius: 8px; aspect-ratio: 3 / 1;"></div>';
  previewSection.hidden = false;
}

function firstNameOf(fullName) {
  const trimmed = (fullName || "").trim();
  if (!trimmed) return "your";
  return trimmed.split(/\s+/)[0] + "'s";
}

function renderStat(label, value) {
  if (!value) return "";
  return `<div class="headline-stat"><span class="headline-stat-label">${label}</span><span class="headline-stat-value">${value}</span></div>`;
}

function renderPreview(data) {
  previewName.textContent = firstNameOf(data.name);
  previewMeta.textContent = `${data.birth_date_pretty} \u00b7 ${data.birth_time_pretty} \u00b7 ${data.birth_place}`;

  const s = data.stats || {};
  headlineStats.innerHTML = [
    renderStat("Sun sign", s.sun_sign),
    renderStat("Ascendant", s.ascendant),
    renderStat("HD type", s.hd_type),
    renderStat("Authority", s.hd_authority),
    renderStat("Profile", s.hd_profile),
  ].join("");

  wheelVisual.innerHTML = data.wheel_svg || "";
  bodygraphVisual.innerHTML = data.bodygraph_svg || "";
  gkVisual.innerHTML = data.gk_bands_html || "";

  currentPreviewId = data.preview_id;
  currentDepth = data.depth;
  currentName = data.name;
  setDownloadStatus("");

  previewSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const name = document.getElementById("name").value.trim();
  const birthDate = document.getElementById("birthDate").value;
  const birthTime = document.getElementById("birthTime").value;
  const birthPlace = document.getElementById("birthPlace").value.trim();
  const depth = form.querySelector('input[name="depth"]:checked').value;

  if (!name || !birthDate || !birthTime || !birthPlace) {
    setStatus("Please fill in every field so we can build an accurate chart.", "error");
    return;
  }

  setLoading(true);
  setStatus("Calculating your chart — this can take up to a minute…");
  showChartSkeletons();

  try {
    const response = await fetch(`${API_BASE}/api/preview-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        birth_date: birthDate,
        birth_time: birthTime,
        birth_place: birthPlace,
        depth,
      }),
    });

    if (!response.ok) {
      const message = await extractErrorMessage(response);
      setStatus(message, "error");
      previewSection.hidden = true;
      setLoading(false);
      return;
    }

    const data = await response.json();
    renderPreview(data);
    setStatus("Your chart preview is ready below.", "success");
  } catch (err) {
    setStatus("We couldn't reach the report service. Please try again in a moment.", "error");
    previewSection.hidden = true;
  } finally {
    setLoading(false);
  }
});

downloadBtn.addEventListener("click", async () => {
  if (!currentPreviewId) return;

  setDownloadLoading(true);
  setDownloadStatus("Rendering your full PDF — this can take up to a minute…");

  try {
    const response = await fetch(`${API_BASE}/api/download-report/${currentPreviewId}`);

    if (!response.ok) {
      const message = await extractErrorMessage(response);
      setDownloadStatus(message, "error");
      setDownloadLoading(false);
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slugify(currentName)}-five-system-celestial-report-${currentDepth}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setDownloadStatus("Your report is downloading now. Enjoy exploring your chart!", "success");
  } catch (err) {
    setDownloadStatus("We couldn't reach the report service. Please try again in a moment.", "error");
  } finally {
    setDownloadLoading(false);
  }
});
