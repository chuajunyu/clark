const TRAY_KEY = "clark-a4-tray-v2";

function readTray() {
  try {
    const value = JSON.parse(sessionStorage.getItem(TRAY_KEY) || "[]");
    return Array.isArray(value) ? [...new Set(value.filter((item) => typeof item === "string" && item))] : [];
  } catch (_) {
    return [];
  }
}

function writeTray(ids) {
  sessionStorage.setItem(TRAY_KEY, JSON.stringify([...new Set(ids)]));
  updateNavCount();
}

function addToTray(voucherId) {
  const ids = readTray();
  if (!ids.includes(voucherId)) ids.push(voucherId);
  writeTray(ids);
  return ids.length;
}

function updateNavCount() {
  const count = readTray().length;
  const badge = document.querySelector("#nav-tray-count");
  if (badge) {
    badge.textContent = String(count);
    badge.hidden = count === 0;
  }
}

function escapeText(value) {
  const node = document.createElement("span");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

function smallNumberWords(number) {
  const ones = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
  const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
  if (number < 0) return `Minus ${smallNumberWords(Math.abs(number))}`;
  if (number < 20) return ones[number];
  if (number < 100) return tens[Math.floor(number / 10)] + (number % 10 ? `-${ones[number % 10]}` : "");
  if (number < 1000) return `${ones[Math.floor(number / 100)]} Hundred${number % 100 ? ` ${smallNumberWords(number % 100)}` : ""}`;
  if (number < 1000000) return `${smallNumberWords(Math.floor(number / 1000))} Thousand${number % 1000 ? ` ${smallNumberWords(number % 1000)}` : ""}`;
  return String(number);
}

function initialiseEditor() {
  const form = document.querySelector("#voucher-form");
  if (!form) return;
  const state = document.querySelector("#save-state");
  const statusText = state?.querySelector(".status-text");
  const warning = document.querySelector("#amount-warning");
  let dirty = false;
  let submitting = false;

  function setDirty() {
    if (dirty) return;
    dirty = true;
    state?.classList.add("is-dirty");
    if (statusText) statusText.textContent = "Unsaved changes";
  }

  function updateAmountPreview() {
    const inputs = [...form.querySelectorAll(".line-amount")];
    let total = 0;
    const invalidRows = [];
    let hasAmount = false;
    inputs.forEach((input, index) => {
      const raw = input.value.trim();
      const parsed = Number(raw.replaceAll(",", ""));
      hasAmount ||= raw !== "";
      input.closest(".amount-cell").querySelector(".line-currency").classList.toggle("is-hidden", raw === "");
      input.classList.toggle("invalid-amount", raw !== "" && !Number.isFinite(parsed));
      if (raw !== "" && Number.isFinite(parsed)) total += parsed;
      if (raw !== "" && !Number.isFinite(parsed)) invalidRows.push(index + 1);
    });
    document.querySelector(".total-currency")?.classList.toggle("is-hidden", !hasAmount);
    const totalOutput = document.querySelector("#amount-total");
    const wordsOutput = document.querySelector("#amount-words");
    if (totalOutput) totalOutput.textContent = hasAmount ? total.toFixed(2) : "";
    if (wordsOutput) {
      const dollars = Math.floor(total);
      const cents = Math.round((total - dollars) * 100);
      wordsOutput.textContent = hasAmount ? `${smallNumberWords(dollars)} Dollars${cents ? ` and ${smallNumberWords(cents)} Cents` : ""} Only` : "";
    }
    if (warning) {
      warning.hidden = invalidRows.length === 0;
      warning.textContent = invalidRows.length ? `Amount row${invalidRows.length === 1 ? "" : "s"} ${invalidRows.join(", ")} will print as entered but will not be included in the total.` : "";
    }
  }

  form.addEventListener("input", () => {
    setDirty();
    updateAmountPreview();
  });
  form.addEventListener("submit", () => { submitting = true; });
  window.addEventListener("beforeunload", (event) => {
    if (!dirty || submitting) return;
    event.preventDefault();
    event.returnValue = "";
  });
  updateAmountPreview();

  const trayAddId = document.querySelector(".editor-workspace")?.dataset.trayAddId;
  if (trayAddId) addToTray(trayAddId);
}

function initialiseSavedList() {
  const toast = document.querySelector("#page-toast");
  document.querySelectorAll(".add-saved-to-tray").forEach((button) => {
    button.addEventListener("click", () => {
      const count = addToTray(button.dataset.voucherId);
      button.textContent = "Added to A4 tray";
      button.disabled = true;
      if (toast) {
        toast.hidden = false;
        toast.textContent = `Voucher added. ${count} voucher${count === 1 ? "" : "s"} now in the A4 tray.`;
      }
    });
  });
}

async function initialiseTrayPage() {
  const page = document.querySelector("#a4-tray-page");
  if (!page) return;
  const list = document.querySelector("#full-tray-list");
  const empty = document.querySelector("#full-tray-empty");
  const summary = document.querySelector("#tray-summary");
  const hidden = document.querySelector("#voucher-ids-json");
  const preview = document.querySelector("#preview-a4");

  async function render() {
    let ids = readTray();
    if (!ids.length) {
      list.innerHTML = "";
      empty.hidden = false;
      summary.textContent = "0 vouchers selected";
      hidden.value = "[]";
      preview.disabled = true;
      return;
    }
    const response = await fetch(`/api/vouchers/summaries?ids=${encodeURIComponent(ids.join(","))}`);
    const payload = await response.json();
    const vouchers = payload.vouchers || [];
    const foundIds = new Set(vouchers.map((voucher) => voucher.id));
    ids = ids.filter((id) => foundIds.has(id));
    writeTray(ids);
    list.innerHTML = vouchers.map((voucher, index) => `
      <article class="full-tray-item">
        <span class="tray-position">${index + 1}</span>
        <div><strong>${escapeText(voucher.voucher_number || "Untitled voucher")}</strong><span>${escapeText(voucher.payee || "No payee entered")}</span></div>
        <div class="tray-item-meta"><span>${escapeText(voucher.voucher_date || "No date")}</span><strong>$${escapeText(voucher.amount)}</strong></div>
        <a href="/vouchers/${encodeURIComponent(voucher.id)}/view">View</a>
        <button type="button" class="remove-tray-item" data-id="${escapeText(voucher.id)}">Remove</button>
      </article>
    `).join("");
    empty.hidden = vouchers.length > 0;
    hidden.value = JSON.stringify(ids);
    preview.disabled = ids.length === 0;
    summary.textContent = `${ids.length} voucher${ids.length === 1 ? "" : "s"} selected - ${Math.ceil(ids.length / 2)} A4 page${ids.length <= 2 ? "" : "s"}`;
  }

  list.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-tray-item");
    if (!button) return;
    writeTray(readTray().filter((id) => id !== button.dataset.id));
    render();
  });
  document.querySelector("#clear-tray")?.addEventListener("click", () => { writeTray([]); render(); });
  await render();
}

updateNavCount();
initialiseEditor();
initialiseSavedList();
initialiseTrayPage();
