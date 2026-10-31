/* Click (or Enter on) a Mermaid diagram to open it full screen, with zoom and pan.
   Wheel or pinch zooms around the pointer, drag pans, double click or "0" fits, "+" and "-" zoom, Esc or a click
   outside the diagram closes, and the focus goes back to the diagram.

   Material for MkDocs draws every diagram into a *closed* shadow root of its `div.mermaid`, where no other script
   reaches the SVG. This file opens those shadow roots instead, so it must run before Material draws: it is a classic
   script written in <head> by overrides/main.html, ahead of Material's bundle, on the pages that have a diagram.
   Nothing is loaded from outside. The texts follow the page's language (`<html lang>`). */
(function () {
  "use strict";

  const attachShadow = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (init) {
    if (this.classList && this.classList.contains("mermaid")) init = Object.assign({}, init, { mode: "open" });
    return attachShadow.call(this, init);
  };

  const TEXTS = {
    en: {
      diagram: "Diagram: open full screen, with zoom",
      hint: "Click to open full screen, with zoom",
      dialog: "Enlarged diagram",
      zoomIn: "Zoom in (+)",
      zoomOut: "Zoom out (-)",
      fit: "Fit to screen (0)",
      close: "Close (Esc)",
      help: "wheel or pinch to zoom · drag to move · double click to fit · Esc to close",
    },
    it: {
      diagram: "Diagramma: apri a schermo intero, con lo zoom",
      hint: "Clic per aprire a schermo intero, con lo zoom",
      dialog: "Diagramma ingrandito",
      zoomIn: "Ingrandisci (+)",
      zoomOut: "Riduci (-)",
      fit: "Adatta allo schermo (0)",
      close: "Chiudi (Esc)",
      help: "rotella o pizzico per lo zoom · trascina per spostare · doppio clic per adattare · Esc per chiudere",
    },
    fr: {
      diagram: "Diagramme : ouvrir en plein écran, avec zoom",
      hint: "Cliquer pour ouvrir en plein écran, avec zoom",
      dialog: "Diagramme agrandi",
      zoomIn: "Agrandir (+)",
      zoomOut: "Réduire (-)",
      fit: "Ajuster à l'écran (0)",
      close: "Fermer (Échap)",
      help: "molette ou pincement pour zoomer · glisser pour déplacer · double clic pour ajuster · Échap pour fermer",
    },
    es: {
      diagram: "Diagrama: abrir a pantalla completa, con zoom",
      hint: "Clic para abrir a pantalla completa, con zoom",
      dialog: "Diagrama ampliado",
      zoomIn: "Ampliar (+)",
      zoomOut: "Reducir (-)",
      fit: "Ajustar a la pantalla (0)",
      close: "Cerrar (Esc)",
      help: "rueda o pellizco para el zoom · arrastra para mover · doble clic para ajustar · Esc para cerrar",
    },
  };

  /** The texts of the page's language; English for any other. */
  function t() {
    const lang = (document.documentElement.lang || "en").toLowerCase().split("-")[0];
    return TEXTS[lang] || TEXTS.en;
  }

  const MIN = 0.1, MAX = 12;
  let overlay = null, stage = null, viewport = null, state = null;

  function button(action, label, glyph) {
    return '<button type="button" data-dz="' + action + '" title="' + label + '" aria-label="' + label + '">' + glyph + "</button>";
  }

  function build() {
    overlay = document.createElement("div");
    overlay.className = "dz-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    const text = t();
    overlay.setAttribute("aria-label", text.dialog);
    overlay.innerHTML =
      '<div class="dz-bar">' +
      button("in", text.zoomIn, "+") +
      button("out", text.zoomOut, "\u2212") +
      button("fit", text.fit, "\u2922") +
      button("close", text.close, "\u2715") +
      "</div>" +
      '<div class="dz-viewport"><div class="dz-stage"></div></div>' +
      '<div class="dz-hint"></div>';
    overlay.querySelector(".dz-hint").textContent = text.help;
    stage = overlay.querySelector(".dz-stage");
    viewport = overlay.querySelector(".dz-viewport");

    overlay.querySelector(".dz-bar").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      const r = viewport.getBoundingClientRect();
      if (b.dataset.dz === "in") zoomAt(r.width / 2, r.height / 2, 1.25);
      else if (b.dataset.dz === "out") zoomAt(r.width / 2, r.height / 2, 0.8);
      else if (b.dataset.dz === "fit") fit();
      else close();
    });
    // A click closes only when the press began outside the diagram (the pointer capture makes every click target the viewport)
    viewport.addEventListener("click", () => { if (state.pressedOutside && !state.moved) close(); });
    viewport.addEventListener("dblclick", (e) => { e.preventDefault(); fit(); });
    viewport.addEventListener("wheel", (e) => {
      e.preventDefault();
      const r = viewport.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015));
    }, { passive: false });

    const pts = new Map();
    let last = null;
    viewport.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 && e.pointerType === "mouse") return;
      viewport.setPointerCapture(e.pointerId);
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      state.moved = false;
      state.pressedOutside = !e.target.closest(".dz-stage");
      last = snapshot(pts);
    });
    viewport.addEventListener("pointermove", (e) => {
      if (!pts.has(e.pointerId)) return;
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const now = snapshot(pts);
      if (last && now.n === last.n) {
        const r = viewport.getBoundingClientRect();
        if (Math.abs(now.cx - last.cx) + Math.abs(now.cy - last.cy) > 2) state.moved = true;
        state.x += now.cx - last.cx;
        state.y += now.cy - last.cy;
        if (now.n === 2 && last.d > 0) zoomAt(now.cx - r.left, now.cy - r.top, now.d / last.d, true);
        apply();
      }
      last = now;
    });
    const up = (e) => { pts.delete(e.pointerId); last = snapshot(pts); };
    viewport.addEventListener("pointerup", up);
    viewport.addEventListener("pointercancel", up);

    document.addEventListener("keydown", (e) => {
      if (!overlay.classList.contains("open")) return;
      const r = viewport.getBoundingClientRect();
      if (e.key === "Tab") {
        // Focus stays on the four buttons while the view is open
        const buttons = [...overlay.querySelectorAll(".dz-bar button")];
        const at = buttons.indexOf(document.activeElement);
        buttons[(at + (e.shiftKey ? buttons.length - 1 : 1)) % buttons.length].focus();
      } else if (e.key === "Escape") close();
      else if (e.key === "+" || e.key === "=") zoomAt(r.width / 2, r.height / 2, 1.25);
      else if (e.key === "-") zoomAt(r.width / 2, r.height / 2, 0.8);
      else if (e.key === "0") fit();
      else return;
      e.preventDefault();
    });
  }

  function snapshot(pts) {
    const p = [...pts.values()];
    if (!p.length) return null;
    const cx = p.reduce((s, q) => s + q.x, 0) / p.length;
    const cy = p.reduce((s, q) => s + q.y, 0) / p.length;
    const d = p.length === 2 ? Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) : 0;
    return { n: p.length, cx, cy, d };
  }

  function apply() {
    stage.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.k})`;
  }

  /** Zoom by factor around the viewport point (px, py), keeping that point still. */
  function zoomAt(px, py, factor, noApply) {
    const k = Math.min(MAX, Math.max(MIN, state.k * factor));
    const f = k / state.k;
    state.x = px - (px - state.x) * f;
    state.y = py - (py - state.y) * f;
    state.k = k;
    if (!noApply) apply();
  }

  function fit() {
    const r = viewport.getBoundingClientRect();
    if (!r.width || !r.height) return requestAnimationFrame(fit);  // not laid out yet: the next frame
    const k = Math.min((r.width * 0.95) / state.w, (r.height * 0.95) / state.h);
    state.k = Math.min(MAX, Math.max(MIN, k));
    state.x = (r.width - state.w * state.k) / 2;
    state.y = (r.height - state.h * state.k) / 2;
    apply();
  }

  function open(svg, opener) {
    if (!overlay) build();
    (document.fullscreenElement || document.body).appendChild(overlay);
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const box = svg.getBoundingClientRect();
    const w = vb && vb.width ? vb.width : box.width;
    const h = vb && vb.height ? vb.height : box.height;
    const clone = svg.cloneNode(true);
    clone.removeAttribute("style");
    clone.setAttribute("width", w);
    clone.setAttribute("height", h);
    stage.replaceChildren(clone);
    state = { w, h, k: 1, x: 0, y: 0, moved: false, opener };
    overlay.classList.add("open");
    document.documentElement.classList.add("dz-lock");
    fit();
    overlay.querySelector('[data-dz="close"]').focus();
  }

  function close() {
    overlay.classList.remove("open");
    document.documentElement.classList.remove("dz-lock");
    stage.replaceChildren();
    if (state && state.opener && state.opener.focus) state.opener.focus();
  }

  /** The SVG Material drew for a diagram, now that its shadow root is open. */
  function svgOf(host) {
    return host.shadowRoot ? host.shadowRoot.querySelector("svg") : host.querySelector("svg");
  }

  document.addEventListener("click", (e) => {
    const host = e.target.closest("div.mermaid");
    if (!host || e.target.closest("a")) return;
    const svg = svgOf(host);
    if (svg) open(svg, host);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const host = e.target.closest && e.target.closest("div.mermaid");
    const svg = host && svgOf(host);
    if (!svg) return;
    e.preventDefault();
    open(svg, host);
  });

  // Every diagram can be reached with the keyboard, and says what a click does.
  new MutationObserver(() => {
    for (const host of document.querySelectorAll("div.mermaid:not([tabindex])")) {
      host.setAttribute("tabindex", "0");
      host.setAttribute("role", "button");
      host.setAttribute("aria-label", t().diagram);
      host.setAttribute("title", t().hint);
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
