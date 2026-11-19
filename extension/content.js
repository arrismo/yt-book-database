(() => {
  const api = globalThis.browser ?? globalThis.chrome;
  const defaultEndpoint = "https://the-reading-room.mikaelmoise00.workers.dev/api/caption-match";
  const segments = [];
  const seen = new Set();
  let timer;

  function captionText() {
    return [...document.querySelectorAll(".ytp-caption-window-container .ytp-caption-segment")]
      .map((node) => node.textContent?.trim() ?? "")
      .filter(Boolean)
      .join(" ");
  }

  async function endpoint() {
    const stored = await api.storage.local.get({ endpoint: defaultEndpoint });
    return String(stored.endpoint || defaultEndpoint).replace(/\/$/, "");
  }

  async function analyze() {
    const text = captionText();
    const video = document.querySelector("video");
    if (!text || !video) return;
    const start_seconds = Math.floor(video.currentTime);
    const key = `${start_seconds}:${text}`;
    if (seen.has(key)) return;
    seen.add(key);
    segments.push({ text, start_seconds });
    if (segments.length > 8) segments.shift();

    try {
      const response = await fetch(await endpoint(), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ segments }),
      });
      if (!response.ok) return;
      const data = await response.json();
      if (Array.isArray(data.matches) && data.matches.length) {
        const current = await api.storage.local.get({ matches: [] });
        const merged = [...(Array.isArray(current.matches) ? current.matches : [])];
        for (const match of data.matches) {
          if (!merged.some((item) => item.book_id === match.book_id && item.start_seconds === match.start_seconds)) merged.push(match);
        }
        await api.storage.local.set({ matches: merged.slice(-50) });
      }
    } catch {
      // The popup reports the configured endpoint; transient network failures are ignored.
    }
  }

  const observer = new MutationObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(analyze, 250);
  });
  observer.observe(document.documentElement, { subtree: true, childList: true, characterData: true });
})();
