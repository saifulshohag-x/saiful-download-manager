// background.js - service worker for Saiful Download Manager extension.
// Sends link/media URLs from any webpage to the Saiful Download Manager
// desktop app via http://127.0.0.1:9527/add

const DEFAULT_PORT = 9527;

function getPort() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["port"], (res) => {
      resolve(res.port || DEFAULT_PORT);
    });
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

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "sdm-link",
    title: "Download with Saiful Download Manager",
    contexts: ["link"],
  });
  chrome.contextMenus.create({
    id: "sdm-media",
    title: "Download with Saiful Download Manager",
    contexts: ["video", "audio"],
  });
  chrome.contextMenus.create({
    id: "sdm-page",
    title: "Send page URL to Saiful Download Manager",
    contexts: ["page"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "sdm-link") {
    sendToApp(info.linkUrl, "");
  } else if (info.menuItemId === "sdm-media") {
    sendToApp(info.srcUrl || info.linkUrl || "", "");
  } else if (info.menuItemId === "sdm-page") {
    sendToApp(tab.url || info.pageUrl || "", "");
  }
});

chrome.action.onClicked.addListener((tab) => {
  if (tab && tab.url) {
    sendToApp(tab.url, "");
  }
});
