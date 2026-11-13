(() => {
  "use strict";

  const data = window.CURLING_FULL_MATCH_EVIDENCE;
  if (!data || !Array.isArray(data.events)) {
    document.body.textContent = "Evidence data could not be loaded. Keep data.js beside this page.";
    return;
  }
  const events = data.events;
  const byId = new Map(events.map((event, index) => [event.id, index]));
  const tracklets = new Map(data.tracklets.map(tracklet => [tracklet.id, tracklet]));
  const $ = id => document.getElementById(id);
  const video = $("video");
  const groupLabels = {
    frozen_candidate: "Frozen provisional",
    development_only: "Development only",
    screen_abstention: "Screen abstention",
    outside_corridor: "Outside corridor",
    reviewed_false_positive: "Reviewed false positive",
  };
  let selectedIndex = 0;
  let visibleIndices = events.map((_, index) => index);
  let pendingSeek = null;

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }
  function timeLabel(seconds) {
    const s = Math.round(seconds);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const rem = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`
             : `${m}:${String(rem).padStart(2, "0")}`;
  }
  function statusName(status) {
    return ({
      partial_stable_view_local_board: "Partial board observed",
      no_stable_stones_in_registered_tail: "No stable stones in sampled tail",
      no_quiet_tail_before_next_candidate_or_interval_end: "No usable quiet tail",
      view_local_partial_comparison: "Same-view partial comparison",
      abstain_missing_partial_board: "Abstained: board missing",
      abstain_intervening_passage_candidate: "Abstained: intervening candidate",
      abstain_camera_change: "Abstained: camera change",
    })[status] || (status ? status.replaceAll("_", " ") : "Unobserved");
  }

  function renderStats() {
    const counts = data.counts;
    const items = [
      [events.length, "raw motion candidates"],
      [counts.frozen_candidate + counts.reviewed_false_positive, "frozen provisional flags"],
      [counts.development_only, "postscore additions"],
      [events.filter(event => event.board_status === "partial_stable_view_local_board").length, "partial boards"],
      [counts.reviewed_false_positive, "source-reviewed false flags"],
    ];
    $("stats").innerHTML = items.map(([count, label]) =>
      `<div class="stat"><strong>${count}</strong><span>${esc(label)}</span></div>`).join("");
  }

  function filteredIndices() {
    const filter = $("filter").value;
    const query = $("search").value.trim().toLowerCase();
    return events.flatMap((event, index) => {
      if (filter !== "all" && event.group !== filter) return [];
      const haystack = `${event.id} ${timeLabel(event.time_s)} ${Math.round(event.time_s)} ${event.colour}`.toLowerCase();
      return query && !haystack.includes(query) ? [] : [index];
    });
  }

  function renderList() {
    visibleIndices = filteredIndices();
    $("list-count").textContent = `${visibleIndices.length} shown · click to seek source video`;
    $("candidate-list").innerHTML = visibleIndices.map(index => {
      const event = events[index];
      const group = event.group;
      return `<button type="button" class="candidate-button group-${group}" data-index="${index}" aria-current="${index === selectedIndex}">
        <span class="stripe"></span><span><span class="candidate-line"><strong>${esc(event.id)} · ${esc(event.colour)}</strong><time>${timeLabel(event.time_s)}</time></span>
        <span class="candidate-sub">${esc(groupLabels[group])}${event.displayed_end_run ? ` · display ${event.displayed_end_run}` : ""}</span></span></button>`;
    }).join("") || "<p class='small-note' style='padding:0 16px'>No candidates match this filter.</p>";
  }

  function svgEmpty(message) {
    return `<text class="empty-svg" x="180" y="310">${esc(message)}</text>`;
  }

  function pathSvg(event) {
    const path = event.path;
    if (!path.length) return svgEmpty("No supported receiving path");
    const yValues = path.map(node => node.y_m);
    const lower = Math.min(0, ...yValues) - 1;
    const upper = Math.max(0, ...yValues) + 1;
    const range = upper - lower;
    const scale = Math.min(304 / 4.75, 584 / range);
    const midpoint = (lower + upper) / 2;
    const x = value => 180 + value * scale;
    const y = value => 320 - (value - midpoint) * scale;
    const left = x(-2.375), right = x(2.375), top = y(upper), bottom = y(lower);
    const points = path.map(node => `${x(node.x_m).toFixed(1)},${y(node.y_m).toFixed(1)}`).join(" ");
    const start = path[0], end = path.at(-1);
    const colour = event.colour === "yellow" ? "#d5a622" : "#c73b33";
    const tickStep = range > 15 ? 5 : range > 8 ? 2 : 1;
    let ticks = "";
    for (let value = Math.ceil(lower / tickStep) * tickStep; value <= upper; value += tickStep) {
      ticks += `<line class="rink-grid" x1="${left}" x2="${right}" y1="${y(value)}" y2="${y(value)}"/><text class="rink-label" x="${right + 5}" y="${y(value) + 4}">${value} m</text>`;
    }
    return `<rect class="rink-boundary" x="${left}" y="${top}" width="${right-left}" height="${bottom-top}"/>
      ${ticks}<line class="rink-center" x1="${x(0)}" x2="${x(0)}" y1="${top}" y2="${bottom}"/>
      <polyline class="path-line" points="${points}"/>
      <circle class="path-dot" cx="${x(start.x_m)}" cy="${y(start.y_m)}" r="7" fill="${colour}"/>
      <circle class="path-dot" cx="${x(end.x_m)}" cy="${y(end.y_m)}" r="7" fill="#184f65"/>
      <text class="rink-label" x="${x(start.x_m)+10}" y="${y(start.y_m)-8}">first</text>
      <text class="rink-label" x="${x(end.x_m)+10}" y="${y(end.y_m)+16}">last</text>`;
  }

  function boardSvg(event) {
    if (event.board_status !== "partial_stable_view_local_board") {
      return svgEmpty(event.board_status ? "No stable partial board" : "Board not observed for this candidate");
    }
    const scale = 64;
    const x = value => 180 + value * scale;
    const y = value => 320 - value * scale;
    const rings = `<circle class="house-outer" cx="180" cy="320" r="${1.829*scale}"/>
      <circle class="house-middle" cx="180" cy="320" r="${1.219*scale}"/>
      <circle class="house-inner" cx="180" cy="320" r="${0.610*scale}"/>
      <circle class="house-button" cx="180" cy="320" r="${0.152*scale}"/>`;
    let grid = `<rect class="rink-boundary" x="28" y="28" width="304" height="584"/>`;
    for (let value = -4; value <= 4; value++) {
      grid += `<line class="rink-grid" x1="28" x2="332" y1="${y(value)}" y2="${y(value)}"/>`;
    }
    grid += `<line class="rink-center" x1="180" x2="180" y1="28" y2="612"/>`;
    const stones = event.stones.map(stone => {
      const fill = stone.colour === "yellow" ? "#d5a622" : "#c73b33";
      const labelFill = stone.colour === "yellow" ? "#382d12" : "#fff";
      return `<g data-tracklet="${esc(stone.tracklet_id)}"><circle class="stone" cx="${x(stone.x_m)}" cy="${y(stone.y_m)}" r="14" fill="${fill}"/>
        <text class="stone-id" x="${x(stone.x_m)}" y="${y(stone.y_m)}" fill="${labelFill}">${esc(stone.tracklet_id)}</text></g>`;
    }).join("");
    return `${grid}${rings}${stones}<text class="rink-label" x="34" y="603">conditional metres · house at (0, 0)</text>`;
  }

  function interpretation(event) {
    if (event.group === "reviewed_false_positive")
      return event.review_note || "The frozen screen accepted this candidate, but source review found a false-positive path. Keep it visible as a known false flag.";
    if (event.group === "development_only")
      return "A postscore short-path rule recovered a moving, stone-like proposal here. It was designed after seeing this recording; the early passage-to-stone association and physical throw identity are unverified.";
    if (event.group === "frozen_candidate")
      return "The frozen motion and stone-appearance filters support a provisional candidate. This does not verify the physical throw, exact boundaries, or complete trajectory.";
    if (event.group === "screen_abstention")
      return "This early motion candidate entered the fixed corridor, but the receiving-path and appearance evidence did not pass the frozen screen. It may be a false alarm or a missed throw; source review is needed.";
    return "This raw motion candidate was withheld by the fixed ice-corridor rule. Its physical identity was not assessed by the high-resolution receiving-path screen.";
  }

  function renderStones(event) {
    const target = $("stones-table");
    $("tracklet-detail").hidden = true;
    if (!event.stones.length) {
      target.innerHTML = "<p class='small-note'>No stable stone observations were available for this candidate.</p>";
      return;
    }
    const rows = event.stones.map(stone => `<tr><td><span class="colour-dot ${esc(stone.colour)}"></span>${esc(stone.colour)}</td>
      <td><button type="button" data-tracklet="${esc(stone.tracklet_id)}">${esc(stone.tracklet_id)}</button></td>
      <td>${stone.x_m.toFixed(2)}, ${stone.y_m.toFixed(2)} m</td><td>${stone.supporting_frames}</td></tr>`).join("");
    target.innerHTML = `<table class="stone-table"><thead><tr><th>Colour</th><th>Tracklet</th><th>View-local position</th><th>Frames</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function showTracklet(id) {
    const tracklet = tracklets.get(id);
    if (!tracklet) return;
    const target = $("tracklet-detail");
    target.hidden = false;
    target.innerHTML = `<strong>${esc(id)} · ${esc(tracklet.colour)} · ${esc(tracklet.view)} camera</strong>
      <p>${tracklet.candidate_ids.length} linked board observations. This is image-space continuity only; physical stone identity is unverified.</p>
      <div class="tracklet-jumps">${tracklet.candidate_ids.map(candidate => `<button type="button" data-candidate="${esc(candidate)}">${esc(candidate)}</button>`).join("")}</div>`;
    target.scrollIntoView({block:"nearest", behavior:"smooth"});
  }

  function seekTo(time) {
    const target = Math.max(0, time);
    if (video.readyState >= 1) video.currentTime = target;
    else pendingSeek = target;
  }

  function select(index, shouldSeek = true) {
    if (index < 0 || index >= events.length) return;
    selectedIndex = index;
    const event = events[index];
    history.replaceState(null, "", `#${event.id}`);
    $("selected-title").textContent = `${event.id} · ${timeLabel(event.time_s)} · ${event.colour} proposal`;
    const pill = $("selected-status");
    pill.className = `status-pill ${event.group}`;
    pill.textContent = groupLabels[event.group];
    $("time-note").textContent = `Observed passage estimate: ${event.time_s.toFixed(3)} s (${timeLabel(event.time_s)}). The video jumps four seconds earlier. This is not the exact release time.`;
    $("fact-view").textContent = event.receiving_view ? `${event.receiving_view} camera` : "Not screened";
    $("fact-end").textContent = event.displayed_end_run ? `End ${event.displayed_end_run} graphic` : "Graphic gap / unsampled";
    $("fact-board").textContent = statusName(event.board_status);
    $("fact-comparison").textContent = event.comparison
      ? `${statusName(event.comparison.status)}${event.comparison.matched_count ? ` · ${event.comparison.matched_count} links` : ""}`
      : "No preceding screened board";
    $("path-caption").textContent = event.path.length
      ? `${event.path.length} sampled positions · ${event.path_source === "postscore_development" ? "postscore development path" : "frozen path"} · conditional camera-local projection`
      : "The screen did not retain an observable path here.";
    $("board-caption").textContent = event.board_status === "partial_stable_view_local_board"
      ? `${event.stones.length} stable stone proposals · camera-local positions · completeness unknown`
      : statusName(event.board_status);
    $("path-svg").innerHTML = pathSvg(event);
    $("board-svg").innerHTML = boardSvg(event);
    $("interpretation").textContent = interpretation(event);
    $("review-link").innerHTML = event.review_frame
      ? `<a href="${esc(event.review_frame)}" target="_blank" rel="noopener">Open source-review frame ↗</a>` : "";
    renderStones(event);
    renderList();
    const list = $("candidate-list");
    const current = list.querySelector('[aria-current="true"]');
    if (current) {
      const listBox = list.getBoundingClientRect();
      const itemBox = current.getBoundingClientRect();
      if (itemBox.top < listBox.top) list.scrollTop -= listBox.top - itemBox.top;
      else if (itemBox.bottom > listBox.bottom) list.scrollTop += itemBox.bottom - listBox.bottom;
    }
    if (shouldSeek) seekTo(event.time_s - 4);
  }

  function move(direction) {
    const position = visibleIndices.indexOf(selectedIndex);
    const next = visibleIndices[position + direction];
    if (next !== undefined) select(next);
  }

  $("candidate-list").addEventListener("click", event => {
    const button = event.target.closest("button[data-index]");
    if (button) {
      select(Number(button.dataset.index));
      if (window.innerWidth <= 700) $("video").scrollIntoView({block:"start", behavior:"smooth"});
    }
  });
  $("stones-table").addEventListener("click", event => {
    const button = event.target.closest("button[data-tracklet]");
    if (button) showTracklet(button.dataset.tracklet);
  });
  $("board-svg").addEventListener("click", event => {
    const group = event.target.closest("g[data-tracklet]");
    if (group) showTracklet(group.dataset.tracklet);
  });
  $("tracklet-detail").addEventListener("click", event => {
    const button = event.target.closest("button[data-candidate]");
    if (button) select(byId.get(button.dataset.candidate));
  });
  $("search").addEventListener("input", renderList);
  $("filter").addEventListener("change", renderList);
  $("previous").addEventListener("click", () => move(-1));
  $("next").addEventListener("click", () => move(1));
  $("seek").addEventListener("click", () => seekTo(events[selectedIndex].time_s - 4));
  video.addEventListener("loadedmetadata", () => {
    if (pendingSeek !== null) {
      video.currentTime = pendingSeek;
      pendingSeek = null;
    }
  });
  window.addEventListener("hashchange", () => {
    const index = byId.get(location.hash.slice(1));
    if (index !== undefined) select(index);
  });

  renderStats();
  const initial = byId.get(location.hash.slice(1));
  select(initial === undefined ? 0 : initial);
})();
