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

function setStatus(message, type) {
  formStatus.textContent = message || "";
  formStatus.className = "form-status" + (type ? " " + type : "");
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.classList.toggle("loading", isLoading);
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
  setStatus("Calculating your chart and rendering your report — this can take up to a minute…");

  try {
    const response = await fetch(`${API_BASE}/api/generate-report`, {
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
      setLoading(false);
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slugify(name)}-five-system-celestial-report-${depth}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("Your report is downloading now. Enjoy exploring your chart!", "success");
  } catch (err) {
    setStatus("We couldn't reach the report service. Please try again in a moment.", "error");
  } finally {
    setLoading(false);
  }
});
