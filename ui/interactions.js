function syncCheckpoint([scene, items]) {
  let state = window.__bobberyCheckpoint;
  if (!state) {
    state = window.__bobberyCheckpoint = {};
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.altKey ||
          event.metaKey || event.isComposing || event.target.tagName !== "TEXTAREA") return;
      const bar = event.target.closest(".st-key-response_bar");
      if (!bar) return;
      event.preventDefault();
      const button = bar.querySelector("button:not(:disabled)");
      if (button && event.target.value.trim() && !state.submitting) {
        state.submitting = true;
        const target = event.target;
        setTimeout(() => {
          state.submitting = false;
          const liveButton = bar.querySelector("button:not(:disabled)");
          if (liveButton && target.value.trim()) liveButton.click();
        }, 10);
      }
    }, true);

    const hide = () => {
      state.hovered = null;
      if (state.tip) state.tip.style.opacity = "0";
    };
    document.addEventListener("pointerover", (event) => {
      const pick = event.target.closest?.('[class*="st-key-pick_"]');
      if (!pick || pick === state.hovered) return;
      const id = pick.className.match(/st-key-pick_([A-Za-z0-9_-]+)/)?.[1];
      const info = state.items[id];
      if (!info || pick.querySelector('button[data-testid^="stBaseButton-primary"]')) {
        hide();
        return;
      }
      state.hovered = pick;
      if (!state.tip) {
        state.tip = document.createElement("div");
        state.tip.id = "bobbery-item-tooltip";
        document.body.appendChild(state.tip);
      }
      const tip = state.tip;
      const title = document.createElement("strong");
      title.textContent = info.header || id;
      tip.replaceChildren(title);
      for (const line of String(info.lines || "").split("\n").filter(Boolean)) {
        const row = document.createElement("div");
        row.textContent = line;
        tip.appendChild(row);
      }
      const rect = pick.getBoundingClientRect();
      const width = tip.offsetWidth, height = tip.offsetHeight;
      const left = rect.left - width - 12;
      tip.style.left = (left < 12 ? Math.min(innerWidth - width - 12, rect.right + 12) : left) + "px";
      tip.style.top = Math.max(12, Math.min(innerHeight - height - 12, rect.top + (rect.height - height) / 2)) + "px";
      tip.style.opacity = "1";
    }, { passive: true });
    document.addEventListener("pointerout", (event) => {
      if (state.hovered && !state.hovered.contains(event.relatedTarget)) hide();
    }, { passive: true });
    document.addEventListener("pointerdown", hide, { passive: true });
    window.addEventListener("scroll", hide, { capture: true, passive: true });
  }
  if (state.scene && state.scene !== scene) {
    const veil = document.createElement("div");
    veil.id = "bobbery-scene-veil";
    document.getElementById(veil.id)?.remove();
    document.body.appendChild(veil);
    veil.animate([{ opacity: 0.78 }, { opacity: 0 }], { duration: 460, easing: "ease-out" })
      .onfinish = () => veil.remove();
  }
  state.scene = scene;
  state.items = items;
}
