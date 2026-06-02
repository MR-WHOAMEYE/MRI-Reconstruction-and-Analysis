const statusText = document.getElementById("statusText");
const metadata = document.getElementById("metadata");
const runButton = document.getElementById("runButton");
const filePathSelect = document.getElementById("filePath");
const frequencyLine = document.getElementById("frequencyLine");
const frequencyArea = document.getElementById("frequencyArea");
const frequencySummary = document.getElementById("frequencySummary");

const imageIds = {
  reconstruction_url: "reconstructionImage",
  ground_truth_url: "groundTruthImage",
  kspace_url: "kspaceImage",
  frequency_spectrum_url: "frequencyImage",
  noise_removed_url: "noiseRemovedImage",
  smoothed_url: "smoothedImage",
  enhanced_url: "enhancedImage",
};

function payload() {
  return {
    file_path: document.getElementById("filePath").value,
    slice_id: Number(document.getElementById("sliceId").value),
    acceleration: Number(document.getElementById("acceleration").value),
    center_fraction: Number(document.getElementById("centerFraction").value),
    noise_removal: document.getElementById("noiseRemoval").value,
    smoothing: document.getElementById("smoothing").value,
    contrast_enhancement: document.getElementById("contrastEnhancement").value,
  };
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", isError);
}

function renderMetadata(data) {
  metadata.innerHTML = "";
  const rows = [
    ["Source", data.source_path],
    ["Slice", String(data.slice_id)],
    ["Acceleration", `${data.acceleration}x`],
    ["Center Fraction", String(data.center_fraction)],
    ["Noise Removal", data.noise_removal],
    ["Smoothing", data.smoothing],
    ["Contrast", data.contrast_enhancement],
  ];

  for (const [term, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value;
    metadata.append(dt, dd);
  }
}

function renderImages(data) {
  Object.entries(imageIds).forEach(([urlKey, elementId]) => {
    const image = document.getElementById(elementId);
    const prompt = image.nextElementSibling;
    image.hidden = true;
    prompt.hidden = false;
    image.onload = () => {
      image.hidden = false;
      prompt.hidden = true;
    };
    image.onerror = () => {
      image.hidden = true;
      prompt.hidden = false;
    };
    image.src = `${data[urlKey]}?t=${Date.now()}`;
  });
}

function populateH5Files(files, defaultFile) {
  filePathSelect.innerHTML = "";
  for (const file of files) {
    const option = document.createElement("option");
    option.value = file;
    option.textContent = file;
    if (file === defaultFile) {
      option.selected = true;
    }
    filePathSelect.append(option);
  }
}

async function loadH5Files() {
  const response = await fetch("/api/h5-files");
  const data = await response.json();
  if (!response.ok) {
    throw new Error("Failed to load H5 files");
  }
  populateH5Files(data.files, data.default);
}

function renderFrequencyGraph(profile) {
  const width = 640;
  const height = 240;
  const paddingX = 20;
  const paddingY = 20;
  const usableWidth = width - paddingX * 2;
  const usableHeight = height - paddingY * 2;

  const points = profile.y.map((value, index) => {
    const x = paddingX + (index / Math.max(profile.y.length - 1, 1)) * usableWidth;
    const y = height - paddingY - value * usableHeight;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const linePath = `M ${points.join(" L ")}`;
  const areaPath = `${linePath} L ${width - paddingX},${height - paddingY} L ${paddingX},${height - paddingY} Z`;
  frequencyLine.setAttribute("d", linePath);
  frequencyArea.setAttribute("d", areaPath);
  frequencySummary.textContent =
    `Peak energy at normalized frequency ${profile.peak_frequency.toFixed(2)} with intensity ${profile.peak_energy.toFixed(2)}.`;
}

async function runPipeline() {
  setStatus("Running MRI reconstruction and analysis...");
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload()),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Pipeline failed");
  }

  renderMetadata(data);
  renderImages(data);
  renderFrequencyGraph(data.frequency_profile);
  setStatus("Processing complete.");
}

runButton.addEventListener("click", () => {
  runPipeline().catch((error) => setStatus(error.message, true));
});

loadH5Files().catch((error) => {
  setStatus(error.message, true);
});
