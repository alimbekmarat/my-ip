const PROVIDERS = [
  { url: "https://ipwho.is/", parse: d => ({ ip: d.ip, cc: d.country_code, geo: [d.city, d.country, d.connection && d.connection.isp].filter(Boolean).join(" · ") }) },
  { url: "https://ipapi.co/json/", parse: d => ({ ip: d.ip, cc: d.country_code, geo: [d.city, d.country_name, d.org].filter(Boolean).join(" · ") }) },
  { url: "https://api.ipify.org?format=json", parse: d => ({ ip: d.ip, geo: "" }) },
];

async function checkIp() {
  for (const p of PROVIDERS) {
    try {
      const c = new AbortController(); const t = setTimeout(() => c.abort(), 6000);
      const r = await fetch(p.url, { signal: c.signal, cache: "no-store" });
      clearTimeout(t);
      if (!r.ok) continue;
      const res = p.parse(await r.json());
      if (!res.ip) continue;
      const { state = {} } = await chrome.storage.local.get("state");
      const history = state.history || [];
      if (state.ip && state.ip !== res.ip) {
        chrome.notifications.create({ type: "basic", iconUrl: "icon128.png", title: "IP сменился", message: `${state.ip} → ${res.ip}` });
      }
      if (!history.length || history[0].ip !== res.ip) history.unshift({ ip: res.ip, t: Date.now() });
      const cc = res.cc || (state.ip === res.ip ? state.cc : null);
      const next = { ip: res.ip, cc, geo: res.geo || (state.ip === res.ip ? state.geo : ""), checkedAt: Date.now(), error: null, history: history.slice(0, 10) };
      await chrome.storage.local.set({ state: next });
      setBadge(res.ip, cc, false);
      return next;
    } catch (e) { /* следующий сервис */ }
  }
  const { state = {} } = await chrome.storage.local.get("state");
  const next = { ...state, checkedAt: Date.now(), error: "Нет ответа — проверь сеть" };
  await chrome.storage.local.set({ state: next });
  setBadge(null, null, true);
  return next;
}

function setBadge(ip, cc, isError) {
  // На значке — код страны (RU, NL, DE…), чтобы сразу видеть, где ты «находишься»
  const text = isError ? "!" : cc ? cc.toUpperCase() : ip ? "?" : "";
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color: isError ? "#c0392b" : cc && cc.toUpperCase() === "RU" ? "#0f7b6c" : "#2d5fd3" });
  chrome.action.setTitle({ title: ip ? `Мой IP: ${ip}${cc ? " (" + cc.toUpperCase() + ")" : ""}` : "Мой IP: нет ответа" });
}
