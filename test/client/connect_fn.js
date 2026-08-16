// Copy of connect() from build_pvzge_ap.py, kept in sync by drift_test.py.
// Do not edit the copied function here -- edit the client and re-copy.
// Everything above and below it is harness scaffolding.

// Module-level state the copied function closes over. Declared here for the
// same reason: it lives outside any function, so drift_test does not see it.
let ws=null, conn=false, rtimer=null, rdelay=5000;
let sessionActive=false, goalSent=false;
let cfg = { server:'localhost:38281', slot:'kurt', password:'' };

const WS_SCHEMES  = ['wss://', 'ws://'];
const WS_SCHEME_RE = /^wss?:\/\//i;
let schemeProbed = false;

const AP_SLOT_IDX_KEY = 'ap_pvz2_slot_idx';

// ── harness stubs ───────────────────────────────────────────────────────────
// Records every URL the client asked for, and lets a test decide whether that
// socket opens or closes unopened -- which is the whole question here.
const attempts = [];
let statuses = [];
let savedCfg = 0;

function setStatus(msg){ statuses.push(msg); }
function log(){}
function toast(){}
function svCfg(){ savedCfg++; }
function onPkt(){}
function findOrCreateAPSlot(){ return 0; }

// connect() short-circuits and reloads unless this key is already set, so the
// harness pretends the slot was made on some earlier run.
const localStorage = {
  _v: { [AP_SLOT_IDX_KEY]: '0' },
  getItem(k){ return Object.prototype.hasOwnProperty.call(this._v,k) ? this._v[k] : null; },
  setItem(k,v){ this._v[k]=String(v); },
};

// Stand-in for the browser WebSocket. Never connects to anything; the test
// drives open/close by hand.
class FakeWebSocket {
  constructor(url){
    this.url = url;
    this.readyState = 0;
    attempts.push(url);
    FakeWebSocket.last = this;
  }
  close(){ this.readyState = 3; }
  // The two outcomes that matter: a handshake that completed, and one the
  // server closed before replying (what ws:// against a TLS-only room does).
  fireOpen(){ this.readyState = 1; if (this.onopen) this.onopen(); }
  fireClose(){ this.readyState = 3; if (this.onclose) this.onclose(); }
}
const WebSocket = FakeWebSocket;

// setTimeout is captured so tests can run the reconnect without real waiting.
const timers = [];
function setTimeout(fn, ms){ timers.push({fn, ms}); return timers.length; }

// ── the copied client function ──────────────────────────────────────────────
function connect() {
    if(!cfg.slot){setStatus('Enter slot name','#fa0');return;}
    // First connect: create the dedicated AP save slot, then reload so the game
    // loads it fresh (the getItem intercept will redirect PlayerIndex going forward).
    if(!localStorage.getItem(AP_SLOT_IDX_KEY)) {
      const apIdx = findOrCreateAPSlot();
      if(apIdx < 0) { setStatus('Could not create AP save slot','#f44'); return; }
      log('AP save slot created at index ' + apIdx + ' — reloading…');
      toast('AP save created — reloading…','#fa0');
      setTimeout(()=>window.location.reload(), 1500);
      return;
    }
    if(ws){try{ws.onclose=null;ws.close();}catch(e){}ws=null;}
    setStatus('Connecting…','#fa0');
    // The address box takes a bare host:port, so the client picks the scheme.
    // Hosted rooms -- multiworld.gg, archipelago.gg -- are TLS only, and answer
    // a plain ws:// handshake by closing the socket before replying, which the
    // browser reports as "Connection closed before receiving a handshake
    // response". A self-hosted or LAN server usually has no certificate and
    // only speaks ws://. So try wss:// first and fall back once, and remember
    // whichever answered so a reconnect does not pay for the probe again.
    const explicit = WS_SCHEME_RE.test(cfg.server);
    const scheme = explicit ? ''
                 : (WS_SCHEMES.indexOf(cfg.scheme) >= 0 ? cfg.scheme : WS_SCHEMES[0]);
    let opened = false;
    try {
      ws=new WebSocket(explicit ? cfg.server : scheme + cfg.server);
      // Only that the socket opened, not that the server liked us -- enough to
      // tell "wrong scheme" apart from "rejected", which is the whole question.
      ws.onopen=()=>{
        opened=true; schemeProbed=false;
        if(!explicit && cfg.scheme!==scheme){ cfg.scheme=scheme; svCfg(); }
      };
      ws.onmessage=e=>{try{JSON.parse(e.data).forEach(onPkt);}catch(ex){}};
      ws.onclose=()=>{
        conn=false;sessionActive=false;goalSent=false;ws=null;setStatus('Disconnected','#f44');
        // Closed without ever opening, on an address that named no scheme: the
        // OTHER scheme is worth one immediate try before the backoff loop, so a
        // plain-ws server is not stuck behind a 5s wait on every attempt. "The
        // other" rather than "the next" matters when cfg.scheme is a remembered
        // ws:// and the player has since moved to a hosted room.
        const alt = (!explicit && !opened && !schemeProbed)
                  ? WS_SCHEMES.find(s => s !== scheme) : null;
        if(alt){
          schemeProbed=true; cfg.scheme=alt; svCfg();
          setStatus('Retrying over '+alt.replace('://','')+'…','#fa0');
          rtimer=setTimeout(connect,300);
          return;
        }
        // Both failed. Clearing the flag in the backoff callback gives every
        // cycle one fresh pair of attempts, so a server that only later comes
        // up with TLS is still found instead of being pinned to the loser.
        rtimer=setTimeout(()=>{
          schemeProbed=false;
          rdelay=Math.min(rdelay*1.5,30000);
          connect();
        },rdelay);
      };
      ws.onerror=()=>{};
    } catch(e) { setStatus('Connection failed: '+e.message,'#f44'); }
  }

// ── harness controls ────────────────────────────────────────────────────────
function reset(server){
  ws=null; conn=false; rtimer=null; rdelay=5000;
  schemeProbed=false;
  cfg = { server: server, slot:'kurt', password:'' };
  attempts.length = 0; timers.length = 0; statuses = []; savedCfg = 0;
}
// Runs the most recently scheduled timer, which is how the client retries.
function runNextTimer(){
  const t = timers.pop();
  timers.length = 0;
  if (t) t.fn();
  return t ? t.ms : null;
}

module.exports = {
  connect, reset, runNextTimer, attempts, timers,
  getCfg: () => cfg,
  getStatuses: () => statuses,
  lastSocket: () => FakeWebSocket.last,
};
