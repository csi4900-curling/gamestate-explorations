/* Shared renderer for public match observation viewers.
 * Shared metric scale, complete chunk bounds, no interpolation across missing rows.
 * Future samples influence layout only; paths stop at the displayed observation.
 */
drawBoard = function(panel, row, rows) {
  const canvas = document.querySelector('#' + panel), ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const bounds = {};
  for (const name of ['left', 'right']) {
    const pts = rows.flatMap(r => r.boards[name].stones.filter(s => s.xy).map(s => s.xy));
    bounds[name] = {
      xmin: Math.min(-2.375, ...pts.map(p => p[0])),
      xmax: Math.max(2.375, ...pts.map(p => p[0])),
      ymin: Math.min(-1.829, ...pts.map(p => p[1])),
      ymax: Math.max(1.829, ...pts.map(p => p[1]))
    };
  }
  const scale = Math.min(...Object.values(bounds).flatMap(b => [
    (canvas.width - 30) / (b.xmax - b.xmin),
    (canvas.height - 80) / (b.ymax - b.ymin)
  ]));
  const b = bounds[panel];
  const pos = p => [canvas.width / 2 + (p[0] - (b.xmin+b.xmax)/2)*scale,
                    45 + (p[1] - b.ymin)*scale];
  ctx.fillStyle = '#243b48'; ctx.font = '13px system-ui';
  ctx.fillText(panel + ' — local metres', 9, 20);
  ctx.strokeStyle = '#cadae0';
  for (const r of [1.829, 1.219, .610]) {
    ctx.beginPath(); ctx.arc(...pos([0,0]), r*scale, 0, Math.PI*2); ctx.stroke();
  }
  let edges = 0, observations = 0, previous = null;
  const rendered = [];
  ctx.strokeStyle = ctx.fillStyle = panel === 'left' ? '#288b9a' : '#d98b31';
  const step = rows.length > 1 ? rows[1].t - rows[0].t : 0;
  for (const sample of rows) {
    if (!row || sample.t > row.t) break;
    for (const stone of sample.boards[panel].stones) {
      if (!stone.xy || stone.id === null || (typeof selectedStone === 'function' && !selectedStone(panel, stone))) continue;
      const p = pos(stone.xy); rendered.push(p); observations++;
      const last = previous?.boards[panel].stones.find(s => s.id === stone.id && s.xy);
      if (last && sample.t-previous.t <= step*1.01) {
        ctx.beginPath(); ctx.moveTo(...pos(last.xy)); ctx.lineTo(...p); ctx.stroke(); edges++;
      }
    }
    previous = sample;
  }
  const current = row?.boards[panel].stones.filter(s => s.xy && (typeof selectedStone !== 'function' || selectedStone(panel, s))) || [];
  for (const stone of current) {
    ctx.beginPath(); ctx.arc(...pos(stone.xy), 3, 0, Math.PI*2); ctx.fill();
  }
  if (!current.length) {
    ctx.fillStyle = '#243b48'; ctx.font = '11px system-ui';
    ctx.fillText(observations ? 'No current points; history retained' : 'No projected observations', 8, 35);
  }
  window.boardPlotAudit = window.boardPlotAudit || {};
  window.boardPlotAudit[panel] = {scale, bounds:b, historicalObservations:observations,
    historyEdges:edges, currentPoints:current.length, renderedPoints:rendered,
    width:canvas.width, height:canvas.height, sourceSampleTime:row?.t ?? null};
};
