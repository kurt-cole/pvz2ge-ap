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
function installUILoseHook(UI) {
  if (!UI || UI._ap_hooked_ui || !UI.prototype || !UI.prototype.loseDarken) return;
  const _origLoseDarken = UI.prototype.loseDarken;
  UI.prototype.loseDarken = function() {
    // Only the call that actually ends the level is a death. Every later
    // cause calls loseDarken again -- zombies go on eating while the death
    // screen sits there -- and the game ignores those through this very
    // guard, so reading it here is what stops one loss sending a DeathLink
    // every few seconds for as long as the screen is up. With LevelPlay not
    // captured this reads as "first", which is the behaviour it had before.
    const play = window._AP_LevelPlay && window._AP_LevelPlay.component;
    if (!this.paused && !(play && (play.gameLost || play.gameWon))
        && window._AP_onGameLose) window._AP_onGameLose();
    return _origLoseDarken.apply(this, arguments);
  };
  UI._ap_hooked_ui = true;
}

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

// The game's own UI class, near enough: loseDarken ends the level once and
// every later cause calls it again while the death screen sits there. The
// LevelPlay component is where the game keeps the flag that says so.
function gameUI(){
  const play = { gameLost: false, gameWon: false };
  window._AP_LevelPlay = { component: play };
  window._AP_onGameLose = sendDeathLink;
  function UI(){ this.paused = false; }
  UI.prototype.loseDarken = function(){ play.gameLost = true; };
  installUILoseHook(UI);
  installUILoseHook(UI);      // idempotent, as the capture may fire twice
  return new UI();
}

module.exports = { deathLinkActive, applyDeathLinkPref, sendDeathLink,
                   applyRemoteDeath, installUILoseHook, gameUI,
                   reset, enterLevel, sent, toasts, timers,
                   advance: ms => { now += ms; },
                   setPref: v => { cfg.deathLink = v; },
                   setSeed: v => { slotDeathLink = v; },
                   connect: () => { conn = true; },
                   suppressed: () => suppressDeathLinkSend,
                   runTimers: () => { for(const t of timers.splice(0)) t.fn(); } };
