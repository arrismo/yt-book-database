(() => {
  const api = globalThis.browser ?? globalThis.chrome;
  const endpoint = document.querySelector("#endpoint");
  const status = document.querySelector("#status");
  const matches = document.querySelector("#matches");

  async function render() {
    const stored = await api.storage.local.get({ endpoint: "", matches: [] });
    endpoint.value = stored.endpoint;
    matches.replaceChildren();
    if (!stored.matches.length) {
      matches.innerHTML = '<p class="empty">Turn on captions and watch a YouTube video. Book matches will appear here.</p>';
      return;
    }
    for (const match of stored.matches.slice().reverse()) {
      const item = document.createElement("div");
      item.className = "match";
      item.innerHTML = `<strong></strong><small></small>`;
      item.querySelector("strong").textContent = match.title;
      item.querySelector("small").textContent = `${match.author} · ${Math.floor(match.start_seconds / 60)}:${String(match.start_seconds % 60).padStart(2, "0")} · ${match.evidence_excerpt}`;
      matches.append(item);
    }
  }

  document.querySelector("#save").addEventListener("click", async () => {
    const value = endpoint.value.trim().replace(/\/$/, "");
    await api.storage.local.set({ endpoint: value });
    status.textContent = value ? "Endpoint saved." : "Enter the Worker endpoint first.";
  });
  document.querySelector("#clear").addEventListener("click", async () => {
    await api.storage.local.set({ matches: [] });
    render();
  });
  render();
})();
