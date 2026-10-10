(() => {
  "use strict";
  const data = window.CURLING_DATA;
  const rows = data.ordered_candidates;
  const $ = id => document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const video = $("video");
  let selected = null;
  let filtered = rows;

  function fmt(seconds) {
    const whole = Math.floor(seconds);
    return `${String(Math.floor(whole / 3600)).padStart(2, "0")}:${String(Math.floor(whole % 3600 / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
  }
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function svg(tag, attrs) {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    return node;
  }
  function kind(row) {
    return row.observation_kind === "left_provisional_passage" ? "left" :
      row.observation_kind === "left_unconfirmed_raw_motion" ? "raw" : "right";
  }
  function kindText(row) {
    return kind(row) === "left" ? "Left provisional passage" :
      kind(row) === "raw" ? "Left screen abstention" : "Right-only review entry";
  }
  function seek(time) {
    if (!Number.isFinite(time)) return;
    video.pause();
    if (video.readyState >= 1) video.currentTime = Math.max(0, time);
    else video.addEventListener("loadedmetadata", () => video.currentTime = Math.max(0, time), {once: true});
  }
  function term(dl, name, value) {
    dl.append(el("dt", name), el("dd", value));
  }
  function drawOverlay(row) {
    const layer = $("video-overlay");
    layer.replaceChildren();
    const m = row.observed_motion;
    if (kind(row) === "right") {
      const points = m.observed_prefix_points;
      if (points.length > 1) layer.append(svg("polyline", {
        points: points.map(p => p.pixel.join(",")).join(" "),
        fill: "none", stroke: "#f6b84e", "stroke-width": 3,
        "stroke-linecap": "round", "stroke-linejoin": "round"
      }));
      layer.append(svg("circle", {cx: m.crossing_x_px, cy: m.entry_line_y_px,
        r: 6, fill: "#f6b84e", stroke: "#183039", "stroke-width": 1.5}));
    } else {
      layer.append(svg("circle", {cx: m.crossing_x_px, cy: m.passage_y_px,
        r: 6, fill: kind(row) === "left" ? "#24bbca" : "#bbc1c5",
        stroke: "#183039", "stroke-width": 1.5}));
    }
  }
  function drawBoard(row) {
    const board = $("board");
    board.replaceChildren(svg("rect", {x: 0, y: 120, width: 320, height: 240,
      fill: "#e8f0ef"}), svg("line", {x1: 160, x2: 160, y1: 120, y2: 360,
      stroke: "#9db7b7", "stroke-width": 1}));
    const observation = row.post_candidate_partial_board;
    if (!observation || observation.status !== "partial_stable_colour_cap_proposals") {
      $("board-note").textContent = observation ?
        "Cap observation abstained because of scene or player motion. No board inferred." :
        "No partial right-camera cap observation is attached to this row.";
      return;
    }
    for (const cap of observation.stable_cap_proposals) {
      const dot = svg("circle", {cx: cap.pixel_center[0] - 320,
        cy: cap.pixel_center[1], r: 7,
        fill: cap.colour === "red" ? "#d65049" : "#ecc147",
        stroke: "#17323b", "stroke-width": 1.5});
      dot.append(svg("title", {}));
      dot.firstChild.textContent = `${cap.local_observation_id} · ${cap.colour} cap proposal`;
      board.append(dot);
      const label = svg("text", {x: cap.pixel_center[0] - 310,
        y: cap.pixel_center[1] - 8, fill: "#17323b", "font-size": 10,
        "font-weight": "bold"});
      label.textContent = cap.local_observation_id;
      board.append(label);
    }
    const prior = data.right_adjacent_partial_cap_transitions.find(t =>
      `right:${t.after_right_track_id}` === row.candidate_id);
    const continuity = prior ? prior.status === "conditional_image_pixel_cap_association" ?
      " Previous right sample: conditional image-pixel associations only." :
      " Previous right sample: comparison abstained." : "";
    $("board-note").textContent = `${observation.stable_cap_proposals.length} repeated colour-cap proposals in right-camera pixels. They are not counted physical stones.${continuity}`;
  }
  function select(row) {
    if (!row) return;
    selected = row;
    $("selected-title").textContent = `${row.sequence_id} · ${row.candidate_id}`;
    $("selected-tier").textContent = kindText(row);
    $("selected-tier").className = `pill ${kind(row)}`;
    $("time-note").textContent = `${fmt(row.source_time_s)} (${row.source_time_s.toFixed(3)} s). Marker is an ${row.time_semantics.replaceAll("_", " ")}; it is not release time. Right-view lines summarize a short observed prefix, not an instantaneous track.`;
    const details = $("motion-details");
    details.replaceChildren();
    term(details, "Colour claim", row.colour_claim);
    term(details, "Evidence tier", row.evidence_tier.replaceAll("_", " "));
    term(details, "Left-camera coverage", row.left_coverage_status.replaceAll("_", " "));
    if (kind(row) === "right") {
      term(details, "Right image crossing", `x=${row.observed_motion.crossing_x_px.toFixed(1)}, y=${row.observed_motion.entry_line_y_px}`);
      term(details, "Visible prefix", row.observed_motion.observed_prefix_interval_s.map(fmt).join("–"));
      term(details, "Observed prefix samples", String(row.observed_motion.observed_prefix_points.length));
    } else {
      term(details, "Left raw track", String(row.observed_motion.track_id));
      term(details, "Screen decision", row.left_screen_reason.replaceAll("_", " "));
      term(details, "Image point", `x=${row.observed_motion.crossing_x_px.toFixed(1)}, y=${row.observed_motion.passage_y_px.toFixed(1)}`);
    }
    if (row.source_pixel_review) {
      const reviewed = row.source_pixel_review;
      term(details, "Source-pixel review", `${reviewed.source_pixel_class.replaceAll("_", " ")} · same-agent, prediction-targeted`);
      const source = el("a", "View marked source crop");
      source.href = `../../layout-router/full-2024-coverage/latvia24-full-v1/${reviewed.sheet_path}`;
      source.target = "_blank";
      source.rel = "noopener";
      const evidence = el("dd");
      evidence.append(source);
      details.append(el("dt", "Review evidence"), evidence);
    }
    $("state-note").textContent = row.source_pixel_review?.source_pixel_class.startsWith("person") ?
      "Source review shows person or equipment pixels at the tracked crossing. This candidate does not provide a stone passage or after-throw state." :
      kind(row) === "raw" ?
      "The left screen withheld this raw motion. No post-event state can be assigned." :
      "This row is a candidate observation. Available pixels cannot establish a physical after-throw state.";
    drawOverlay(row);
    drawBoard(row);
    const cap = row.post_candidate_partial_board?.stable_cap_proposals?.[0];
    $("post").disabled = !cap;
    $("post").onclick = () => seek(cap.sample_times_s[1]);
    document.querySelectorAll(".candidate").forEach(node =>
      node.classList.toggle("active", node.dataset.id === row.candidate_id));
    document.querySelectorAll(".marker").forEach(node =>
      node.classList.toggle("selected", node.dataset.id === row.candidate_id));
    seek(row.source_time_s);
    history.replaceState(null, "", `#${encodeURIComponent(row.candidate_id)}`);
  }
  function renderList() {
    const query = $("search").value.trim().toLowerCase();
    const filter = $("filter").value;
    filtered = rows.filter(row => (filter === "all" || row.observation_kind === filter ||
      (filter === "reviewed_person" && row.source_pixel_review?.source_pixel_class.startsWith("person"))) &&
      (!query || `${row.sequence_id} ${row.candidate_id} ${fmt(row.source_time_s)}`.toLowerCase().includes(query)));
    $("list-count").textContent = `${filtered.length} of ${rows.length}`;
    const list = $("candidate-list");
    list.replaceChildren();
    for (const row of filtered) {
      const button = el("button", undefined, "candidate");
      button.type = "button";
      button.dataset.id = row.candidate_id;
      const sourceFlag = row.source_pixel_review?.source_pixel_class.startsWith("person") ?
        " · source-reviewed person" : row.source_pixel_review ? " · source-visible stone body" : "";
      button.append(el("strong", `${row.sequence_id} · ${row.candidate_id}`),
        el("small", `${fmt(row.source_time_s)} · ${kindText(row)} · ${row.colour_claim}${sourceFlag}`,
          kind(row)));
      if (row.source_pixel_review?.source_pixel_class.startsWith("person")) button.classList.add("reviewed-person");
      button.onclick = () => select(row);
      list.append(button);
    }
    if (selected && filtered.includes(selected)) select(selected);
    else if (filtered.length) select(filtered[0]);
  }
  function renderCoverage() {
    const bar = $("coverage");
    const duration = data.source_duration_s;
    for (const interval of data.routed_coverage_gaps_s) {
      const div = el("div", undefined, "interval gap");
      div.style.left = `${interval[0] / duration * 100}%`;
      div.style.width = `${(interval[1] - interval[0]) / duration * 100}%`;
      bar.append(div);
    }
    for (const item of data.left_trigger_blind_intervals) {
      const interval = item.interval_s;
      const div = el("div", undefined, "interval blind");
      div.style.left = `${interval[0] / duration * 100}%`;
      div.style.width = `${(interval[1] - interval[0]) / duration * 100}%`;
      bar.append(div);
    }
    for (const row of rows) {
      const button = el("button", undefined, `marker ${kind(row)}`);
      button.type = "button";
      button.dataset.id = row.candidate_id;
      button.style.left = `${row.source_time_s / duration * 100}%`;
      button.title = `${row.candidate_id} · ${fmt(row.source_time_s)}`;
      button.onclick = () => select(row);
      bar.append(button);
    }
  }
  function init() {
    const stats = [
      [rows.length, "ordered evidence rows"],
      [data.candidate_counts_by_kind.left_provisional_passage, "left provisional passages"],
      [data.candidate_counts_by_kind.left_unconfirmed_raw_motion, "left screen abstentions"],
      [data.candidate_counts_by_kind.right_only_review_entry, "right-only reviews"]
    ];
    for (const [number, label] of stats) {
      const tile = el("div", undefined, "stat");
      tile.append(el("strong", String(number)), el("span", label));
      $("summary").append(tile);
    }
    renderCoverage();
    $("search").oninput = renderList;
    $("filter").onchange = renderList;
    $("seek").onclick = () => selected && seek(selected.source_time_s);
    $("previous").onclick = () => select(rows[Math.max(0, rows.indexOf(selected) - 1)]);
    $("next").onclick = () => select(rows[Math.min(rows.length - 1, rows.indexOf(selected) + 1)]);
    const requested = decodeURIComponent(location.hash.slice(1));
    renderList();
    if (requested) select(rows.find(row => row.candidate_id === requested) || rows[0]);
  }
  init();
})();
