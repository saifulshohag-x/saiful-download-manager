// background.js - Firefox background script for Saiful Download Manager.
// Uses browser.* APIs (Firefox) but falls back to chrome.* for compatibility.

const DEFAULT_PORT = 9527;

function getPort() {
  return new Promise((resolve) => {
    if (typeof browser !== "undefined") {
      browser.storage.local.get(["port"]).then((res) => {
        resolve(res.port || DEFAULT_PORT);
      });
    } else {
      chrome.storage.local.get(["port"], (res) => {
        resolve(res.port || DEFAULT_PORT);
      });
    }
  });
}

async function sendToApp(url, filename = "") {
  const port = await getPort();
  const endpoint = `http://127.0.0.1:${port}/add`;
  try {
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, filename: filename }),
    });
    const data = await resp.json();
    if (data.ok) {
      console.log("[Saiful DM] added:", data.file_name);
    } else {
      console.error("[Saiful DM] error:", data.error);
    }
  } catch (e) {
    console.error("[Saiful DM] cannot reach app:", e);
  }
}

// Install context menus
const api = typeof browser !== "undefined" ? browser : chrome;
api.runtime.onInstalled.addListener(() => {
  api.contextMenus.create({
    id: "sdm-link",
    title: "Download with Saiful Download Manager",
    contexts: ["link"],
  });
  api.contextMenus.create({
    id: "sdm-media",
    title: "Download with Saiful Download Manager",
    contexts: ["video", "audio"],
  });
  api.contextMenus.create({
    id: "sdm-page",
    title: "Send page URL to Saiful Download Manager",
    contexts: ["page"],
  });
});

api.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "sdm-link") {
    sendToApp(info.linkUrl, "");
  } else if (info.menuItemId === "sdm-media") {
    sendToApp(info.srcUrl || info.linkUrl || "", "");
  } else if (info.menuItemId === "sdm-page") {
    sendToApp(tab.url || info.pageUrl || "", "");
  }
});

if (api.browserAction && api.browserAction.onClicked) {
  api.browserAction.onClicked.addListener((tab) => {
    if (tab && tab.url) {
      sendToApp(tab.url, "");
    }
  });
}
