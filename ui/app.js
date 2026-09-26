(function () {

  const sequence = [
    "UNDERSTAND",
    "DISCOVER",
    "MODEL",
    "CONTRACT",
    "ARCHITECT",
    "HUMAN GATE",
    "IMPLEMENT",
    "TEST",
    "VERIFY",
    "REPLAY",
    "EVIDENCE",
    "HUMAN ACCEPTANCE"
  ];

  let registry;
  let dictionary;
  let fallback;
  let task;

  function resolve(obj, path) {
    return path
      .split(".")
      .reduce((value, key) => value && value[key], obj);
  }

  function t(key) {
    return resolve(dictionary, key) ||
           resolve(fallback, key) ||
           key;
  }

  
const TASK_REGISTRY_URL = "./tasks/index.json";

let taskRegistry = [];
let activeTask = null;
let activeChange = null;
let activeEvidence = null;
let activeAcceptance = null;

async function getOptionalJson(path) {
  try {
    return await getJson(path);
  } catch (error) {
    return null;
  }
}

async function loadTaskRegistry() {
  taskRegistry = await getJson(TASK_REGISTRY_URL);

  const selector = document.getElementById("taskSelector");
  if (!selector) return;

  selector.innerHTML = "";

  for (const item of taskRegistry) {
    const option = document.createElement("option");
    option.value = item.task_id;
    option.textContent =
      `${item.task_id} · ${item.title} · ${item.status}`;
    selector.appendChild(option);
  }

  selector.addEventListener("change", async (event) => {
    await loadSelectedTask(event.target.value);
  });
}

async function loadSelectedTask(taskId) {
  if (!taskRegistry.length) {
    await loadTaskRegistry();
  }

  const selected =
    taskRegistry.find((item) => item.task_id === taskId) ||
    taskRegistry[taskRegistry.length - 1];

  if (!selected) {
    throw new Error("No HDC task available for review.");
  }

  const selector = document.getElementById("taskSelector");
  if (selector) selector.value = selected.task_id;

  activeTask = await getJson(selected.task_path);

  activeChange = selected.change_path
    ? await getOptionalJson(selected.change_path)
    : null;

  activeEvidence = selected.evidence_path
    ? await getOptionalJson(selected.evidence_path)
    : null;

  activeAcceptance = selected.acceptance_path
    ? await getOptionalJson(selected.acceptance_path)
    : null;

  const title = document.getElementById("taskTitle");
  if (title) {
    title.textContent =
      `${activeTask.task_id} · ${activeTask.title}`;
  }

  window.currentTask = activeTask;
  window.currentChange = activeChange;
  window.currentEvidence = activeEvidence;
  window.currentAcceptance = activeAcceptance;

  if (typeof renderApp === "function") {
    renderApp(
      activeTask,
      activeChange,
      activeEvidence,
      activeAcceptance
    );
  }
}

async function getJson(path) {
    const response = await fetch(path, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(
        path + " returned HTTP " + response.status
      );
    }

    return response.json();
  }

  async function getText(path) {
    const response = await fetch(path, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(
        path + " returned HTTP " + response.status
      );
    }

    return response.text();
  }

  function translatePage() {
    document.querySelectorAll("[data-t]").forEach(function (node) {
      node.textContent = t(node.getAttribute("data-t"));
    });
  }

  function status(value) {
    const key = "status." + value;
    const valueTranslated = t(key);

    return valueTranslated === key
      ? String(value).toUpperCase()
      : valueTranslated;
  }

  function renderSequence() {
    const host = document.getElementById("sequence");
    host.innerHTML = "";

    /*
      Repository currently proves completion through Human Gate.
      Implementation/test/etc. are not marked complete.
    */
    const lifecycleCompleted = {
      proposed: 3,
      contracted: 4,
      gated: 6,
      implementing: 6,
      testing: 7,
      verified: 9,
      replayed: 10,
      evidenced: 11,
      awaiting_acceptance: 11,
      accepted: 12
    };

    const completed =
      lifecycleCompleted[task?.status] || 0;

    sequence.forEach(function (name, index) {

      const step = document.createElement("span");
      step.className =
        index < completed ? "step done" : "step";

      step.textContent = name;
      host.appendChild(step);

      if (index < sequence.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "arrow";
        arrow.textContent = "→";
        host.appendChild(arrow);
      }
    });
  }

  function renderTask() {
    const gate =
      task.human_gate && task.human_gate.decision
        ? task.human_gate.decision
        : "pending";

    document.getElementById("taskId").textContent =
      task.task_id;

    document.getElementById("taskStatus").textContent =
      status(task.status);

    document.getElementById("gateStatus").textContent =
      status(gate);

    document.getElementById("gatePill").textContent =
      t("dashboard.gate") + " · " + status(gate);

    document.getElementById("fieldTaskId").textContent =
      task.task_id;

    document.getElementById("fieldTitle").textContent =
      task.title;

    document.getElementById("fieldObjective").textContent =
      task.objective;

    document.getElementById("fieldGateRequired").textContent =
      String(task.human_gate_required);

    document.getElementById("fieldBeforeGate").textContent =
      String(task.implementation_allowed_before_gate);

    document.getElementById("authorityDecision").textContent =
      status(gate);

    document.getElementById("implementationAuthority").textContent =
      gate === "approved"
        ? t("authority.authorized")
        : t("status.pending");

    document.getElementById("authoritySource").textContent =
      task.human_gate && task.human_gate.record
        ? task.human_gate.record
        : "—";

    renderSequence();
  }

  async function applyLocale(locale) {
    const supported =
      registry.supported.map(function (x) {
        return x.code;
      });

    if (!supported.includes(locale)) {
      locale = registry.default;
    }

    dictionary =
      await getJson("./i18n/" + locale + ".json");

    fallback =
      await getJson(
        "./i18n/" + registry.fallback + ".json"
      );

    localStorage.setItem("aios.locale", locale);

    document.documentElement.lang = locale;
    document.getElementById("localeSelect").value = locale;

    translatePage();

    if (task) {
      renderTask();
    }
  }

  function buildLocaleSelector() {
    const select =
      document.getElementById("localeSelect");

    registry.supported.forEach(function (item) {
      const option = document.createElement("option");

      option.value = item.code;
      option.textContent = item.label;

      select.appendChild(option);
    });

    select.addEventListener("change", function () {
      applyLocale(select.value).catch(showError);
    });
  }

  function showError(error) {
    const box = document.getElementById("errorBox");

    box.style.display = "block";
    box.textContent =
      "UI load error: " + error.message;

    console.error(error);
  }

  async function start() {
    registry =
      await getJson("./i18n/locales.json");

    buildLocaleSelector();

    const saved =
      localStorage.getItem("aios.locale") ||
      registry.default;

    await applyLocale(saved);

    task =
      await loadSelectedTask();

    renderTask();

    if (task.human_gate && task.human_gate.record) {
      document.getElementById("decisionRecord").textContent =
        await getText("./" + task.human_gate.record);
    }
  }

  start().catch(showError);

})();
