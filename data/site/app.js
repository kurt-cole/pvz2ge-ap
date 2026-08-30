/* The viewer. Reads window.DATA from bundle.js, which data/build.py writes.
 *
 * Deliberately dependency-free and deliberately file:// safe -- the bundle is a
 * .js assignment rather than a fetch, so this page opens by double-clicking it
 * with no server and no network. Every view degrades when a measurement is
 * missing: an unmeasured level is GREY, never green, because ranking an
 * unmeasured level as the easiest in the game is the one failure mode that
 * would quietly poison the logic work this is for.
 */
const D = window.DATA;
const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else if (v != null) n.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) n.append(kid);
  return n;
};
const cnsOf = name => D.level_map[name] || name;
const press = name => D.pressure[cnsOf(name)] || {};
const level = name => D.levels[cnsOf(name)] || {};
const reqs = name => D.requirements[cnsOf(name)] || {};

/* Pressure index -> band colour. Six bands, each +0.7 of index (a little over
 * half a doubling), so the palette spans the whole roster rather than saturating
 * on the last world. */
function pcolor(idx) {
  if (idx == null) return 'var(--unmeasured)';
  const b = Math.max(0, Math.min(5, Math.floor(idx / 0.7)));
  return `var(--p${b})`;
}

/* ---------- detail drawer ---------- */
const drawer = $('#detail');
$('#detail .close').onclick = () => drawer.classList.remove('on');
function show(node) {
  const body = $('#detail-body');
  body.replaceChildren(node);
  drawer.classList.add('on');
}

function tokenChip(t) {
  const spec = (D.answers.tokens || {})[t.token] || {};
  return el('span', { class: 'chip ' + (t.severity || 'flavour'), title: t.why || '' },
    t.token);
}

function levelDetail(lvl) {
  const p = press(lvl.name), r = reqs(lvl.name), raw = level(lvl.name);
  const kids = [
    el('h2', {}, lvl.name),
    el('div', { class: 'muted tiny' },
      `${lvl.world} — ${lvl.stretch || 'no stretch'} — ${lvl.kind}` +
      (raw.codename && raw.codename !== lvl.name ? ` — ${raw.codename}` : '')),
  ];
  if (lvl.goal_for && lvl.goal_for.length)
    kids.push(el('div', {}, lvl.goal_for.map(g => el('span', { class: 'chip ok' }, 'goal: ' + g))));

  kids.push(el('h4', {}, 'Pressure'));
  if (!p.measured) {
    kids.push(el('p', { class: 'muted tiny' },
      p.why || 'unmeasured — no wave data. Run build.py with --game.'));
  } else {
    kids.push(el('table', {}, el('tbody', {},
      ...[['peak required DPS', p.peak + ' HP/s'],
          ['sustained (p75)', p.sustained + ' HP/s'],
          ['per usable lane', p.per_lane + ' HP/s × ' + p.usable_rows],
          ['pressure index', p.index],
          ['burst index', p.burst_index],
          ['front loading', p.front_loading],
          ['total HP', p.total_hp],
          ['waves', p.wave_count]]
        .map(([k, v]) => el('tr', {}, el('td', { class: 'muted' }, k), el('td', {}, String(v)))))));
    kids.push(sparkline(p.curve, 400, 70));
  }

  kids.push(el('h4', {}, 'Threats'));
  const tk = (r.tokens || []);
  kids.push(tk.length ? el('div', {}, tk.map(tokenChip))
                      : el('p', { class: 'muted tiny' }, 'none recorded'));
  for (const t of tk) {
    kids.push(el('div', { class: 'tiny', style: 'margin:4px 0 8px' },
      el('code', {}, t.token), ' ', el('span', { class: 'muted' }, t.why || ''),
      el('div', {}, (t.answers || []).length
        ? t.answers.slice(0, 14).map(n => el('span', { class: 'chip ok' }, n))
        : el('span', { class: 'chip hard' }, 'nothing in the pool answers this')),
      t.current_rule ? el('div', { class: 'muted' }, 'current rule: ' + t.current_rule) : null));
  }

  if ((r.must || []).length) {
    kids.push(el('h4', {}, 'Proposed hard requirement'));
    kids.push(el('p', { class: 'tiny muted' },
      'One any-of group per fatal threat — the shape WORLD_ENTRY_PLANTS already uses.'));
    kids.push(el('pre', { class: 'tiny' },
      r.must.map(g => `${g.token}: any of ${g.any_of.length} plant(s)`).join('\n')));
  }
  if (!r.gateable)
    kids.push(el('p', { class: 'chip warn' },
      'NOT gateable: selection is ' + r.selection + ' — the player does not pick the plants'));

  if ((raw.waves || []).length) {
    kids.push(el('h4', {}, 'Waves'));
    kids.push(el('div', { class: 'scroll' }, el('table', {},
      el('thead', {}, el('tr', {}, ...['#', 'at', 'HP', 'pts', 'zombies'].map(h => el('th', {}, h)))),
      el('tbody', {}, raw.waves.map(w => el('tr', {},
        el('td', {}, String(w.index + (w.flag ? ' ⚑' : ''))),
        el('td', {}, w.at + 's'), el('td', {}, String(w.spawn_hp)),
        el('td', {}, String(w.spawn_points)),
        el('td', { class: 'tiny muted' },
          Object.entries(w.zombies).map(([z, n]) => `${z}×${n}`).join(', '))))))));
  }
  return el('div', {}, kids);
}

function sparkline(curve, w, h) {
  if (!curve || !curve.length) return el('div');
  const max = Math.max(...curve) || 1;
  const pts = curve.map((v, i) =>
    `${(i / (curve.length - 1)) * w},${h - (v / max) * (h - 4) - 2}`).join(' ');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.setAttribute('height', h);
  svg.innerHTML =
    `<polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="1.5"/>` +
    `<text x="2" y="11" font-size="10" fill="var(--dim)">${Math.round(max)} HP/s peak</text>`;
  return svg;
}

/* ---------- levels view ---------- */
function renderLevels() {
  const root = $('#v-levels');
  const worlds = {};
  for (const l of D.logic.levels) {
    if (l.kind === 'shop') continue;
    (worlds[l.world] ||= []).push(l);
  }
  const kindSel = el('select', { onchange: draw },
    ...['all', 'level', 'dangerroom', 'sidepath', 'victory']
      .map(k => el('option', { value: k }, k)));
  const holder = el('div');
  root.replaceChildren(
    el('p', { class: 'note' },
      'Every level, in play order, coloured by pressure index (log2 of required HP/s per ' +
      'lane against the first level of the game). Grey is UNMEASURED, not easy. ' +
      'Gaps mark the stretch boundaries generation actually cuts on; a blue border is a ' +
      'goal level; a yellow dot means the level carries a hard threat token.'),
    el('div', { class: 'controls' }, el('label', { class: 'muted' }, 'kind '), kindSel),
    legend(), holder);

  function draw() {
    const want = kindSel.value;
    holder.replaceChildren(...Object.entries(worlds).map(([world, list]) => {
      const rows = list.filter(l => want === 'all' || l.kind === want)
        .sort((a, b) => (a.order ?? 1e9) - (b.order ?? 1e9));
      if (!rows.length) return null;
      const cells = [];
      let lastStretch = null;
      for (const l of rows) {
        if (lastStretch !== null && l.stretch !== lastStretch)
          cells.push(el('div', { class: 'stretchgap' }));
        lastStretch = l.stretch;
        const p = press(l.name), r = reqs(l.name);
        const hard = (r.must || []).length > 0;
        cells.push(el('div', {
          class: 'cell' + (l.goal_for && l.goal_for.length ? ' goal' : ''),
          style: `background:${pcolor(p.index)}`,
          title: `${l.name}\n${l.stretch}\n` +
                 (p.measured ? `index ${p.index}, peak ${p.peak} HP/s` : 'unmeasured'),
          onclick: e => { document.querySelectorAll('.cell.sel').forEach(c => c.classList.remove('sel'));
                          e.currentTarget.classList.add('sel'); show(levelDetail(l)); },
        }, hard ? el('span', { class: 'dot' }) : null));
      }
      return el('div', { class: 'worldrow' },
        el('h3', {}, `${world}  `, el('span', { class: 'muted tiny' }, `${rows.length} levels`)),
        el('div', { class: 'cells' }, cells));
    }).filter(Boolean));
  }
  draw();
}

function legend() {
  const sw = (v, t) => el('span', {}, el('span', { class: 'sw', style: `background:${v}` }), t);
  return el('div', { class: 'legend' },
    sw('var(--unmeasured)', 'unmeasured'), sw('var(--p0)', 'index <0.7'),
    sw('var(--p1)', '0.7'), sw('var(--p2)', '1.4'), sw('var(--p3)', '2.1'),
    sw('var(--p4)', '2.8'), sw('var(--p5)', '3.5+'));
}

/* ---------- plants view ---------- */
function renderPlants() {
  const root = $('#v-plants');
  const plants = Object.values(D.plants);
  const roles = [...new Set(plants.flatMap(p => Object.keys(p.roles)))].sort();
  const elements = [...new Set(plants.flatMap(p => p.elements))].sort();
  const filter = el('input', { placeholder: 'filter by name, role, flag, element', oninput: draw });
  const minBand = el('select', { onchange: draw },
    ...['b1', 'b2', 'b3', 'b4', 'b5'].map(b => el('option', { value: b }, 'band ≥ ' + b)));
  const holder = el('div', { class: 'matrix' });
  root.replaceChildren(
    el('p', { class: 'note' },
      'Element × role. A plant appears in every cell it qualifies for — the classes ' +
      'are not exclusive, which is the point: Torchwood is fire support AND a warmth source, ' +
      'and a rule may reach it either way. Purple means the band is CURATED judgement; ' +
      'plain means it was measured out of the game sheets.'),
    el('div', { class: 'controls' }, filter, minBand), holder);

  function draw() {
    const q = filter.value.toLowerCase();
    const bmin = minBand.value;
    const ok = p => !q || p.name.toLowerCase().includes(q) ||
      Object.keys(p.roles).some(r => r.includes(q)) ||
      p.elements.some(e => e.includes(q)) || p.flags.some(f => f.includes(q));
    const pass = (p, r) => p.roles[r] && p.roles[r] >= bmin;
    holder.replaceChildren(el('table', {},
      el('thead', {}, el('tr', {}, el('th', {}, ''), ...roles.map(r => el('th', {}, r)))),
      el('tbody', {}, elements.map(e => el('tr', {},
        el('th', {}, e),
        ...roles.map(r => el('td', {}, plants
          .filter(p => ok(p) && p.elements.includes(e) && pass(p, r))
          .map(p => el('span', {
            class: 'pname tiny' + (p.provenance['role:' + r] === 'curated' ? ' chip curated' : ' chip'),
            onclick: () => show(plantDetail(p)),
          }, `${p.name} ${p.roles[r]}`)))))))));
  }
  draw();
}

function plantDetail(p) {
  const answers = Object.entries(D.answers.tokens)
    .filter(([, spec]) => (D.requirements && true) &&
      Object.values(D.requirements).some(r =>
        (r.must || []).some(g => g.any_of.includes(p.name))))
    .map(([t]) => t);
  const gates = Object.values(D.requirements)
    .flatMap(r => (r.tokens || []).filter(t => (t.answers || []).includes(p.name)).map(t => t.token));
  return el('div', {},
    el('h2', {}, p.name), el('div', { class: 'muted tiny' }, p.cns),
    el('h4', {}, 'Classes'),
    el('div', {}, p.elements.map(e => el('span', { class: 'chip' }, e))),
    el('div', {}, Object.entries(p.roles).map(([r, b]) =>
      el('span', { class: 'chip' + (p.provenance['role:' + r] === 'curated' ? ' curated' : ' ok') },
        `${r} ${b}`))),
    el('div', {}, p.flags.map(f => el('span', { class: 'chip warn' }, f))),
    el('h4', {}, 'Stats'),
    el('table', {}, el('tbody', {}, ...[['sun', p.sun_cost], ['recharge', p.recharge],
      ['dps', p.dps], ['burst', p.burst], ['measured', p.measured]]
      .map(([k, v]) => el('tr', {}, el('td', { class: 'muted' }, k),
        el('td', {}, v == null ? '—' : String(v)))))),
    el('h4', {}, 'Named by generation'),
    p.ap_lists.length ? el('div', {}, p.ap_lists.map(l => el('span', { class: 'chip ok' }, l)))
                      : el('p', { class: 'muted tiny' }, 'in no logic list — pure filler today'),
    el('h4', {}, 'Answers these threats'),
    el('div', {}, [...new Set(gates)].map(t => el('span', { class: 'chip' }, t))));
}

/* ---------- threats view ---------- */
function renderThreats() {
  const root = $('#v-threats');
  const counts = {};
  for (const r of Object.values(D.requirements))
    for (const t of r.tokens || []) counts[t.token] = (counts[t.token] || 0) + 1;
  const rows = Object.entries(D.answers.tokens).map(([token, spec]) => {
    const sample = Object.values(D.requirements)
      .flatMap(r => (r.tokens || []).filter(t => t.token === token))[0];
    return el('tr', {},
      el('td', {}, el('span', { class: 'chip ' + spec.severity }, token)),
      el('td', {}, String(counts[token] || 0)),
      el('td', { class: 'muted' }, spec.why || ''),
      el('td', {}, spec.current_rule
        ? el('code', {}, spec.current_rule)
        : el('span', { class: 'chip warn' }, 'no rule models this')),
      el('td', { class: 'tiny' }, (sample && sample.answers || []).length
        ? (sample.answers.length + ' plants: ' + sample.answers.slice(0, 6).join(', ') +
           (sample.answers.length > 6 ? '…' : ''))
        : el('span', { class: 'chip hard' }, 'nothing answers this')));
  });
  root.replaceChildren(
    el('p', { class: 'note' },
      'Every threat token, how many levels carry it, and whether generation models it today. ' +
      'A "no rule models this" row on a HARD token is a logic gap: levels demand it and ' +
      'nothing in rules.py asks for it.'),
    el('table', {}, el('thead', {}, el('tr', {},
      ...['token', 'levels', 'why it matters', 'current rule', 'what answers it']
        .map(h => el('th', {}, h)))), el('tbody', {}, rows)));
}

/* ---------- side paths ---------- */
function renderSidepaths() {
  const root = $('#v-sidepaths');
  const rows = D.sidepaths.filter(p => p.stages.length).map(p => el('tr', {},
    el('td', {}, p.name),
    el('td', { class: 'muted' }, p.world || '—'),
    el('td', {}, p.unlock_level ? el('code', {}, p.unlock_level) : '—'),
    el('td', {}, p.unlock_index == null ? '—' : String(p.unlock_index)),
    el('td', {}, String(p.stages.length)),
    el('td', {}, (p.stages_detail || []).map(s => el('span', {
      class: 'chip', style: `border-color:${pcolor(s.index)}`,
      title: s.plays_like ? 'plays like ' + s.plays_like : 'unmeasured',
      onclick: () => { const l = D.logic.levels.find(x => x.name === s.name); if (l) show(levelDetail(l)); },
    }, s.index == null ? s.name.split(' ').pop() : String(s.index)))),
    el('td', {}, p.max_spike == null ? '—'
      : el('span', { class: 'chip ' + (p.max_spike > 1 ? 'hard' : 'soft') }, '+' + p.max_spike)),
    el('td', { class: 'tiny' }, p.hardest_stage || '—'),
    // null here is a finding, not a gap: nothing on the main path ever settles
    // this heavy, so there is no level to gate it behind.
    el('td', {}, p.suggested_deep_gate ? el('code', {}, p.suggested_deep_gate)
      : p.hardest_stage ? el('span', { class: 'chip hard' }, 'beyond the main path')
      : '—')));
  root.replaceChildren(
    el('p', { class: 'note' },
      'The steep-side-path problem, stated. Each path is ONE flat region gated on the level ' +
      'that reveals it, so every stage is in logic the moment the first is. "spike" is how ' +
      'much pressure index the hardest stage adds over that unlock level; "plays like" is the ' +
      'main-path level of equivalent pressure: the point where that much pressure becomes ' +
      'NORMAL on the main path, on a rolling median, not the first level to spike that high. ' +
      'A path with a spike above +1 is more than twice the pressure it is gated at and wants ' +
      'splitting rather than one gate. "beyond the main path" means nothing in the main game ' +
      'ever settles that heavy.'),
    el('table', {}, el('thead', {}, el('tr', {},
      ...['path', 'world', 'unlock level', 'unlock idx', 'stages', 'stage indices',
          'max spike', 'hardest stage', 'plays like'].map(h => el('th', {}, h)))),
      el('tbody', {}, rows)));
}

/* ---------- logic graph ---------- */
function renderLogic() {
  const root = $('#v-logic');
  const nodes = new Map();
  for (const e of D.logic.edges) { nodes.set(e.from, null); nodes.set(e.to, null); }
  // Depth = longest path from Menu, so stretches line up in columns.
  const depth = new Map([['Menu', 0]]);
  for (let pass = 0; pass < 8; pass++)
    for (const e of D.logic.edges)
      if (depth.has(e.from))
        depth.set(e.to, Math.max(depth.get(e.to) ?? 0, depth.get(e.from) + 1));
  const cols = {};
  for (const [n, d] of depth) (cols[d] ||= []).push(n);

  const CW = 210, RH = 26;
  const height = Math.max(...Object.values(cols).map(c => c.length)) * RH + 40;
  const width = (Object.keys(cols).length) * CW + 40;
  const pos = new Map();
  for (const [d, list] of Object.entries(cols))
    list.sort().forEach((n, i) => pos.set(n, [20 + d * CW, 24 + i * RH]));

  const svgns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('width', width);
  let html = '';
  for (const e of D.logic.edges) {
    const a = pos.get(e.from), b = pos.get(e.to);
    if (!a || !b) continue;
    const gated = e.requires.length ? 'var(--warn)' : 'var(--line)';
    html += `<path class="edge" stroke="${gated}" d="M${a[0] + 180},${a[1]} C${a[0] + 200},${a[1]} ${b[0] - 20},${b[1]} ${b[0]},${b[1]}"/>`;
  }
  for (const [n, [x, y]] of pos) {
    const edge = D.logic.edges.find(e => e.to === n);
    const nreq = edge ? edge.requires.length : 0;
    html += `<g class="node" data-node="${n}"><rect x="${x}" y="${y - 10}" width="180" height="20"/>` +
      `<text x="${x + 7}" y="${y + 4}">${n}${nreq ? '  ●' + nreq : ''}</text></g>`;
  }
  svg.innerHTML = html;
  svg.addEventListener('click', ev => {
    const g = ev.target.closest('[data-node]');
    if (g) show(nodeDetail(g.dataset.node));
  });
  root.replaceChildren(
    el('p', { class: 'note' },
      'The region graph rules.py really builds, read out of constants.py rather than ' +
      'restated. An orange edge carries an access rule; the dot count is how many separate ' +
      'requirements stack on that entrance. Click a node for the rules on the way in.'),
    el('div', { class: 'scroll' }, svg));
}

function nodeDetail(name) {
  const incoming = D.logic.edges.filter(e => e.to === name);
  const here = D.logic.levels.filter(l => l.stretch === name || l.region === name);
  return el('div', {},
    el('h2', {}, name),
    el('h4', {}, 'Requirements on the way in'),
    incoming.length ? incoming.map(e => el('div', { style: 'margin-bottom:8px' },
      el('div', { class: 'tiny muted' }, e.name || `${e.from} → ${e.to}`),
      e.requires.length ? e.requires.map(r => el('div', { class: 'tiny' },
        el('span', { class: 'chip ' + (r.kind === 'item' ? 'ok' : 'soft') }, r.kind),
        r.text, r.per_slot ? el('span', { class: 'chip warn' }, 'per-slot draw') : null,
        el('div', { class: 'muted tiny' }, r.source),
        r.plants.length ? el('div', { class: 'tiny muted' },
          r.plants.slice(0, 10).join(', ') + (r.plants.length > 10 ? ` … (${r.plants.length})` : '')) : null))
        : el('div', { class: 'chip ok' }, 'no rule — open'))) : el('p', { class: 'muted' }, 'no entrance'),
    el('h4', {}, `Locations here (${here.length})`),
    el('div', { class: 'tiny muted' }, here.slice(0, 60).map(l => l.name).join(', ')));
}

/* ---------- about ---------- */
function renderAbout() {
  const c = D.coverage;
  $('#v-about').replaceChildren(
    el('p', { class: 'note' },
      'Built by data/build.py. Everything on these pages is either read out of the apworld ' +
      '(the real logic) or measured out of a game checkout (the real numbers); where a number ' +
      'is judgement it is marked curated. Rebuild with: python data/build.py --game <checkout>'),
    el('table', {}, el('tbody', {}, ...Object.entries(c)
      .filter(([k]) => k !== 'objclasses' && k !== 'unresolved_sample' && k !== 'files_failed_sample')
      .map(([k, v]) => el('tr', {}, el('td', { class: 'muted' }, k),
        el('td', {}, el('code', {}, JSON.stringify(v).slice(0, 300))))))));
}

/* ---------- boot ---------- */
const tier = $('#tier');
tier.textContent = D.coverage.tier === 'measured'
  ? `measured — ${D.coverage.levels_measured} levels`
  : 'STRUCTURE ONLY — no game checkout; pressure is unmeasured';
tier.className = D.coverage.tier;

renderLevels(); renderPlants(); renderThreats(); renderSidepaths(); renderLogic(); renderAbout();
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.view').forEach(v =>
    v.classList.toggle('on', v.id === 'v-' + b.dataset.view));
});
