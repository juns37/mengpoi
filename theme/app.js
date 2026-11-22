(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const body = document.body, root = document.documentElement, BASE = body.dataset.base || "";
  const store = (k, v) => { try { return v === undefined ? localStorage.getItem(k) : (v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v)); } catch (e) { return null; } };

  // app bar elevation on scroll
  const onScroll = () => body.classList.toggle("scrolled", scrollY > 4);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();

  // theme: auto -> opposite of system -> auto
  $(".theme")?.addEventListener("click", () => {
    const sysDark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = root.dataset.theme || (sysDark ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    if ((next === "dark") === sysDark) { delete root.dataset.theme; store("theme", null); }
    else { root.dataset.theme = next; store("theme", next); }
  });

  // modal drawer
  const closeNav = () => body.classList.remove("nav-open");
  $(".menu")?.addEventListener("click", () => body.classList.toggle("nav-open"));
  $(".scrim")?.addEventListener("click", closeNav);
  addEventListener("keydown", e => e.key === "Escape" && closeNav());
  $(".nav-item.on")?.scrollIntoView({ block: "center" });

  // copy code
  $$(".code .copy").forEach(b => b.addEventListener("click", async () => {
    const t = b.parentElement.querySelector("code").innerText;
    try { await navigator.clipboard.writeText(t); }
    catch (e) { const a = Object.assign(document.createElement("textarea"), { value: t }); document.body.append(a); a.select(); document.execCommand("copy"); a.remove(); }
    const ic = b.querySelector(".ms"); b.classList.add("done"); ic.textContent = "check";
    setTimeout(() => { b.classList.remove("done"); ic.textContent = "content_copy"; }, 1400);
  }));

  // lightbox
  const lb = $(".lightbox");
  $$(".prose figure img").forEach(img => img.addEventListener("click", () => {
    if (!lb?.showModal) return;
    $("img", lb).src = img.currentSrc || img.src; lb.showModal();
  }));
  lb?.addEventListener("click", () => lb.close());

  // toc scroll spy
  const toc = $$(".toc a");
  if (toc.length) {
    const map = new Map(toc.map(a => [decodeURIComponent(a.hash.slice(1)), a]));
    const hs = [...map.keys()].map(id => document.getElementById(id)).filter(Boolean);
    const spy = () => {
      let cur = hs[0];
      for (const h of hs) if (h.getBoundingClientRect().top < 120) cur = h;
      toc.forEach(a => a.classList.remove("on")); map.get(cur?.id)?.classList.add("on");
    };
    addEventListener("scroll", spy, { passive: true }); spy();
  }

  // search
  const dlg = $(".search"), inp = $(".search input"), res = $(".search-res");
  let idx = null, sel = 0;
  const norm = s => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const escH = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const mark = (s, terms) => { let h = escH(s); terms.forEach(t => { if (t) h = h.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"); }); return h; };
  const run = () => {
    const q = norm(inp.value.trim());
    if (!idx) return;
    if (!q) { res.innerHTML = idx.map(p => `<a href="${p.u}"><strong>${escH(p.t)}</strong><small>${escH(p.s)}</small></a>`).join(""); sel = 0; hi(); return; }
    const terms = q.split(/\s+/);
    const hits = idx.map(p => {
      const t = norm(p.t), x = norm(p.x); let sc = 0;
      for (const w of terms) { if (t.includes(w)) sc += 10; else if (x.includes(w)) sc += 1; else return null; }
      const i = x.indexOf(terms[0]); const snip = i < 0 ? p.x.slice(0, 110) : (i > 40 ? "…" : "") + p.x.slice(Math.max(0, i - 40), i + 90) + "…";
      return { p, sc, snip };
    }).filter(Boolean).sort((a, b) => b.sc - a.sc).slice(0, 20);
    res.innerHTML = hits.length ? hits.map(h => `<a href="${h.p.u}"><strong>${mark(h.p.t, terms)}</strong><small>${escH(h.p.s)} · ${mark(h.snip, terms)}</small></a>`).join("") : `<div class="none">Tidak ada hasil untuk “${escH(inp.value)}”</div>`;
    sel = 0; hi();
  };
  const hi = () => $$("a", res).forEach((a, i) => a.classList.toggle("sel", i === sel));
  const open = async () => {
    if (!dlg?.showModal) return;
    dlg.showModal(); inp.focus(); inp.select();
    if (!idx) { try { idx = await (await fetch(BASE + "/search.json")).json(); } catch (e) { idx = []; } }
    run();
  };
  $(".search-open")?.addEventListener("click", open);
  $(".search-close")?.addEventListener("click", () => dlg.close());
  dlg?.addEventListener("click", e => e.target === dlg && dlg.close());
  inp?.addEventListener("input", run);
  inp?.addEventListener("keydown", e => {
    const a = $$("a", res);
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, a.length - 1); hi(); a[sel]?.scrollIntoView({ block: "nearest" }); e.preventDefault(); }
    if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); hi(); a[sel]?.scrollIntoView({ block: "nearest" }); e.preventDefault(); }
    if (e.key === "Enter" && a[sel]) location.href = a[sel].href;
  });
  addEventListener("keydown", e => {
    if ((e.key === "/" || (e.key === "k" && (e.ctrlKey || e.metaKey))) && !/input|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); open(); }
  });
})();

// ROM archive filter
(() => {
  const tools = document.querySelector(".arc-tools"); if (!tools) return;
  const inp = tools.querySelector("input"), chips = [...tools.querySelectorAll(".fchip")];
  const items = [...document.querySelectorAll(".arc-item")], groups = [...document.querySelectorAll(".arc-group")];
  let a = "";
  const run = () => {
    const q = inp.value.trim().toLowerCase().split(/\s+/).filter(Boolean); let n = 0;
    items.forEach(it => { const ok = (!a || it.dataset.a === a) && q.every(w => it.dataset.q.includes(w)); it.hidden = !ok; n += ok; });
    groups.forEach(g => g.hidden = !g.querySelector(".arc-item:not([hidden])"));
    document.querySelector(".arc-empty").hidden = n > 0;
  };
  chips.forEach(c => c.addEventListener("click", () => { chips.forEach(x => x.classList.toggle("on", x === c)); a = c.dataset.a; run(); }));
  inp.addEventListener("input", run);
})();
