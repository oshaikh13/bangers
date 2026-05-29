const state = {
  run: null,
  tab: "goals",
  manifest: null,
  selection: null,
  listCollapsed: false,
  detailCollapsed: false,
};

const layout = document.getElementById("layout");
const runSelect = document.getElementById("run-select");
const listHeader = document.getElementById("list-header");
const detailHeader = document.getElementById("detail-header");
const itemList = document.getElementById("item-list");
const detailContent = document.getElementById("detail-content");
const toggleListPane = document.getElementById("toggle-list-pane");
const toggleDetailPane = document.getElementById("toggle-detail-pane");
const tabs = document.querySelectorAll(".tab");

init();

async function init() {
  bindEvents();
  updateLayoutClasses();
  await loadRuns();
  parseHash();
  await refreshCurrentTab();
}

function bindEvents() {
  runSelect.addEventListener("change", async () => {
    state.run = runSelect.value;
    state.selection = null;
    await loadManifest();
    await refreshCurrentTab();
    updateHash();
  });

  toggleListPane.addEventListener("click", () => {
    state.listCollapsed = !state.listCollapsed;
    updateLayoutClasses();
  });

  toggleDetailPane.addEventListener("click", () => {
    state.detailCollapsed = !state.detailCollapsed;
    updateLayoutClasses();
  });

  tabs.forEach((tab) => {
    tab.addEventListener("click", async () => {
      setActiveTab(tab.dataset.tab);
      state.selection = null;
      detailHeader.textContent = "";
      await refreshCurrentTab();
      updateHash();
    });
  });

  window.addEventListener("hashchange", async () => {
    parseHash();
    setActiveTab(state.tab, false);
    await refreshCurrentTab();
  });
}

async function loadRuns() {
  const data = await fetchJson("/api/runs");
  runSelect.innerHTML = "";

  if (!data.runs.length) {
    runSelect.innerHTML = `<option value="">No discovery runs found</option>`;
    state.run = null;
    detailContent.innerHTML =
      `<p class="empty-state">No discovery_* directories found in the repo root.</p>`;
    return;
  }

  for (const run of data.runs) {
    const option = document.createElement("option");
    option.value = run.name;
    const goalLabel =
      run.goal_count === 1 ? "1 goal" : `${run.goal_count} goals`;
    option.textContent = `${run.name} (${goalLabel})`;
    runSelect.appendChild(option);
  }

  state.run = data.default_run || data.runs[0].name;
  runSelect.value = state.run;
  await loadManifest();
}

async function loadManifest() {
  if (!state.run) {
    state.manifest = null;
    return;
  }
  state.manifest = await fetchJson(`/api/runs/${encodeURIComponent(state.run)}/manifest`);
}

function setActiveTab(tabName, updateButtons = true) {
  state.tab = tabName;
  updateLayoutClasses();
  if (!updateButtons) {
    return;
  }
  tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
}

function updateLayoutClasses() {
  layout.classList.toggle("list-collapsed", state.listCollapsed);
  layout.classList.toggle("detail-collapsed", state.detailCollapsed);
  toggleListPane.textContent = state.listCollapsed ? "›" : "‹";
  toggleDetailPane.textContent = state.detailCollapsed ? "‹" : "›";
}

async function refreshCurrentTab() {
  if (!state.run) {
    return;
  }

  if (state.tab === "goals") {
    await renderGoalsTab();
  } else if (state.tab === "combined") {
    await renderCombinedTab();
  } else if (state.tab === "bangers") {
    await renderBangersTab();
  } else if (state.tab === "questions") {
    await renderQuestionsTab();
  }
}

async function renderGoalsTab() {
  const manifest = state.manifest;
  listHeader.textContent = `${manifest.counts.goals} goal files`;
  detailHeader.textContent = "Select a goal file";
  itemList.innerHTML = "";

  if (!manifest.stages.goals) {
    detailContent.innerHTML = `<p class="empty-state">No goals found for this run.</p>`;
    return;
  }

  for (const item of manifest.goals) {
    itemList.appendChild(
      createListButton(
        item.path,
        `Interval ${item.interval_index}`,
        `goals/${item.interval_index}`,
        state.selection === `goals/${item.interval_index}`,
      ),
    );
  }

  const selected = state.selection || `goals/${manifest.goals[0]?.interval_index}`;
  if (selected?.startsWith("goals/")) {
    await loadGoalFile(selected.slice("goals/".length));
  }
}

async function loadGoalFile(intervalIndex) {
  state.selection = `goals/${intervalIndex}`;
  markActiveSelection();
  const data = await fetchJson(
    `/api/runs/${encodeURIComponent(state.run)}/goals/${intervalIndex}`,
  );

  detailHeader.textContent = `goal_${intervalIndex}.json · ${data.goals.length} goals`;
  detailContent.innerHTML = "";

  data.goals.forEach((goal, index) => {
    detailContent.appendChild(
      createCollapsibleCard(
        `#${index + 1} ${goal.goal || "Untitled goal"}`,
        `
          <div class="badge-row">
            <span class="badge">Usefulness ${goal.usefulness ?? "?"}</span>
            <span class="badge">Confidence ${goal.confidence ?? "?"}</span>
          </div>
          ${field("Description", goal.description)}
          ${field("Context", goal.context)}
          ${field("Reasoning", goal.reasoning)}
          ${field("Execution timestamp", goal.execution_timestamp)}
        `,
      ),
    );
  });
}

async function renderCombinedTab() {
  const manifest = state.manifest;
  const combinedPath = manifest.combined_path || "combined.json";
  listHeader.textContent = "1 combined file";
  detailHeader.textContent = combinedPath;
  itemList.innerHTML = "";

  if (!manifest.stages.combined) {
    detailContent.innerHTML = `<p class="empty-state">No combined.json found for this run.</p>`;
    return;
  }

  const fileSelected =
    state.selection === "combined/file" || state.selection?.startsWith("combined/");
  itemList.appendChild(
    createListButton(
      combinedPath,
      `${manifest.counts.combined} combined goals`,
      "combined/file",
      fileSelected,
    ),
  );

  if (!state.selection?.startsWith("combined/")) {
    state.selection = "combined/file";
  }

  const openIndex = combinedSelectionIndex(state.selection);
  await loadCombinedFile(openIndex);
}

function combinedSelectionIndex(selection) {
  if (!selection?.startsWith("combined/")) {
    return null;
  }
  const id = selection.slice("combined/".length);
  if (id === "file") {
    return null;
  }
  return id;
}

async function loadCombinedFile(openIndex = null) {
  state.selection =
    openIndex === null ? "combined/file" : `combined/${openIndex}`;
  markActiveSelection();
  const data = await fetchJson(`/api/runs/${encodeURIComponent(state.run)}/combined`);

  detailHeader.textContent = `${state.manifest.combined_path || "combined.json"} · ${data.items.length} combined goals`;
  detailContent.innerHTML = "";

  data.items.forEach((item, index) => {
    const manifestItem = state.manifest.combined.find(
      (entry) => entry.combined_index === index,
    );
    const card = createCollapsibleCard(
      item.combined || `Combined ${index}`,
      `
        <div class="badge-row"><span class="badge">Index ${index}</span></div>
        <div class="field">
          <span class="field-label">Source goals</span>
          <ul class="source-list">
            ${(item.goals || [])
              .map(
                (goal) =>
                  `<li><strong>${escapeHtml(goal.name || "Untitled")}</strong> · ${escapeHtml(goal.time || "unknown time")}</li>`,
              )
              .join("")}
          </ul>
        </div>
        <div class="link-row">
          ${manifestItem?.has_banger ? `<button class="link-button" data-link="bangers/${index}">View bangers</button>` : ""}
          ${
            manifestItem?.question_ids?.length
              ? `<button class="link-button" data-link="questions/${manifestItem.question_ids[0]}">View questions</button>`
              : ""
          }
        </div>
      `,
      openIndex !== null && String(openIndex) === String(index),
    );
    card.dataset.combinedIndex = String(index);
    detailContent.appendChild(card);
  });

  bindLinkButtons(detailContent);

  if (openIndex !== null) {
    detailContent
      .querySelector(`[data-combined-index="${openIndex}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }
}

async function renderBangersTab() {
  const manifest = state.manifest;
  listHeader.textContent = `${manifest.counts.bangers} banger files`;
  detailHeader.textContent = "Select a banger";
  itemList.innerHTML = "";

  if (!manifest.stages.bangers) {
    detailContent.innerHTML = `<p class="empty-state">No banger files found for this run.</p>`;
    return;
  }

  for (const item of manifest.bangers) {
    const combinedItem = state.manifest.combined.find(
      (entry) => entry.combined_index === item.combined_index,
    );
    itemList.appendChild(
      createListButton(
        combinedItem?.combined || `Banger ${item.combined_index}`,
        item.path,
        `bangers/${item.combined_index}`,
        state.selection === `bangers/${item.combined_index}`,
      ),
    );
  }

  const selected = state.selection || `bangers/${manifest.bangers[0]?.combined_index}`;
  if (selected?.startsWith("bangers/")) {
    await loadBangerDetail(selected.split("/")[1]);
  }
}

async function loadBangerDetail(combinedIndex) {
  state.selection = `bangers/${combinedIndex}`;
  markActiveSelection();
  detailHeader.textContent = "Banger opportunities";
  const data = await fetchJson(
    `/api/runs/${encodeURIComponent(state.run)}/bangers/${combinedIndex}`,
  );
  const manifestItem = state.manifest.combined.find(
    (entry) => entry.combined_index === Number(combinedIndex),
  );

  detailContent.innerHTML = "";
  detailContent.appendChild(
    createCollapsibleCard(
      manifestItem?.combined || `Banger ${combinedIndex}`,
      `
        <div class="badge-row"><span class="badge">Combined index ${combinedIndex}</span></div>
        <div class="link-row">
          <button class="link-button" data-link="combined/${combinedIndex}">View combined</button>
          ${
            manifestItem?.question_ids?.length
              ? `<button class="link-button" data-link="questions/${manifestItem.question_ids[0]}">View questions</button>`
              : ""
          }
        </div>
      `,
      true,
    ),
  );
  bindLinkButtons(detailContent);

  for (const goalGroup of data.banger.goals || []) {
    for (const [index, opportunity] of (goalGroup.opportunities || []).entries()) {
      detailContent.appendChild(
        renderOpportunityCard(goalGroup.goal, opportunity, index, combinedIndex),
      );
    }
  }
}

function renderOpportunityCard(goalName, opportunity, index, combinedIndex) {
  const manifestItem = state.manifest.combined.find(
    (entry) => entry.combined_index === Number(combinedIndex),
  );
  const questionId = manifestItem?.question_ids?.[index];

  const card = createCollapsibleCard(
    `${goalName || "Goal"} · ${opportunity.suggestion || `Opportunity ${index}`}`,
    `
      <div class="badge-row"><span class="badge">${escapeHtml(opportunity.timestamp || "No timestamp")}</span></div>
      ${field("Suggestion", opportunity.suggestion)}
      ${field("Action", opportunity.action)}
      ${field("Why now", opportunity.why_now)}
      ${field("Expected artifact", opportunity.expected_artifact)}
      ${field("Trigger evidence", (opportunity.trigger_evidence || []).join("\n"))}
      <div class="link-row">
        ${questionId ? `<button class="link-button" data-link="questions/${questionId}">View questions</button>` : ""}
      </div>
    `,
  );
  bindLinkButtons(card);
  return card;
}

async function renderQuestionsTab() {
  const manifest = state.manifest;
  listHeader.textContent = `${manifest.counts.questions} question sets`;
  detailHeader.textContent = "Select a question set";
  itemList.innerHTML = "";

  if (!manifest.stages.questions) {
    detailContent.innerHTML = `<p class="empty-state">No question files found for this run.</p>`;
    return;
  }

  for (const item of manifest.questions) {
    itemList.appendChild(
      createListButton(
        item.suggestion_title || item.question_id,
        `combined ${item.combined_index} · goal ${item.goal_index} · opp ${item.opportunity_index}`,
        `questions/${item.question_id}`,
        state.selection === `questions/${item.question_id}`,
      ),
    );
  }

  const selected = state.selection || `questions/${manifest.questions[0]?.question_id}`;
  if (selected?.startsWith("questions/")) {
    await loadQuestionDetail(selected.slice("questions/".length));
  }
}

async function loadQuestionDetail(questionId) {
  state.selection = `questions/${questionId}`;
  markActiveSelection();
  detailHeader.textContent = "Question set details";
  const data = await fetchJson(
    `/api/runs/${encodeURIComponent(state.run)}/questions/${encodeURIComponent(questionId)}`,
  );
  const questions = data.questions || {};
  const threads = questions.threads || [];
  const totalPairs = threads.reduce(
    (sum, thread) => sum + (thread.qa_pairs?.length || 0),
    0,
  );

  detailContent.innerHTML = "";
  detailContent.appendChild(
    createCollapsibleCard(
      questions.suggestion_title || questionId,
      `
        <div class="badge-row">
          <span class="badge">${threads.length} threads</span>
          <span class="badge">${totalPairs} Q/A pairs</span>
        </div>
        <div class="link-row">
          <button class="link-button" data-link="combined/${data.combined_index}">View combined</button>
          <button class="link-button" data-link="bangers/${data.combined_index}">View bangers</button>
        </div>
      `,
      true,
    ),
  );
  bindLinkButtons(detailContent);

  threads.forEach((thread, threadIndex) => {
    const pairs = thread.qa_pairs || [];
    const threadHeader = document.createElement("h3");
    threadHeader.className = "thread-header";
    threadHeader.textContent = `Thread ${thread.thread_id ?? threadIndex} · ${pairs.length} Q/A pairs`;
    detailContent.appendChild(threadHeader);
    pairs.forEach((pair, index) => {
      detailContent.appendChild(
        createCollapsibleCard(
          `Q${pair.q_id ?? index}. ${pair.question || `Q/A ${index + 1}`}`,
          `
            <div class="badge-row"><span class="badge">Difficulty ${pair.question_difficulty ?? "?"}</span></div>
            ${field("Answer", pair.answer)}
            ${field("Why it matters", pair.why_it_matters)}
          `,
          true,
        ),
      );
    });
  });
}

function createCollapsibleCard(title, bodyHtml, open = false) {
  const details = document.createElement("details");
  details.className = "collapsible-card";
  details.open = open;
  details.innerHTML = `
    <summary>${escapeHtml(title)}</summary>
    <div class="collapsible-card-body">${bodyHtml}</div>
  `;
  return details;
}

function createListButton(title, meta, selectionKey, active) {
  const li = document.createElement("li");
  const button = document.createElement("button");
  button.className = `item-button${active ? " active" : ""}`;
  button.dataset.selection = selectionKey;
  button.innerHTML = `
    <span class="title">${escapeHtml(title)}</span>
    <span class="meta">${escapeHtml(meta)}</span>
  `;
  button.addEventListener("click", async () => {
    state.selection = selectionKey;
    await refreshCurrentTab();
    updateHash();
  });
  li.appendChild(button);
  return li;
}

function markActiveSelection() {
  itemList.querySelectorAll(".item-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.selection === state.selection);
  });
}

function bindLinkButtons(root) {
  root.querySelectorAll("[data-link]").forEach((button) => {
    button.addEventListener("click", async () => {
      const link = button.dataset.link;
      const slash = link.indexOf("/");
      const tab = link.slice(0, slash);
      const id = link.slice(slash + 1);
      setActiveTab(tab);
      state.selection = `${tab}/${id}`;
      await refreshCurrentTab();
      updateHash();
    });
  });
}

function parseHash() {
  const hash = window.location.hash.replace(/^#/, "");
  if (!hash) {
    return;
  }
  const slash = hash.indexOf("/");
  if (slash === -1) {
    if (["goals", "combined", "bangers", "questions"].includes(hash)) {
      state.tab = hash;
      state.selection = null;
    }
    return;
  }
  const tab = hash.slice(0, slash);
  const id = hash.slice(slash + 1);
  if (["goals", "combined", "bangers", "questions"].includes(tab)) {
    state.tab = tab;
    state.selection = `${tab}/${id}`;
  }
}

function updateHash() {
  const next = state.selection || state.tab;
  if (`#${next}` !== window.location.hash) {
    window.location.hash = next;
  }
}

function field(label, value) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  return `
    <div class="field">
      <span class="field-label">${escapeHtml(label)}</span>
      <div class="field-value">${escapeHtml(String(value))}</div>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}
