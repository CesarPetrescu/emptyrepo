const $ = (selector) => document.querySelector(selector);
const list = $("#asset-list");
const template = $("#asset-item-template");
const viewer = $("#model-viewer");
const search = $("#search");

const state = {
  catalog: null,
  visible: [],
  selected: 0,
  rotating: true,
};

const formatNumber = (value) => new Intl.NumberFormat("en-US").format(value);
const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "UNKNOWN" : date.toISOString().slice(0, 10);
};

function selectAsset(asset, index) {
  state.selected = state.catalog.assets.indexOf(asset);
  const items = [...list.querySelectorAll(".asset-item")];
  items.forEach((item) => {
    const selected = item.dataset.slug === asset.slug;
    item.classList.toggle("selected", selected);
    item.setAttribute("aria-selected", String(selected));
  });

  viewer.style.opacity = "0.2";
  viewer.src = asset.files.glb;
  viewer.poster = asset.files.preview;
  viewer.alt = `Interactive 3D preview of ${asset.name}`;
  viewer.setAttribute("camera-orbit", "42deg 68deg auto");
  viewer.setAttribute("camera-target", "auto auto auto");

  $("#asset-category").textContent = asset.category.toUpperCase();
  $("#asset-category").style.color = asset.accent;
  $("#asset-name").textContent = asset.name;
  $("#asset-description").textContent = asset.description;
  $("#asset-index").textContent = `${String(state.selected + 1).padStart(2, "0")} / ${String(state.catalog.assets.length).padStart(2, "0")}`;
  $("#stat-triangles").textContent = formatNumber(asset.stats.triangles);
  $("#stat-vertices").textContent = formatNumber(asset.stats.vertices);
  $("#stat-size").textContent = asset.dimensionsStuds.map((value) => Number(value).toFixed(1)).join(" × ");
  $("#stat-materials").textContent = String(asset.stats.materials).padStart(2, "0");
  $("#download-glb").href = asset.files.glb;
  $("#download-fbx").href = asset.files.fbx;

  const tags = $("#use-tags");
  tags.replaceChildren(...asset.robloxUse.map((text) => {
    const tag = document.createElement("span");
    tag.textContent = text;
    return tag;
  }));
}

function renderList(assets) {
  state.visible = assets;
  list.replaceChildren();
  $("#result-count").textContent = `${assets.length} ITEM${assets.length === 1 ? "" : "S"}`;
  if (!assets.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "NO ASSETS MATCH THIS FILTER";
    list.append(empty);
    return;
  }

  for (const asset of assets) {
    const item = template.content.firstElementChild.cloneNode(true);
    item.dataset.slug = asset.slug;
    item.style.setProperty("--asset-accent", asset.accent);
    item.querySelector("img").src = asset.files.preview;
    item.querySelector("img").alt = `${asset.name} rendered preview`;
    item.querySelector("strong").textContent = asset.name;
    item.querySelector("small").textContent = asset.category;
    item.querySelector(".asset-tris").textContent = `${formatNumber(asset.stats.triangles)} △`;
    item.addEventListener("click", () => selectAsset(asset));
    item.addEventListener("keydown", (event) => {
      if (!["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      const current = assets.indexOf(asset);
      const next = assets[(current + direction + assets.length) % assets.length];
      selectAsset(next);
      list.querySelector(`[data-slug="${next.slug}"]`)?.focus();
    });
    list.append(item);
  }

  const selected = state.catalog.assets[state.selected];
  if (assets.some((asset) => asset.slug === selected?.slug)) {
    selectAsset(selected);
  } else {
    selectAsset(assets[0]);
  }
}

async function loadCatalog() {
  try {
    const response = await fetch("catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
    state.catalog = await response.json();
    const { pack, assets } = state.catalog;
    $("#asset-total").textContent = String(assets.length).padStart(2, "0");
    $("#blender-version").textContent = `BLENDER ${pack.blenderVersion}`;
    $("#build-date").textContent = formatDate(pack.generatedAt);
    $("#download-bundle").href = pack.bundle;
    $("#build-state").textContent = `BUILD ${pack.version} READY`;
    renderList(assets);
  } catch (error) {
    console.error(error);
    $("#build-state").textContent = "CATALOG LOAD FAILED";
    list.innerHTML = `<p class="empty-state">THE GENERATED CATALOG COULD NOT BE LOADED.<br>OPEN THIS PAGE THROUGH HTTP, NOT FILE://.</p>`;
    $("#asset-description").textContent = "The asset build exists, but the browser could not read catalog.json.";
  }
}

search.addEventListener("input", () => {
  if (!state.catalog) return;
  const query = search.value.trim().toLowerCase();
  const filtered = state.catalog.assets.filter((asset) => {
    const haystack = [asset.name, asset.category, asset.description, ...asset.robloxUse].join(" ").toLowerCase();
    return haystack.includes(query);
  });
  renderList(filtered);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== search) {
    event.preventDefault();
    search.focus();
  }
  if (event.key === "Escape" && document.activeElement === search) {
    search.value = "";
    search.blur();
    search.dispatchEvent(new Event("input"));
  }
});

$("#rotate-toggle").addEventListener("click", (event) => {
  state.rotating = !state.rotating;
  viewer.toggleAttribute("auto-rotate", state.rotating);
  event.currentTarget.classList.toggle("active", state.rotating);
  event.currentTarget.setAttribute("aria-pressed", String(state.rotating));
});

$("#reset-view").addEventListener("click", () => {
  viewer.cameraOrbit = "42deg 68deg auto";
  viewer.cameraTarget = "auto auto auto";
  viewer.fieldOfView = "auto";
  viewer.jumpCameraToGoal();
});

$("#compact-toggle").addEventListener("click", () => {
  $(".browser-panel").classList.toggle("compact");
});

viewer.addEventListener("progress", (event) => {
  $("#load-progress").style.width = `${Math.round(event.detail.totalProgress * 100)}%`;
});
viewer.addEventListener("load", () => {
  viewer.style.opacity = "1";
  $("#load-progress").style.width = "100%";
  window.setTimeout(() => { $("#load-progress").style.width = "0"; }, 450);
});
viewer.addEventListener("error", (event) => {
  console.error("Model viewer error", event.detail);
  viewer.style.opacity = "1";
});

loadCatalog();
