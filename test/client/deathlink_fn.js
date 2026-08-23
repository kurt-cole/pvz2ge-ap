// Harness for the DeathLink switch in the AP panel. See drift_test.py: the
// functions below the dashed line are verbatim copies from build_pvzge_ap.py;
// everything above it stands in for the live client.
const window = {};
let conn = false;
let cfg = { server: 'localhost:38281', slot: 'kurt', password: '', deathLink: true };
let slotDeathLink = false;
let deathLinkTagSent = false;
let suppressDeathLinkSend = false;
let lastDeathLinkSentAt = 0;

const sent = [], toasts = [];
function send(pkts){ for(const p of pkts) sent.push(p); }
function toast(m, c){ toasts.push({ msg: String(m), color: c }); }

// The client debounces on Date.now(); driving it by hand is what lets the
// debounce be tested without a real 3s wait.
let now = 1000000;
const Date = { now: () => now };

// The client hands the timer a closure that clears suppressDeathLinkSend.
// Captured rather than run, so a test can assert the flag is still set while
// the remote death is being applied.
const timers = [];
function setTimeout(fn, ms){ timers.push({ fn, ms }); return timers.length; }

// ── copied verbatim from build_pvzge_ap.py ───────────────────────────────────
function deathLinkActive(){ return slotDeathLink && cfg.deathLink !== false; }

function applyDeathLinkPref(){
  const want = deathLinkActive();
  if(!conn || want === deathLinkTagSent) return;
  deathLinkTagSent = want;
  send([{cmd:'ConnectUpdate', tags: want ? ['AP','DeathLink'] : ['AP']}]);
}

function sendDeathLink(){
  if(!deathLinkActive() || suppressDeathLinkSend) return;
  const now = Date.now();
  if(now - lastDeathLinkSentAt < 3000) return; // debounce: loseDarken can
  lastDeathLinkSentAt = now;                   // fire more than once per loss
  // 'Bounce' is the client->server command; 'Bounced' is what the server
  // sends back out (see the onPkt case). Sending 'Bounced' here is not a
  // command the server recognises, so nothing gets broadcast.
  // No 'games' filter: DeathLink should reach every slot carrying the tag,
  // not just other players of this game.
  send([{cmd:'Bounce', tags:['DeathLink'],
         data:{time: now/1000, source: cfg.slot, cause: cfg.slot+' lost a level'}}]);
}

function applyRemoteDeath(data){
  const inst = window._AP_UI && window._AP_UI.component;
  if(!inst) return; // not currently in a level -- can't kill what isn't running
  // loseDarken is itself hooked to send DeathLink on loss; suppress that
  // while we're the ones triggering it, or this becomes an infinite ping-pong.
  suppressDeathLinkSend = true;
  try { inst.loseDarken(null, data.cause || ((data.source||'Someone')+' died'), ''); }
  catch(e) {}
  setTimeout(()=>{ suppressDeathLinkSend = false; }, 500);
  toast('💀 '+(data.cause || ((data.source||'Someone')+' died')), '#f66');
}

// ── harness controls ─────────────────────────────────────────────────────────
// Rebuilds module scope between cases. `pref` undefined models a cfg written
// before this option existed -- the key is simply absent.
function reset(opts){
  const o = opts || {};
  cfg = { server: 'localhost:38281', slot: 'kurt', password: '' };
  if('pref' in o) cfg.deathLink = o.pref;
  slotDeathLink = !!o.seed;
  conn = o.conn !== false;
  deathLinkTagSent = false;
  suppressDeathLinkSend = false;
  lastDeathLinkSentAt = 0;
  now = 1000000;
  sent.length = 0; toasts.length = 0; timers.length = 0;
  window._AP_UI = null;
}

// Stands in for the game's UI class while a level is running. Records what
// loseDarken was called with, which is how the client kills the player.
function enterLevel(){
  const calls = [];
  window._AP_UI = { component: { loseDarken(a, cause, c){ calls.push(cause); } } };
  return calls;
}

module.exports = { deathLinkActive, applyDeathLinkPref, sendDeathLink,
                   applyRemoteDeath, reset, enterLevel, sent, toasts, timers,
                   advance: ms => { now += ms; },
                   setPref: v => { cfg.deathLink = v; },
                   setSeed: v => { slotDeathLink = v; },
                   connect: () => { conn = true; },
                   suppressed: () => suppressDeathLinkSend,
                   runTimers: () => { for(const t of timers.splice(0)) t.fn(); } };
