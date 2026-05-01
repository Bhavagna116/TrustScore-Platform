/**
 * dashboard.js
 * ------------
 * Client-side interactivity for TrustScore AI dashboard.
 * Handles: filtering, search, Chart.js visualizations.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  let activeType = "all";
  let minScore = 0.0;
  let activeTag = "";
  let searchQuery = "";

  const cards = document.querySelectorAll(".source-card");
  const searchInput = document.getElementById("search-input");
  const scoreSlider = document.getElementById("score-slider");
  const scoreVal = document.getElementById("score-val");
  const typeButtons = document.querySelectorAll(".type-btn");
  const tagPills = document.querySelectorAll("#filter-tags .tag-pill");
  const resetBtn = document.getElementById("reset-filters");
  const sortSelect = document.getElementById("sort-select");
  const exportCsvBtn = document.getElementById("export-csv");
  const exportJsonBtn = document.getElementById("export-json");
  const scrapeBtn = document.getElementById("scrape-btn");
  const scrapeInput = document.getElementById("scrape-url-input");
  const scrapeStatus = document.getElementById("scrape-status");

  // ── Filter Logic ───────────────────────────────────────────────────────────
  function applyFilters() {
    let visibleCount = 0;
    cards.forEach((card) => {
      const type = card.dataset.type || "";
      const score = parseFloat(card.dataset.score || "0");
      const title = card.dataset.title || "";
      const author = card.dataset.author || "";
      const tags = card.dataset.tags || "";

      const typeOk = activeType === "all" || type === activeType;
      const scoreOk = score >= minScore;
      const tagOk = !activeTag || tags.toLowerCase().includes(activeTag.toLowerCase());
      const searchOk = !searchQuery ||
        title.includes(searchQuery) || author.includes(searchQuery);

      const visible = typeOk && scoreOk && tagOk && searchOk;
      card.classList.toggle("hidden", !visible);
      if (visible) visibleCount++;
    });

    // Show/hide empty state
    let emptyState = document.getElementById("no-results");
    if (visibleCount === 0 && !emptyState) {
      emptyState = document.createElement("div");
      emptyState.id = "no-results";
      emptyState.className = "empty-state";
      emptyState.innerHTML = `
        <div class="empty-icon">🔍</div>
        <h3>No matching sources</h3>
        <p>Try adjusting your filters.</p>
      `;
      document.getElementById("source-list").appendChild(emptyState);
    } else if (visibleCount > 0 && emptyState) {
      emptyState.remove();
    }

    // Apply Sorting
    if (sortSelect) {
      const sortVal = sortSelect.value;
      const visibleCards = Array.from(cards).filter(c => !c.classList.contains("hidden"));
      const listContainer = document.getElementById("source-list");
      
      visibleCards.sort((a, b) => {
        if (sortVal === "score-desc") {
          return parseFloat(b.dataset.score || 0) - parseFloat(a.dataset.score || 0);
        } else if (sortVal === "score-asc") {
          return parseFloat(a.dataset.score || 0) - parseFloat(b.dataset.score || 0);
        } else if (sortVal === "date-desc") {
          const dateA = a.querySelector('.meta-item:nth-child(2)')?.textContent.replace('📅 ', '') || "";
          const dateB = b.querySelector('.meta-item:nth-child(2)')?.textContent.replace('📅 ', '') || "";
          return dateB.localeCompare(dateA);
        } else if (sortVal === "date-asc") {
          const dateA = a.querySelector('.meta-item:nth-child(2)')?.textContent.replace('📅 ', '') || "";
          const dateB = b.querySelector('.meta-item:nth-child(2)')?.textContent.replace('📅 ', '') || "";
          return dateA.localeCompare(dateB);
        }
        return 0; // default
      });

      visibleCards.forEach(card => listContainer.appendChild(card));
    }
  }

  // ── Event Listeners ────────────────────────────────────────────────────────
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      applyFilters();
    });
  }

  if (scoreSlider) {
    scoreSlider.addEventListener("input", (e) => {
      minScore = parseFloat(e.target.value);
      scoreVal.textContent = minScore.toFixed(1);
      applyFilters();
    });
  }

  typeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      activeType = btn.dataset.type;
      typeButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      applyFilters();
    });
  });

  tagPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const tag = pill.dataset.tag;
      if (activeTag === tag) {
        activeTag = "";
        pill.classList.remove("active");
      } else {
        tagPills.forEach((p) => p.classList.remove("active"));
        activeTag = tag;
        pill.classList.add("active");
      }
      applyFilters();
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      activeType = "all";
      minScore = 0.0;
      activeTag = "";
      searchQuery = "";
      if (searchInput) searchInput.value = "";
      if (scoreSlider) scoreSlider.value = 0;
      if (scoreVal) scoreVal.textContent = "0.0";
      typeButtons.forEach((b) => b.classList.remove("active"));
      document.getElementById("btn-all")?.classList.add("active");
      tagPills.forEach((p) => p.classList.remove("active"));
      applyFilters();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", applyFilters);
  }

  // ── Export Logic ───────────────────────────────────────────────────────────
  function getExportUrl(format) {
    const params = new URLSearchParams({ format });
    if (activeType !== "all") params.append("source_type", activeType);
    if (minScore > 0) params.append("min_score", minScore);
    if (activeTag) params.append("tag", activeTag);
    if (searchQuery) params.append("q", searchQuery);
    return `/api/export?${params.toString()}`;
  }

  if (exportCsvBtn) {
    exportCsvBtn.addEventListener("click", () => {
      window.location.href = getExportUrl("csv");
    });
  }

  if (exportJsonBtn) {
    exportJsonBtn.addEventListener("click", () => {
      window.open(getExportUrl("json"), "_blank");
    });
  }

  // ── Copy URL Logic ─────────────────────────────────────────────────────────
  document.querySelectorAll(".copy-url-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const url = btn.dataset.url;
      try {
        await navigator.clipboard.writeText(url);
        const originalIcon = btn.textContent;
        btn.textContent = "✅";
        setTimeout(() => { btn.textContent = originalIcon; }, 2000);
      } catch (err) {
        console.error("Failed to copy", err);
      }
    });
  });

  // ── Analyze New URL Logic ──────────────────────────────────────────────────
  if (scrapeBtn && scrapeInput && scrapeStatus) {
    scrapeBtn.addEventListener("click", async () => {
      const url = scrapeInput.value.trim();
      if (!url) return;

      scrapeBtn.disabled = true;
      scrapeInput.disabled = true;
      scrapeStatus.style.display = "block";
      scrapeStatus.textContent = "Processing... this may take a few seconds.";

      try {
        const res = await fetch("/api/scrape", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        
        const data = await res.json();
        if (res.ok) {
          scrapeStatus.textContent = "Success! Reloading...";
          scrapeStatus.style.color = "#10b981";
          setTimeout(() => window.location.reload(), 1000); // Simple reload to show new data + charts
        } else {
          scrapeStatus.textContent = `Error: ${data.error || 'Failed to process'}`;
          scrapeStatus.style.color = "#ef4444";
          scrapeBtn.disabled = false;
          scrapeInput.disabled = false;
        }
      } catch (err) {
        scrapeStatus.textContent = "Network error occurred.";
        scrapeStatus.style.color = "#ef4444";
        scrapeBtn.disabled = false;
        scrapeInput.disabled = false;
      }
    });
  }

  // ── Chart.js Configurations ────────────────────────────────────────────────
  if (typeof STATS === "undefined" || !STATS) return;

  const CHART_COLORS = {
    blog:    "rgba(99, 102, 241, 0.8)",
    youtube: "rgba(239, 68, 68, 0.8)",
    pubmed:  "rgba(34, 211, 238, 0.8)",
    high:    "rgba(16, 185, 129, 0.8)",
    medium:  "rgba(245, 158, 11, 0.8)",
    low:     "rgba(239, 68, 68, 0.8)",
  };

  const CHART_DEFAULTS = {
    plugins: {
      legend: {
        labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
      }
    },
    scales: {
      x: {
        grid: { color: "rgba(255,255,255,0.05)" },
        ticks: { color: "#94a3b8", font: { family: "Inter" } },
      },
      y: {
        grid: { color: "rgba(255,255,255,0.05)" },
        ticks: { color: "#94a3b8", font: { family: "Inter" } },
      }
    }
  };

  // 1. Score Breakdown by Source Type
  const breakdownCtx = document.getElementById("scoreBreakdownChart");
  if (breakdownCtx && STATS.by_type) {
    const types = Object.keys(STATS.by_type);
    const avgScores = types.map((t) => STATS.by_type[t].avg_score);
    const colors = types.map((t) => CHART_COLORS[t] || "rgba(99,102,241,0.8)");

    new Chart(breakdownCtx, {
      type: "bar",
      data: {
        labels: types.map((t) => t.charAt(0).toUpperCase() + t.slice(1)),
        datasets: [{
          label: "Avg Trust Score",
          data: avgScores,
          backgroundColor: colors,
          borderRadius: 8,
          borderSkipped: false,
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            callbacks: {
              label: (ctx) => ` Score: ${ctx.parsed.y.toFixed(2)}`
            }
          }
        },
        scales: {
          ...CHART_DEFAULTS.scales,
          y: { ...CHART_DEFAULTS.scales.y, min: 0, max: 1 }
        }
      }
    });
  }

  // 2. Tag Frequency Chart
  const tagCtx = document.getElementById("tagFreqChart");
  if (tagCtx && STATS.top_tags && STATS.top_tags.length > 0) {
    const topN = STATS.top_tags.slice(0, 8);
    new Chart(tagCtx, {
      type: "bar",
      data: {
        labels: topN.map((t) => t.tag),
        datasets: [{
          label: "Frequency",
          data: topN.map((t) => t.count),
          backgroundColor: "rgba(99, 102, 241, 0.7)",
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: "y",
        ...CHART_DEFAULTS,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            ticks: { ...CHART_DEFAULTS.scales.x.ticks, stepSize: 1 }
          },
          y: CHART_DEFAULTS.scales.y,
        }
      }
    });
  }

  // 3. Score Distribution Doughnut
  const distCtx = document.getElementById("distChart");
  if (distCtx && STATS.score_distribution) {
    const dist = STATS.score_distribution;
    new Chart(distCtx, {
      type: "doughnut",
      data: {
        labels: ["High (≥0.7)", "Medium (0.4-0.7)", "Low (<0.4)"],
        datasets: [{
          data: [dist.high, dist.medium, dist.low],
          backgroundColor: [
            CHART_COLORS.high,
            CHART_COLORS.medium,
            CHART_COLORS.low,
          ],
          borderWidth: 0,
          hoverOffset: 6,
        }]
      },
      options: {
        cutout: "70%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { family: "Inter", size: 10 }, padding: 10 }
          }
        }
      }
    });
  }

  // ── Animate score bars on load ─────────────────────────────────────────────
  const fills = document.querySelectorAll(".score-bar-fill, .component-bar-fill");
  fills.forEach((el) => {
    const target = el.style.width;
    el.style.width = "0%";
    setTimeout(() => { el.style.width = target; }, 100);
  });
});
