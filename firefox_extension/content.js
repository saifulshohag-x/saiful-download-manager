// content.js - Saiful Download Manager content script
//
// Adds a floating "Download" button on top of every <video>, <audio>, <embed>,
// and <object> element on every page. Also detects direct download links
// (matching file extensions) and shows a small floating "Download with SDM"
// button next to them.
//
// Sends the URL to the desktop app via http://127.0.0.1:9527/add

(function () {
  "use strict";

  const DEFAULT_PORT = 9527;
  const DOWNLOAD_EXTS = [
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".msi", ".apk", ".dmg", ".deb", ".rpm",
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".mpg", ".mpeg",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    ".iso", ".bin", ".csv", ".json", ".xml"
  ];

  function getPort() {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get(["port"], (res) => {
          resolve(res && res.port ? res.port : DEFAULT_PORT);
        });
      } catch (e) {
        resolve(DEFAULT_PORT);
      }
    });
  }

  async function sendToApp(url, filename) {
    const port = await getPort();
    try {
      const resp = await fetch(`http://127.0.0.1:${port}/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url, filename: filename || "" }),
      });
      const data = await resp.json();
      if (data && data.ok) {
        console.log("[SDM] Added:", data.file_name);
        return true;
      } else {
        console.error("[SDM] Error:", data && data.error);
      }
    } catch (e) {
      console.error("[SDM] Cannot reach app:", e);
      showToast("Saiful Download Manager not running. Please start the app.");
    }
    return false;
  }

  // Floating toast notification
  function showToast(message, durationMs) {
    durationMs = durationMs || 3000;
    let toast = document.createElement("div");
    toast.className = "sdm-toast";
    toast.textContent = message;
    document.documentElement.appendChild(toast);
    // Force reflow then add visible class
    void toast.offsetWidth;
    toast.classList.add("sdm-toast-visible");
    setTimeout(function () {
      toast.classList.remove("sdm-toast-visible");
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, durationMs);
  }

  // ----------------------------------------------------------------------
  // Video / audio overlay button
  // ----------------------------------------------------------------------
  function makeOverlayButton(mediaEl) {
    if (mediaEl.getAttribute("data-sdm-overlay")) return; // already done
    mediaEl.setAttribute("data-sdm-overlay", "1");
    const btn = document.createElement("div");
    btn.className = "sdm-video-btn";
    btn.innerHTML = "⬇ SDM";
    btn.title = "Download with Saiful Download Manager";

    // Position relative to the media element
    function positionBtn() {
      const rect = mediaEl.getBoundingClientRect();
      if (rect.width < 100 || rect.height < 60) {
        btn.style.display = "none";
        return;
      }
      btn.style.display = "block";
      btn.style.top = (window.scrollY + rect.top + 8) + "px";
      btn.style.left = (window.scrollX + rect.left + 8) + "px";
    }
    positionBtn();
    document.documentElement.appendChild(btn);

    // Re-position on scroll / resize / media load
    window.addEventListener("scroll", positionBtn, { passive: true });
    window.addEventListener("resize", positionBtn);
    if (mediaEl.readyState) positionBtn();
    mediaEl.addEventListener("loadedmetadata", positionBtn);

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      let url = mediaEl.currentSrc || mediaEl.src ||
                (mediaEl.querySelector("source") &&
                 mediaEl.querySelector("source").src) || "";
      if (!url && window.location.href) {
        // Try to grab currentFrame URL
        url = window.location.href;
      }
      if (url) {
        sendToApp(url, "");
        showToast("Added to Saiful Download Manager");
      } else {
        showToast("No video URL found");
      }
    });

    // Hide if media leaves viewport (best effort)
    const observer = new MutationObserver(function () {
      if (!document.contains(mediaEl)) {
        if (btn.parentNode) btn.parentNode.removeChild(btn);
        observer.disconnect();
      } else {
        positionBtn();
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  // ----------------------------------------------------------------------
  // Direct download link overlay (links to .zip/.pdf/.mp4 etc.)
  // ----------------------------------------------------------------------
  function makeLinkButton(linkEl) {
    if (linkEl.getAttribute("data-sdm-link")) return;
    const href = linkEl.href || "";
    if (!href) return;
    let ext = "";
    try {
      const u = new URL(href, window.location.href);
      const path = u.pathname.toLowerCase();
      const dot = path.lastIndexOf(".");
      if (dot >= 0) ext = path.substring(dot);
    } catch (e) { return; }
    if (DOWNLOAD_EXTS.indexOf(ext) < 0) return;

    linkEl.setAttribute("data-sdm-link", "1");
    const btn = document.createElement("a");
    btn.href = "#";
    btn.className = "sdm-link-btn";
    btn.innerHTML = "⬇";
    btn.title = "Download with Saiful Download Manager";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      sendToApp(href, "");
      showToast("Added to Saiful Download Manager");
    });
    // Insert button right after the link
    if (linkEl.parentNode) {
      linkEl.parentNode.insertBefore(btn, linkEl.nextSibling);
    }
  }

  // ----------------------------------------------------------------------
  // Scan page for media and download links
  // ----------------------------------------------------------------------
  function scanPage() {
    try {
      // Video / audio / embed / object
      const medias = document.querySelectorAll(
        "video, audio, object, embed, [data-hls-src], [data-video-src]"
      );
      medias.forEach(makeOverlayButton);
      // Downloadable links
      const links = document.querySelectorAll("a[href]");
      links.forEach(makeLinkButton);
    } catch (e) {
      console.error("[SDM] scan error:", e);
    }
  }

  // Initial scan
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scanPage);
  } else {
    scanPage();
  }
  // Re-scan periodically to catch dynamically-added videos
  setInterval(scanPage, 3000);
  // Also re-scan on major DOM mutations
  const mo = new MutationObserver(function () { scanPage(); });
  mo.observe(document.documentElement, { childList: true, subtree: true });
})();
