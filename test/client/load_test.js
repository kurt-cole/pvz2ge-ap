// Executes the ENTIRE injected client once, under stubs, purely to see whether
// it survives being loaded.
//
// This exists because the other JS suites cannot catch a whole class of bug.
// They require *_fn.js, which holds copies of individual functions, so nothing
// ever runs the client as one program. `node --check` parses it but never
// executes it, so it is blind to:
//
//   - a `let`/`const` read from a function that runs earlier in the module
//     body (temporal dead zone), which throws at load and kills the client
//   - a call to a function that was never defined -- log() was called in three
//     places for months without existing
//   - anything else that throws while the top level is running
//
// A dead client looks exactly like a working one until you play the game, and
// finding out costs a full Electron rebuild. This is the cheap version of that.
//
// Scope: the SYNCHRONOUS top level only. Whatever the client defers to a timer
// builds real DOM, which is well past what is worth stubbing, so timers are
// never allowed to fire.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const CLIENT_SRC = path.join(__dirname, '..', '..', 'pvz2gardendless', 'build_pvzge_ap.py');

// Pull the client out of the Python string it lives in. Delimiters rather than
// line numbers: the end line moves with every edit.
function extractClient() {
  const py = fs.readFileSync(CLIENT_SRC, 'utf8');
  const open = py.indexOf('TMPPATCH_CONTENT = r"""');
  if (open < 0) throw new Error('TMPPATCH_CONTENT not found in build_pvzge_ap.py');
  const start = open + 'TMPPATCH_CONTENT = r"""'.length;
  const end = py.indexOf('"""', start);
  if (end < 0) throw new Error('unterminated TMPPATCH_CONTENT string');
  return py.slice(start, end);
}

const noop = () => {};

// A DOM element that answers anything asked of it, so the client can build its
// overlay without a real document.
const el = () => new Proxy({
  style: {}, dataset: {}, children: [],
  classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
  appendChild: noop, removeChild: noop, remove: noop, setAttribute: noop,
  addEventListener: noop, removeEventListener: noop, getContext: () => ({}),
  focus: noop, blur: noop, click: noop,
}, {
  get: (t, k) => (k in t ? t[k]
                 : (typeof k === 'string' && k.startsWith('on') ? null : el())),
  set: () => true,
});

const store = {};
function Storage() {}
Storage.prototype.getItem = function (k) { return k in store ? store[k] : null; };
Storage.prototype.setItem = function (k, v) { store[k] = String(v); };
Storage.prototype.removeItem = function (k) { delete store[k]; };

// Timers are recorded, never run: see the scope note above.
const deferred = [];

const sandbox = {
  console: { log: noop, warn: noop, error: noop, info: noop, debug: noop },
  setTimeout: (fn) => { deferred.push(fn); return deferred.length; },
  setInterval: (fn) => { deferred.push(fn); return deferred.length; },
  clearTimeout: noop, clearInterval: noop,
  queueMicrotask: noop,
  Promise, JSON, Math, Date, Set, Map, Object, Array, String, Number, Boolean,
  RegExp, Error, Proxy, Reflect, isNaN, parseInt, parseFloat, encodeURIComponent,
  Storage,
  localStorage: new Storage(),
  sessionStorage: new Storage(),
  document: new Proxy({
    createElement: el, createTextNode: el, getElementById: () => null,
    querySelector: () => null, querySelectorAll: () => [],
    addEventListener: noop, body: el(), head: el(), readyState: 'complete',
  }, { get: (t, k) => (k in t ? t[k] : el()) }),
  navigator: { userAgent: 'node', platform: 'test' },
  location: { href: 'file:///game', protocol: 'file:', hostname: '' },
  WebSocket: function () { this.close = noop; this.send = noop; },
  fetch: () => Promise.resolve({ json: () => Promise.resolve({}), text: () => Promise.resolve('') }),
  System: { register: noop },
  requestAnimationFrame: (fn) => { deferred.push(fn); return deferred.length; },
  cancelAnimationFrame: noop,
  performance: { now: () => 0 },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
sandbox.top = sandbox;

let failed = 0;
const fail = (m) => { failed++; console.log('  FAIL  ' + m); };
const ok = (m) => console.log('  ok    ' + m);

let src;
try {
  src = extractClient();
  ok(`extracted ${src.split('\n').length} lines of client from build_pvzge_ap.py`);
} catch (e) {
  fail('could not extract the client: ' + e.message);
  console.log('\n1 FAILURE(S)');
  process.exit(1);
}

try {
  vm.runInNewContext(src, sandbox, { filename: 'tmpPatch.js', timeout: 10000 });
  ok('the whole client executes without throwing (no TDZ, no undefined call)');
} catch (e) {
  const where = (e.stack || '').split('\n').slice(0, 3).join('\n      ');
  fail(`the client threw while loading -- it would be dead in game:\n      ${where}`);
}

// The hooks the game and the AP layer reach the client through. If the top
// level ran but one of these never got installed, the client is loaded and
// still does nothing.
for (const name of ['_AP_shopRewardLabel', '_AP_isShopCommodityChecked',
                    '_AP_onShopPurchase']) {
  if (typeof sandbox[name] !== 'function') fail(`window.${name} was not installed`);
}
if (!failed) ok('the window hooks the game calls into are all installed');

if (deferred.length) ok(`${deferred.length} deferred callback(s) left unrun, as intended`);

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCLIENT LOADS CLEAN');
process.exit(failed ? 1 : 0);
