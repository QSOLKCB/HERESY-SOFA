/* HERESY CASEBOARD — no frameworks, cookies, telemetry or third-party requests.
 * Static JSON catalog; the red string is canvas, the evidence stays in Git.
 */
(() => {
  "use strict";

  const root = document.getElementById("case-grid");
  const surface = document.getElementById("board-surface");
  const canvas = document.getElementById("thread-canvas");
  const dialog = document.getElementById("case-dialog");
  const detail = document.getElementById("dialog-content");
  const search = document.getElementById("case-search");
  const noResults = document.getElementById("no-results");
  const filterButtons = Array.from(document.querySelectorAll(".filter"));
  const SOURCE = "https://github.com/QSOLKCB/HERESY-SOFA";
  const palette = {
    PARSER: "#ac6b37", SHELL: "#8a6650", DATABASE: "#6a8062",
    ENCODING: "#b86b44", GIT: "#607d74", SECURITY: "#a6453d",
    WATCHLIST: "#82765d", GRAPH: "#6d789e"
  };
  const state = {cases: [], connections: [], filter: "all", query: "", lastFocus: null};

  function make(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = String(content);
    return node;
  }
  function validRepoPath(path) {
    return typeof path === "string" && /^(experiments|incidents|blueprints)\/HERESY-0[0-9]{2}(?:\/|\.)[A-Za-z0-9_.-]+$/.test(path);
  }
  function link(label, href) {
    const node = make("a", "", label);
    node.href = href;
    node.target = "_blank";
    node.rel = "noopener noreferrer";
    node.appendChild(make("span", "", "↗"));
    return node;
  }
  function status(caseData) {
    if (caseData.status === "placeholder" && caseData.evidenceState === "observed") return {short: "OBSERVED", extended: "VALID VARIATION / NOT AN UPSTREAM BUG", kind: "observed", dot: "green"};
    if (caseData.status === "placeholder") return {short: "WANTED", extended: "DEVICE ASSERTION NOT TESTED", kind: "wanted", dot: "gray"};
    if (caseData.published) return {short: "SOFA FILED", extended: "REPRODUCER + SOFA", kind: "published", dot: "green"};
    return {short: "CAUGHT", extended: "BOUNDED REPRODUCTION", kind: "captured", dot: ""};
  }
  function addCaseCard(item, index) {
    const button = make("button", "case-card" + (item.status === "placeholder" && item.evidenceState !== "observed" ? " is-wanted" : "") + (item.id === "HERESY-011" ? " is-feature" : ""));
    button.type = "button";
    button.dataset.caseId = item.id;
    button.style.setProperty("--tilt", String(Number(item.rotation) || 0) + "deg");
    button.style.setProperty("--accent", palette[item.category] || "#9a6b50");
    button.setAttribute("aria-label", "Open dossier for " + item.id + ": " + item.name);

    button.append(make("span", "case-tape"), make("span", "case-pin"));
    const paper = make("span", "case-paper");
    const serial = make("span", "case-serial");
    serial.append(make("span", "", "FILE / " + item.id.slice(-3)));
    const signal = status(item);
    serial.append(make("span", "case-seal " + signal.kind, signal.short));
    paper.append(serial, make("span", "case-symbol", item.symbol), make("span", "case-name", item.name), make("span", "case-teaser", "“" + item.teaser + "”"));
    const foot = make("span", "case-foot");
    const left = make("span", "");
    left.append(make("i",signal.dot),document.createTextNode(item.category));
    foot.append(left, make("span", "case-open", "↗"));
    paper.append(foot);
    button.append(paper);
    button.addEventListener("click", () => openDossier(item, button));
    // Handle instant transforms too (reduced-motion, or a zero-duration CSS
    // transition). Animated transforms are tracked below until completion.
    for (const name of ["pointerenter", "pointerleave", "focus", "blur"]) {
      button.addEventListener(name, requestDrawing);
    }
    root.append(button);
  }
  function rule(title, body) {
    const section = make("section", "dossier-rule");
    section.append(make("h3", "", title), make("p", "", body));
    return section;
  }
  function openDossier(item, focusFrom) {
    state.lastFocus = focusFrom;
    document.getElementById("dialog-number").textContent = item.id + " / OFFICIAL CASE FILE";
    detail.replaceChildren();
    const body = make("div", "dossier-content");
    const s = status(item);
    body.append(make("div", "dossier-kicker", item.category + " / " + item.type));
    const heading = make("h2", "dossier-title", item.name);
    heading.id = "dialog-title"; // Resolves the modal's aria-labelledby.
    body.append(heading);
    body.append(make("p", "dossier-description", item.teaser));
    const stamps = make("div", "dossier-stamps");
    stamps.append(make("span",item.status === "placeholder" && item.evidenceState !== "observed" ? "unverified" : "verified",s.extended));
    if (item.status === "placeholder") stamps.append(make("span", "unverified","OUTSIDE DEFAULT RUN-ALL"));
    if (item.id === "HERESY-005" && item.competition === "HERESY-005-CUDA-CUP") {
      stamps.append(make("span", "unverified", "CUDA CUP OPEN / 710 NOT OBSERVED"));
    }
    if (item.published) stamps.append(make("span", "verified",item.published === "blueprint" ? "BLUEPRINT PUBLISHED" : item.published === "til" ? "PREFLIGHT TIL PUBLISHED" : "SOFA REPLY PUBLISHED"));
    body.append(stamps);
    body.append(rule("01 / THE ALLEGATION", item.cause));
    body.append(rule("02 / RECORDED EVIDENCE", item.finding));
    body.append(rule("03 / CORRECTIVE PROCEDURE", item.mitigation));
    body.append(rule("04 / CLAIM BOUNDARY", item.scope));
    const tags = make("div", "dossier-meta");
    for(const tag of item.tags || []) tags.append(make("span", "", "#" + tag));
    body.append(tags);
    const links = make("nav", "dossier-links");
    links.setAttribute("aria-label", "Case source links");
    if (validRepoPath(item.doc)) links.append(link("READ THE EXPERIMENT", SOURCE + "/blob/main/" + item.doc));
    if (validRepoPath(item.incident)) links.append(link("READ THE INCIDENT REPORT", SOURCE + "/blob/main/" + item.incident));
    if (validRepoPath(item.report)) links.append(link("READ SOURCE-LOCKED EXECUTION REPORT", SOURCE + "/blob/main/" + item.report));
    if (item.id === "HERESY-005" && item.competition === "HERESY-005-CUDA-CUP") {
      links.append(link("JOIN THE CUDA ASSERTION COMPETITION", "https://agents.stackoverflow.com/questions/15a7e10c-b83c-4a6a-b488-2d21dc3844a8"));
      links.append(link("READ CUDA CUP RULES & SAFETY", SOURCE + "/blob/main/competitions/HERESY-005-CUDA-CUP/README.md"));
    }
    if (item.id === "HERESY-011") links.append(link("READ THE ARCHIVED BLUEPRINT",SOURCE + "/blob/main/blueprints/HERESY-011/BLUEPRINT.md"));
    // Publication references are a small fixed, audited set. Never interpolate
    // untrusted external URLs into the DOM.
    const publications = {
      "HERESY-005":"https://agents.stackoverflow.com/tils/dd9e3bfe-edeb-4596-8d59-26af83f26572",
      "HERESY-006":"https://agents.stackoverflow.com/blueprints/4bcd561f-3968-4e61-a49b-abc636a05f79",
      "HERESY-007":"https://agents.stackoverflow.com/tils/44ce169b-068e-45d0-a15d-500166400d24",
      "HERESY-009":"https://agents.stackoverflow.com/tils/7d036b29-2221-43ec-b6c6-748e379bae32",
      "HERESY-010":"https://agents.stackoverflow.com/tils/68be9bd0-2e63-47e3-9a2b-c262f9937942",
      "HERESY-011":"https://agents.stackoverflow.com/blueprints/31f6e754-bf85-4e81-b626-ea17d0d70fb9"
    };
    if (item.published && publications[item.id]) {
      links.append(link(item.published === "blueprint" ? "OPEN PUBLISHED SOFA BLUEPRINT" : item.published === "til" ? "OPEN PUBLISHED SOFA TIL" : "OPEN SOFA THREAD WITH PUBLISHED REPLY",publications[item.id]));
    }
    body.append(links);
    detail.append(body);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }
  function closeDossier() {
    if (dialog.open && typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
    if (state.lastFocus && state.lastFocus.isConnected && !state.lastFocus.hidden) state.lastFocus.focus();
  }
  document.getElementById("dialog-close").addEventListener("click", closeDossier);
  dialog.addEventListener("click", (event) => {if (event.target === dialog) closeDossier();});
  dialog.addEventListener("close", () => {
    if (state.lastFocus?.isConnected && !state.lastFocus.hidden) state.lastFocus.focus();
  });

  function matches(item) {
    const filter = state.filter;
    if (filter === "implemented" && item.status !== "implemented") return false;
    if (filter === "placeholder" && (item.status !== "placeholder" || item.evidenceState === "observed")) return false;
    if (filter === "observed" && item.evidenceState !== "observed") return false;
    if (filter === "published" && !item.published) return false;
    if (!state.query) return true;
    const corpus = [item.id,item.name,item.formal,item.category,item.cause,item.finding,item.mitigation,item.teaser,item.scope,...(item.tags || [])].join(" ").toLowerCase();
    return corpus.includes(state.query);
  }
  function updateView() {
    let visible = 0;
    for (const item of state.cases) {
      const card = root.querySelector('[data-case-id="' + item.id + '"]');
      if (!card) continue;
      card.hidden = !matches(item);
      if (!card.hidden) visible++;
    }
    noResults.hidden = visible !== 0;
    filterButtons.forEach(button => {
      const selected = button.dataset.filter === state.filter;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    requestDrawing();
  }
  filterButtons.forEach(btn => btn.addEventListener("click", () => {
    state.filter = btn.dataset.filter;
    updateView();
  }));
  search.addEventListener("input", () => {
    state.query = search.value.trim().toLowerCase();
    updateView();
  });
  // ResizeObserver does not observe CSS transforms: a moving card also moves
  // its pin. Follow the transform on every animation frame while it is active,
  // then redraw once at the exact final position (including reversals/cancels).
  const activeTransitions = new Set();
  let frame = 0;
  function requestDrawing() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      drawThreads();
      if (activeTransitions.size > 0) requestDrawing();
    });
  }
  function trackCardTransition(event) {
    if (event.propertyName !== "transform" ||
        !event.target.classList?.contains("case-card")) return;
    if (event.type === "transitionrun") {
      activeTransitions.add(event.target);
    } else {
      activeTransitions.delete(event.target);
    }
    // Both transitionend and transitioncancel need a final redraw. A rapid
    // hover reversal emits cancel then run; the new run resumes the loop.
    requestDrawing();
  }
  for (const type of ["transitionrun", "transitionend", "transitioncancel"]) {
    root.addEventListener(type, trackCardTransition);
  }
  function drawThreads() {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = surface.getBoundingClientRect();
    const width = Math.max(1,rect.width),height = Math.max(1,rect.height);
    const dpr = Math.min(window.devicePixelRatio || 1,2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,width,height);
    if (!state.connections.length) return;
    const points = {};
    for (const item of state.cases) {
      const card = root.querySelector('[data-case-id="' + item.id + '"]');
      if (!card || card.hidden) continue;
      const pin = card.querySelector(".case-pin");
      if (!pin) continue;
      const p = pin.getBoundingClientRect();
      points[item.id] = {x:p.left + p.width/2 - rect.left,y:p.top + p.height/2 - rect.top};
    }
    ctx.lineWidth = 1.75;ctx.lineCap="round";
    for(const pair of state.connections) {
      if(!Array.isArray(pair) || pair.length !== 2) continue;
      const a = points[pair[0]],b = points[pair[1]];
      if(!a || !b) continue;
      const dx=b.x-a.x,dy=b.y-a.y;
      const sag=Math.min(58,Math.max(18,Math.abs(dx)*.06+Math.abs(dy)*.04));
      const midpoint={x:(a.x+b.x)/2 + (dy > 0 ? 9:-9),y:(a.y+b.y)/2+sag};
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo(midpoint.x,midpoint.y,b.x,b.y);
      ctx.strokeStyle="#5a1d1888";ctx.shadowColor="#21100d88";ctx.shadowBlur=4;ctx.shadowOffsetY=3;ctx.stroke();
      ctx.shadowBlur=0;ctx.shadowOffsetY=0;
      ctx.beginPath();ctx.moveTo(a.x,a.y-1);ctx.quadraticCurveTo(midpoint.x,midpoint.y-1,b.x,b.y-1);
      ctx.strokeStyle="#b54637bd";ctx.lineWidth=1.2;ctx.stroke();
      ctx.fillStyle="#8c3328";
      for (const p of [a,b]) {ctx.beginPath();ctx.arc(p.x,p.y,2.4,0,Math.PI*2);ctx.fill();}
    }
  }
  window.addEventListener("resize", requestDrawing, {passive:true});
  if(typeof ResizeObserver === "function") new ResizeObserver(requestDrawing).observe(surface);
  document.fonts?.ready?.then(requestDrawing);

  async function loadCases() {
    try {
      const response = await fetch("./cases.json",{cache:"no-cache"});
      if (!response.ok) throw new Error("Could not load case catalogue");
      const data = await response.json();
      if(data.schema !== 1 || !Array.isArray(data.cases) || !Array.isArray(data.connections)) throw new Error("Unexpected case catalogue schema");
      if(new Set(data.cases.map(x=>x.id)).size !== data.cases.length) throw new Error("Duplicate case IDs");
      state.cases = data.cases;
      state.connections = data.connections;
      root.replaceChildren();
      data.cases.forEach(addCaseCard);
      document.getElementById("stat-total").textContent = String(data.cases.length);
      document.getElementById("stat-captured").textContent = String(data.cases.filter(x=>x.status === "implemented").length);
      document.getElementById("stat-observed").textContent = String(data.cases.filter(x=>x.evidenceState === "observed").length);
      document.getElementById("stat-watch").textContent = String(data.cases.filter(x=>x.status === "placeholder" && x.evidenceState !== "observed").length);
      for (const [name,count] of Object.entries({
        all:data.cases.length,implemented:data.cases.filter(x=>x.status === "implemented").length,
        placeholder:data.cases.filter(x=>x.status === "placeholder" && x.evidenceState !== "observed").length,
        observed:data.cases.filter(x=>x.evidenceState === "observed").length,
        published:data.cases.filter(x=>x.published).length
      })) {
        document.getElementById("filter-count-"+name).textContent=String(count);
      }
      updateView();
    } catch (error) {
      root.replaceChildren();
      root.append(make("p","loading-message","CASE FILES UNAVAILABLE. OPEN THE SOURCE ARCHIVE OR SERVE THIS SITE OVER HTTP."));
      console.error("HERESY caseboard:",error instanceof Error ? error.message : "unknown error");
    }
  }
  loadCases();
})();
