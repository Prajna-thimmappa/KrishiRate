// KrishiRate frontend logic
// - All user-facing text lives in the TEXT object so Step 7 (Kannada)
//   can swap in a different language object without touching layout code.
// - Calls the same-origin FastAPI endpoints (/prices/*, /markets).
// - Uses Chart.js from CDN for the 30-day trend line chart.

const BASE = ""; // same origin as the backend

// Hardcoded starter lists for Karnataka.
const CROPS = ["Arecanut", "Coconut", "Rubber", "Paddy"];
const DISTRICTS = [
  "Dakshina Kannada",
  "Udupi",
  "Chikkamagaluru",
  "Hassan",
  "Kodagu",
  "Belagavi",
];

// All UI text in one place for easy translation (Step 7).
const LANGUAGES = {
  en: {
    title: "KrishiRate",
    subtitle: "Today's Mandi Prices",
    crop: "Crop",
    district: "District",
    market: "Market (Mandi)",
    refresh: "Refresh Prices",
    compare: "Compare Markets",
    language: "Language",
    modal: "Modal Price",
    min: "Minimum Price",
    max: "Maximum Price",
    unit: "/quintal",
    trend: "30-Day Price Trend",
    loading: "Loading prices...",
    noData: "No price data found for this selection.",
    error: "Error loading prices. Please try again.",
    footer: "Data source: data.gov.in (Agmarknet) &middot; Falls back to sample data when offline",
    datePrefix: "Data as of",
    compareHeading: "Market Comparison",
    compareDatePrefix: "Data as of",
    alertHeading: "Set Price Alert",
    alertChatId: "Telegram Chat ID",
    alertCrop: "Crop",
    alertDistrict: "District",
    alertMarket: "Market (Mandi) - optional",
    alertTargetPrice: "Target Price (/quintal)",
    alertCondition: "Condition",
    alertAbove: "Price goes above target",
    alertBelow: "Price goes below target",
    alertSetBtn: "Set Alert",
    alertCreated: "Alert created successfully.",
    alertError: "Error setting alert. Please try again.",
  },
  kn: {
    title: "ಕೃಷಿರೇಟ್",
    subtitle: "ಇಂದಿನ ಮಂಡಿ ಬೆಲೆಗಳು",
    crop: "ಪಯರು",
    district: "ಜಿಲ್ಲೆ",
    market: "ಮಾರುಕಟ್ಟೆ (ಮಂಡಿ)",
    refresh: "ಬೆಲೆಗಳನ್ನು ನವೀಕರಿಸಿ",
    compare: "ಮಾರುಕಟ್ಟೆಗಳ ಹೋಲಿಕೆ",
    language: "ಭಾಷೆ",
    modal: "ಮಾಧ್ಯಮ ಬೆಲೆ",
    min: "ಕನಿಷ್ಠ ಬೆಲೆ",
    max: "ಅಧಿಕ ಬೆಲೆ",
    unit: "/ಕ್ವಿಂಟಲ್",
    trend: "30-ದಿನ ಬೆಲೆ ಪ್ರವೃತ್ತಿ",
    loading: "ಬೆಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...",
    noData: "ಈ ಆಯ್ಕೆಗೆ ಬೆಲೆ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ.",
    error: "ಬೆಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡುವಲ್ಲಿ ದೋಷ. ದಯವಿಟ್ಟು ಮರುಪ್ರಯತ್ನಿಸಿ.",
    footer: "ಡೇಟಾ ಮೂಲ: data.gov.in (Agmarknet) · ಓರ್ಫೈನ್ ಆಗಿದ್ದಾಗ ಸ್ಯಾಂಪಲ್ ಡೇಟಾ",
    datePrefix: "ಡೇಟಾ ಎಂದು",
    compareHeading: "ಮಾರುಕಟ್ಟೆಗಳ ಹೋಲಿಕೆ",
    compareDatePrefix: "ಡೇಟಾ ಎಂದು",
    alertHeading: "ಬೆಲೆ ಎಚ್ಚರಿಕೆ ನಿಗಧಿ",
    alertChatId: "ಟೆಲಿಗ್ರામ ಚಾಟ್ ಐಡಿ",
    alertCrop: "ಪಯರು",
    alertDistrict: "ಜಿಲ್ಲೆ",
    alertMarket: "ಮಾರುಕಟ್ಟೆ (ಮಂಡಿ) - alternate",
    alertTargetPrice: "ಗುರಿ ಬೆಲೆ (/ಕ್ವಿಂಟಲ್)",
    alertCondition: "ಸ್ಥಿತಿ",
    alertAbove: "ಬೆಲೆ ಗುರಿಯನ್ನು ದಾಟಿದಾಗ",
    alertBelow: "ಬೆಲೆ ಗುರಕ್ಕಿಂತ ಕೆಳಗೆ ಇದ್ದಾಗ",
    alertSetBtn: "ನಿಗಧಿ",
    alertCreated: "ಎಚ್ಚರಿಕೆ ಯಶಸ್ವಿಯಾಗಿ ನಿಗಧಿಗೆ yhtyeಿತು.",
    alertError: "ಎಚ್ಚರಿಕೆಯನ್ನು ನಿಗಧಿಗೊಳುವುದರಲ್ಲಿ ದೋಷ. ದಯವಿಟ್ಟು ಮರುಪ್ರಯತ್ನಿಸಿ.",
  },
};

let currentLang = localStorage.getItem("krishi_lang") || "en";
let TEXT = LANGUAGES[currentLang];

function setLang(lang) {
  currentLang = lang;
  TEXT = LANGUAGES[lang];
  localStorage.setItem("krishi_lang", lang);
  const sel = $("lang");
  if (sel) sel.value = lang;
  applyText();
}

let trendChart = null;

// Tiny DOM helper.
function $(id) {
  return document.getElementById(id);
}

// Apply all UI text from the TEXT object.
function applyText() {
  const h1 = document.querySelector("header h1");
  const sub = document.querySelector("header p");
  if (h1) h1.textContent = TEXT.title;
  if (sub) sub.textContent = TEXT.subtitle;

  const langLabel = document.querySelector('label[for="lang"]');
  if (langLabel) langLabel.textContent = TEXT.language;

  const cropLabel = document.querySelector('label[for="crop"]');
  const districtLabel = document.querySelector('label[for="district"]');
  const marketLabel = document.querySelector('label[for="market"]');
  if (cropLabel) cropLabel.textContent = TEXT.crop;
  if (districtLabel) districtLabel.textContent = TEXT.district;
  if (marketLabel) marketLabel.textContent = TEXT.market;

  const refreshBtn = $("refreshBtn");
  if (refreshBtn) refreshBtn.textContent = TEXT.refresh;

  const compareBtn = $("compareBtn");
  if (compareBtn) compareBtn.textContent = TEXT.compare;

  // Card labels.
  const cardLabels = document.querySelectorAll(".price-card .card-label");
  if (cardLabels[0]) cardLabels[0].textContent = TEXT.modal;
  if (cardLabels[1]) cardLabels[1].textContent = TEXT.min;
  if (cardLabels[2]) cardLabels[2].textContent = TEXT.max;

  // Unit labels.
  const units = document.querySelectorAll(".card-unit");
  units.forEach((u) => (u.textContent = TEXT.unit));

  const chartHeading = document.querySelector(".chart-section h2");
  if (chartHeading) chartHeading.textContent = TEXT.trend;

  const compareHeading = $("compareHeading");
  if (compareHeading) compareHeading.textContent = TEXT.compareHeading;

  // Table headers.
  const thMarket = $("thMarket");
  const thModal = $("thModal");
  const thMin = $("thMin");
  const thMax = $("thMax");
  if (thMarket) thMarket.textContent = TEXT.market;
  if (thModal) thModal.textContent = TEXT.modal;
  if (thMin) thMin.textContent = TEXT.min;
  if (thMax) thMax.textContent = TEXT.max;

  // Alert form labels.
  const alertHeading = $("alertHeading");
  if (alertHeading) alertHeading.textContent = TEXT.alertHeading;
  const alertChatLabel = document.querySelector('label[for="alertChatId"]');
  const alertCropLabel = document.querySelector('label[for="alertCrop"]');
  const alertDistrictLabel = document.querySelector('label[for="alertDistrict"]');
  const alertMarketLabel = document.querySelector('label[for="alertMarket"]');
  const alertTargetLabel = document.querySelector('label[for="alertTargetPrice"]');
  const alertConditionLabel = document.querySelector('label[for="alertCondition"]');
  if (alertChatLabel) alertChatLabel.textContent = TEXT.alertChatId;
  if (alertCropLabel) alertCropLabel.textContent = TEXT.alertCrop;
  if (alertDistrictLabel) alertDistrictLabel.textContent = TEXT.alertDistrict;
  if (alertMarketLabel) alertMarketLabel.textContent = TEXT.alertMarket;
  if (alertTargetLabel) alertTargetLabel.textContent = TEXT.alertTargetPrice;
  if (alertConditionLabel) alertConditionLabel.textContent = TEXT.alertCondition;
  const alertSubmitBtn = $("alertSubmitBtn");
  if (alertSubmitBtn) alertSubmitBtn.textContent = TEXT.alertSetBtn;
  const alertConditionSel = $("alertCondition");
  if (alertConditionSel) {
    alertConditionSel.options[0].textContent = TEXT.alertAbove;
    alertConditionSel.options[1].textContent = TEXT.alertBelow;
  }

  $("status").textContent = TEXT.loading;
  $("emptyMsg").textContent = TEXT.noData;

  const footer = document.querySelector("footer p");
  if (footer) footer.innerHTML = TEXT.footer;
}

// Populate the crop dropdown.
function populateCrops() {
  const sel = $("crop");
  CROPS.forEach((c) => {
    const o = document.createElement("option");
    o.value = c;
    o.textContent = c;
    sel.appendChild(o);
  });
}

// Populate the district dropdown.
function populateDistricts() {
  const sel = $("district");
  DISTRICTS.forEach((d) => {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d;
    sel.appendChild(o);
  });
}

// Populate the alert form crop dropdown.
function populateAlertCrops() {
  const sel = $("alertCrop");
  if (!sel) return;
  CROPS.forEach((c) => {
    const o = document.createElement("option");
    o.value = c;
    o.textContent = c;
    sel.appendChild(o);
  });
}

// Populate the alert form district dropdown.
function populateAlertDistricts() {
  const sel = $("alertDistrict");
  if (!sel) return;
  DISTRICTS.forEach((d) => {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d;
    sel.appendChild(o);
  });
}

// Fetch markets for a district from /markets?district=.
async function loadMarkets(district) {
  const sel = $("market");
  sel.innerHTML = '<option value="">' + TEXT.market + "</option>";
  sel.disabled = true;

  try {
    const res = await fetch(`${BASE}/markets?district=${encodeURIComponent(district)}`);
    if (!res.ok) throw new Error("failed to load markets");
    const data = await res.json();
    (data.markets || []).forEach((m) => {
      const o = document.createElement("option");
      o.value = m.market;
      o.textContent = m.market + (m.state ? " (" + m.state + ")" : "");
      sel.appendChild(o);
    });
  } catch (err) {
    console.error("markets load error", err);
  } finally {
    sel.disabled = false;
  }
}

// Fetch markets for a district for the alert form.
async function loadAlertMarkets(district) {
  const sel = $("alertMarket");
  if (!sel) return;
  sel.innerHTML = '<option value="">' + TEXT.alertMarket + "</option>";
  try {
    const res = await fetch(`${BASE}/markets?district=${encodeURIComponent(district)}`);
    if (!res.ok) throw new Error("failed to load markets");
    const data = await res.json();
    (data.markets || []).forEach((m) => {
      const o = document.createElement("option");
      o.value = m.market;
      o.textContent = m.market + (m.state ? " (" + m.state + ")" : "");
      sel.appendChild(o);
    });
  } catch (err) {
    console.error("alert markets load error", err);
  }
}

// Show/hide UI states.
function showLoading(show) {
  $("status").hidden = !show;
  $("todaySection").hidden = true;
  $("chartSection").hidden = true;
  $("compareSection").hidden = true;
  $("emptyMsg").hidden = true;
}

function showToday(data) {
  $("status").hidden = true;
  $("todaySection").hidden = false;
  $("chartSection").hidden = false;
  $("compareSection").hidden = true;
  $("emptyMsg").hidden = true;

  $("dataDate").textContent = TEXT.datePrefix + " " + data.date;

  const first = (data.prices || [])[0];
  const fmt = (v) => (v == null ? "N/A" : v.toString());
  $("modalValue").textContent = "\u20B9" + fmt(first && first.modal_price);
  $("minValue").textContent = "\u20B9" + fmt(first && first.min_price);
  $("maxValue").textContent = "\u20B9" + fmt(first && first.max_price);
}

function showEmpty() {
  $("status").hidden = true;
  $("todaySection").hidden = true;
  $("chartSection").hidden = true;
  $("compareSection").hidden = true;
  $("emptyMsg").hidden = false;
}

function showCompare(data) {
  $("status").hidden = true;
  $("todaySection").hidden = true;
  $("chartSection").hidden = true;
  $("compareSection").hidden = false;
  $("emptyMsg").hidden = true;

  $("compareDate").textContent = TEXT.compareDatePrefix + " " + data.date;

  const body = $("compareBody");
  body.innerHTML = "";
  const markets = data.markets || [];
  if (!markets.length) {
    showEmpty();
    return;
  }
  markets.forEach((m) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + escapeHtml(m.market) + "</td>" +
      "<td>" + (m.modal_price == null ? "N/A" : "\u20B9" + m.modal_price) + "</td>" +
      "<td>" + (m.min_price == null ? "N/A" : "\u20B9" + m.min_price) + "</td>" +
      "<td>" + (m.max_price == null ? "N/A" : "\u20B9" + m.max_price) + "</td>";
    body.appendChild(tr);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function showError(msg) {
  $("status").textContent = msg || TEXT.error;
  $("status").hidden = false;
  $("todaySection").hidden = true;
  $("chartSection").hidden = true;
  $("emptyMsg").hidden = true;
}

// Render the 30-day trend line chart with Chart.js.
function renderTrend(prices) {
  const ctx = $("trendChart").getContext("2d");

  if (trendChart) {
    trendChart.destroy();
  }

  const labels = (prices || []).map((p) => p.date);
  const values = (prices || []).map((p) => p.modal_price);

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Modal Price",
          data: values,
          borderColor: "#2e7d32",
          backgroundColor: "rgba(46, 125, 50, 0.15)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          title: { display: true, text: "\u20B9 / quintal" },
        },
        x: {
          title: { display: true, text: "Date" },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { mode: "index", intersect: false },
      },
    },
  });
}

// Fetch today's prices and the 30-day trend for crop+district+market.
async function loadPrices(crop, district, market) {
  if (!crop || !district || !market) {
    showEmpty();
    return;
  }

  showLoading(true);

  try {
    const todayRes = await fetch(
      `${BASE}/prices/today?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}&market=${encodeURIComponent(market)}`
    );
    if (todayRes.status === 404) {
      showEmpty();
      return;
    }
    if (!todayRes.ok) throw new Error("today fetch failed");
    const today = await todayRes.json();

    const trendRes = await fetch(
      `${BASE}/prices/trend?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&days=30`
    );
    if (trendRes.status === 404) {
      showToday(today);
      renderTrend([]);
      return;
    }
    if (!trendRes.ok) throw new Error("trend fetch failed");
    const trend = await trendRes.json();

    showToday(today);
    renderTrend(trend.prices || []);
  } catch (err) {
    console.error("price load error", err);
    showError(TEXT.error);
  }
}

// Fetch market comparison for a crop+district and render the comparison table.
async function loadCompare(crop, district) {
  if (!crop || !district) {
    showEmpty();
    return;
  }
  showLoading(true);
  try {
    const res = await fetch(
      `${BASE}/prices/compare?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}`
    );
    if (res.status === 404) {
      showEmpty();
      return;
    }
    if (!res.ok) throw new Error("compare fetch failed");
    const data = await res.json();
    showCompare(data);
  } catch (err) {
    console.error("compare load error", err);
    showError(TEXT.error);
  }
}

// Show a feedback message under the alert form.
function showAlertMsg(text, type) {
  const msg = $("alertMsg");
  if (!msg) return;
  msg.textContent = text;
  msg.className = "status-msg " + (type === "ok" ? "ok" : "err");
  msg.hidden = false;
  setTimeout(() => (msg.hidden = true), 5000);
}

// Create a price alert via POST /alerts.
async function setAlert(formData) {
  const msg = $("alertMsg");
  try {
    const res = await fetch(`${BASE}/alerts`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });
    if (res.status === 422) {
      const body = await res.json();
      showAlertMsg(body.detail || TEXT.alertError, "err");
      return;
    }
    if (!res.ok) throw new Error("alert create failed");
    await res.json();
    showAlertMsg(TEXT.alertCreated, "ok");
    $("alertForm").reset();
  } catch (err) {
    console.error("alert create error", err);
    showAlertMsg(TEXT.alertError, "err");
  }
}

// Wire up dropdowns and refresh button.
function setupListeners() {
  const cropSel = $("crop");
  const districtSel = $("district");
  const marketSel = $("market");
  const refreshBtn = $("refreshBtn");

  // Reload markets when district changes.
  districtSel.addEventListener("change", async () => {
    await loadMarkets(districtSel.value);
    loadPrices(cropSel.value, districtSel.value, marketSel.value);
  });

  // Re-fetch when crop or market changes.
  cropSel.addEventListener("change", () => {
    loadPrices(cropSel.value, districtSel.value, marketSel.value);
  });
  marketSel.addEventListener("change", () => {
    loadPrices(cropSel.value, districtSel.value, marketSel.value);
  });

  // Restore persisted language and wire up the toggle.
  const langSel = $("lang");
  if (langSel) {
    langSel.value = currentLang;
    langSel.addEventListener("change", () => {
      setLang(langSel.value);
    });
  }

  // Compare Markets re-fetches the comparison table for the current crop+district.
  const compareBtn = $("compareBtn");
  if (compareBtn) {
    compareBtn.addEventListener("click", () => {
      loadCompare(cropSel.value, districtSel.value);
    });
  }

  // Set Alert form: reload alert markets when district changes, then submit.
  const alertDistrictSel = $("alertDistrict");
  const alertMarketSel = $("alertMarket");
  const alertForm = $("alertForm");
  if (alertDistrictSel && alertMarketSel && alertForm) {
    alertDistrictSel.addEventListener("change", async () => {
      await loadAlertMarkets(alertDistrictSel.value);
    });
    alertForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const formData = new URLSearchParams();
      formData.append("chat_id", $("alertChatId").value);
      formData.append("crop", $("alertCrop").value);
      formData.append("district", alertDistrictSel.value);
      formData.append("target_price", $("alertTargetPrice").value);
      formData.append("condition", $("alertCondition").value);
      if (alertMarketSel.value) {
        formData.append("market", alertMarketSel.value);
      }
      setAlert(formData);
    });
  }

  // Manual refresh re-fetches prices (and markets for the current district).
  refreshBtn.addEventListener("click", async () => {
    await loadMarkets(districtSel.value);
    loadPrices(cropSel.value, districtSel.value, marketSel.value);
  });
}

// Boot up.
document.addEventListener("DOMContentLoaded", () => {
  applyText();
  populateCrops();
  populateDistricts();
  populateAlertCrops();
  populateAlertDistricts();
  setupListeners();

  const cropSel = $("crop");
  const districtSel = $("district");
  loadMarkets(districtSel.value).then(() => {
    loadPrices(cropSel.value, districtSel.value, $("market").value);
  });
  loadAlertMarkets($("alertDistrict").value);
});
