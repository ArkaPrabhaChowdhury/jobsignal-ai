const sourceCatalog = JSON.parse(document.getElementById("source-catalog").textContent);
const state = {
  listings: [],
  stats: null,
};

const $ = (selector) => document.querySelector(selector);

function text(tag, value, className = "") {
  const element = document.createElement(tag);
  element.textContent = value ?? "-";
  if (className) element.className = className;
  return element;
}

function relativeTime(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function setLoading(container, message) {
  container.replaceChildren(text("div", message, "loading-state"));
}

function renderMetrics(stats) {
  const skills = stats.top_skills || [];
  $("#total-listings").textContent = Number(stats.total_listings || 0).toLocaleString("en-IN");
  $("#source-count").textContent = Object.keys(stats.by_source || {}).length;
  $("#run-count").textContent = (stats.last_5_runs || []).length;
  $("#leading-skill").textContent = skills[0]?.skill || "No data";
  $("#leading-skill-detail").textContent = skills[0]
    ? `${skills[0].count} mentions in the current index`
    : "Waiting for skill data";
  $("#skill-sample").textContent = `${skills.reduce((sum, item) => sum + item.count, 0)} total mentions`;
  $("#updated-at").textContent = `Snapshot refreshed ${new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date())}`;
}

function renderSkills(skills) {
  const container = $("#skill-chart");
  container.replaceChildren();
  if (!skills.length) {
    container.append(text("div", "No skill data is available yet.", "empty-state"));
    return;
  }

  const maximum = Math.max(...skills.map((skill) => skill.count), 1);
  skills.slice(0, 8).forEach((skill, index) => {
    const row = document.createElement("div");
    row.className = "skill-row";
    const track = document.createElement("div");
    track.className = "skill-track";
    const fill = document.createElement("div");
    fill.className = "skill-fill";
    fill.style.transitionDelay = `${index * 45}ms`;
    track.append(fill);
    row.append(text("span", skill.skill, "skill-name"), track, text("span", skill.count, "skill-value"));
    container.append(row);
    requestAnimationFrame(() => {
      fill.style.width = `${Math.max(4, (skill.count / maximum) * 100)}%`;
    });
  });
}

function renderSources(stats) {
  const container = $("#source-table");
  const sourceSelect = $("#source-filter");
  const ingestSelect = $("#sources");
  container.replaceChildren();
  sourceSelect.querySelectorAll("option:not(:first-child)").forEach((option) => option.remove());
  ingestSelect.replaceChildren();

  sourceCatalog.forEach((source) => {
    const count = stats.by_source?.[source.name] || 0;
    const row = document.createElement("div");
    row.className = "source-row";
    const info = document.createElement("div");
    info.append(text("p", source.name, "source-name"), text("p", source.description, "source-description"));
    const meta = document.createElement("div");
    meta.className = "source-meta";
    meta.append(text("strong", count.toLocaleString("en-IN")), text("span", `${source.mode} mode`));
    row.append(info, meta);
    container.append(row);

    const filterOption = new Option(source.name, source.name);
    sourceSelect.add(filterOption);

    const isDefaultSource = source.name === "greenhouse_playwright";
    const ingestOption = new Option(
      `${source.name} - ${source.mode}`,
      source.name,
      isDefaultSource,
      isDefaultSource,
    );
    ingestSelect.add(ingestOption);
  });
}

function renderListings() {
  const query = $("#listing-search").value.trim().toLowerCase();
  const source = $("#source-filter").value;
  const filtered = state.listings.filter((listing) => {
    const haystack = [
      listing.title,
      listing.company,
      listing.location,
      ...(listing.skills || []),
    ].join(" ").toLowerCase();
    return (!query || haystack.includes(query)) && (!source || listing.source === source);
  });

  const body = $("#listing-body");
  body.replaceChildren();
  $("#listing-count").textContent = `${filtered.length} result${filtered.length === 1 ? "" : "s"}`;
  $("#listing-empty").classList.toggle("hidden", filtered.length > 0);
  $(".table-scroll").classList.toggle("hidden", filtered.length === 0);

  filtered.forEach((listing) => {
    const row = document.createElement("tr");
    const roleCell = document.createElement("td");
    const roleLink = text("a", listing.title, "role-link");
    roleLink.href = listing.url;
    roleLink.target = "_blank";
    roleLink.rel = "noreferrer";
    roleCell.append(roleLink);

    const confidenceValue = Number(listing.confidence || 0);
    const confidence = text("span", `${Math.round(confidenceValue * 100)}%`, `confidence${confidenceValue >= 0.75 ? " high" : ""}`);
    const confidenceCell = document.createElement("td");
    confidenceCell.append(confidence);
    const sourceCell = document.createElement("td");
    sourceCell.append(text("span", listing.source, "source-label"));

    row.append(
      roleCell,
      text("td", listing.company || "Unknown"),
      text("td", listing.location || "Not specified"),
      text("td", (listing.skills || []).slice(0, 4).join(", ") || "Not enriched", "skill-cell"),
      sourceCell,
      confidenceCell,
    );
    body.append(row);
  });
}

function renderRuns(runs) {
  const container = $("#run-list");
  container.replaceChildren();
  if (!runs.length) {
    container.append(text("div", "No crawl runs have been recorded.", "empty-state"));
    return;
  }

  runs.forEach((run) => {
    const row = document.createElement("div");
    row.className = "run-row";
    const source = document.createElement("div");
    source.className = "run-source";
    source.append(text("strong", run.source), text("span", String(run.run_id).slice(0, 8)));

    const stat = (value, label) => {
      const wrapper = document.createElement("div");
      wrapper.className = "run-stat";
      wrapper.append(text("strong", value), text("span", label));
      return wrapper;
    };

    row.append(
      source,
      stat(run.fetched, "Fetched"),
      stat(run.stored, "Stored"),
      stat(run.skipped_low_confidence, "Low confidence"),
      text("span", relativeTime(run.started_at), "run-time"),
    );
    container.append(row);
  });
}

async function loadDashboard() {
  setLoading($("#skill-chart"), "Loading skill demand...");
  setLoading($("#source-table"), "Loading source coverage...");
  setLoading($("#run-list"), "Loading crawl runs...");

  const [statsResponse, listingsResponse, healthResponse] = await Promise.all([
    fetch("/stats"),
    fetch("/listings/recent?limit=24"),
    fetch("/health"),
  ]);

  if (!statsResponse.ok || !listingsResponse.ok) {
    throw new Error("Market data could not be loaded.");
  }

  state.stats = await statsResponse.json();
  state.listings = await listingsResponse.json();
  renderMetrics(state.stats);
  renderSkills(state.stats.top_skills || []);
  renderSources(state.stats);
  renderListings();
  renderRuns(state.stats.last_5_runs || []);

  const health = $("#health-status");
  if (healthResponse.ok) {
    health.textContent = "Data connection healthy";
    health.className = "data-status ok";
  } else {
    health.textContent = "Data connection degraded";
    health.className = "data-status error";
  }
}

$("#listing-search").addEventListener("input", renderListings);
$("#source-filter").addEventListener("change", renderListings);
$("#reset-filters").addEventListener("click", () => {
  $("#listing-search").value = "";
  $("#source-filter").value = "";
  renderListings();
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    $("#question").value = button.dataset.question;
    $("#question").focus();
  });
});

$("#query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = $("#query-result");
  output.className = "query-output empty";
  output.replaceChildren(text("p", "Analyzing indexed listings..."));

  try {
    const response = await fetch(`/query?q=${encodeURIComponent($("#question").value.trim())}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Analysis failed.");

    output.className = "query-output";
    const answer = text("p", data.answer || "No answer returned.", "query-answer");
    output.replaceChildren(answer);
    if (data.sources?.length) {
      const sources = document.createElement("div");
      sources.className = "query-sources";
      sources.append(text("strong", "Source records"));
      data.sources.forEach((url) => {
        const link = text("a", url);
        link.href = url;
        link.target = "_blank";
        link.rel = "noreferrer";
        sources.append(link);
      });
      output.append(sources);
    }
  } catch (error) {
    output.className = "query-output empty";
    output.replaceChildren(text("p", error.message || "Analysis failed."));
  }
});

$("#ingest-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = $("#ingest-result");
  const selectedSources = Array.from($("#sources").selectedOptions).map((option) => option.value);
  result.className = "inline-result";
  result.textContent = "Starting ingestion...";

  try {
    const response = await fetch("/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: $("#role").value.trim(),
        sources: selectedSources,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Ingestion could not be started.");
    result.textContent = `Run ${data.run_id} started for ${(data.sources || []).join(", ")}.`;
  } catch (error) {
    result.className = "inline-result error";
    result.textContent = error.message || "Ingestion could not be started.";
  }
});

$("#mobile-menu").addEventListener("click", () => {
  const open = document.body.classList.toggle("nav-open");
  $("#mobile-menu").setAttribute("aria-expanded", String(open));
});

document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    document.body.classList.remove("nav-open");
    $("#mobile-menu").setAttribute("aria-expanded", "false");
    document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

loadDashboard().catch((error) => {
  $("#health-status").textContent = "Data connection unavailable";
  $("#health-status").className = "data-status error";
  setLoading($("#skill-chart"), error.message);
  setLoading($("#source-table"), error.message);
  setLoading($("#run-list"), error.message);
});
