importScripts("common.js");

chrome.runtime.onInstalled.addListener(() => { chrome.alarms.create("ip", { periodInMinutes: 1 }); checkIp(); });
chrome.runtime.onStartup.addListener(() => { chrome.alarms.create("ip", { periodInMinutes: 1 }); checkIp(); });
chrome.alarms.onAlarm.addListener(a => { if (a.name === "ip") checkIp(); });
chrome.runtime.onMessage.addListener((msg, _s, reply) => {
  if (msg === "check") { checkIp().then(reply); return true; }
});
