const $ = id => document.getElementById(id);
const fmt = t => new Date(t).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });

function render(s = {}) {
  $("ip").textContent = s.ip || "—";
  $("geo").textContent = s.geo || "";
  $("err").textContent = s.error || "";
  $("meta").textContent = s.checkedAt ? `Проверено ${fmt(s.checkedAt)} · автопроверка раз в минуту` : "Автопроверка раз в минуту";
  const box = $("hist"); box.textContent = "";
  (s.history || []).slice(1, 6).forEach(h => {
    const row = document.createElement("div");
    const a = document.createElement("span"); a.textContent = h.ip;
    const b = document.createElement("span"); b.textContent = fmt(h.t);
    row.append(a, b); box.append(row);
  });
  if (box.childElementCount) box.insertAdjacentHTML("afterbegin", '<div class="label" style="border:0">Прошлые IP</div>');
}

async function refresh() {
  $("btn").disabled = true; $("btn").textContent = "Проверяю…";
  render(await chrome.runtime.sendMessage("check"));
  $("btn").disabled = false; $("btn").textContent = "Проверить сейчас";
}

async function copy() {
  const ip = $("ip").textContent; if (ip === "—") return;
  await navigator.clipboard.writeText(ip); $("copy").textContent = "Готово";
  setTimeout(() => $("copy").textContent = "Копировать", 1500);
}

$("btn").onclick = refresh; $("copy").onclick = copy; $("ip").onclick = copy;
chrome.storage.local.get("state").then(({ state }) => { render(state); if (!state) refresh(); });
chrome.storage.onChanged.addListener(ch => { if (ch.state) render(ch.state.newValue); });
