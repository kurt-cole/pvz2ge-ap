// Drives the REAL connect() from build_pvzge_ap.py against a fake WebSocket.
//
// The bug this covers: the client hardcoded ws://, so every hosted room
// (multiworld.gg, archipelago.gg) failed with "Connection closed before
// receiving a handshake response" and retried forever on a growing backoff.
const C = require('./connect_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);

const HOSTED = 'multiworld.gg:56691';
const LOCAL  = 'localhost:38281';

// ── a bare address tries wss:// first ───────────────────────────────────────
C.reset(HOSTED);
C.connect();
if (C.attempts[0] !== 'wss://' + HOSTED)
  fail(`first attempt was ${C.attempts[0]}, expected wss://${HOSTED}`);
else ok('a bare address is tried over wss:// first');

// ── TLS-only server: opens, so no fallback and the scheme is remembered ─────
C.lastSocket().fireOpen();
if (C.getCfg().scheme !== 'wss://') fail('a successful wss:// connect was not remembered');
else ok('the working scheme is remembered for next time');

C.reset(HOSTED);
C.getCfg().scheme = 'wss://';
C.connect();
if (C.attempts.length !== 1 || C.attempts[0] !== 'wss://' + HOSTED)
  fail('a remembered scheme was not reused: ' + JSON.stringify(C.attempts));
else ok('a remembered scheme skips the probe');

// ── plain-ws server: wss fails unopened, ws is tried immediately ────────────
C.reset(LOCAL);
C.connect();
C.lastSocket().fireClose();                 // closed before opening
if (C.attempts.length !== 1) fail('fell back without waiting for the close');
const waited = C.runNextTimer();            // the immediate retry
if (C.attempts[1] !== 'ws://' + LOCAL)
  fail(`fallback attempt was ${C.attempts[1]}, expected ws://${LOCAL}`);
else if (waited !== 300)
  fail(`fallback waited ${waited}ms, expected the short 300ms probe`);
else ok('a failed wss:// falls back to ws:// immediately (300ms, not the backoff)');

C.lastSocket().fireOpen();
if (C.getCfg().scheme !== 'ws://') fail('the ws:// fallback was not remembered');
else ok('the ws:// fallback is remembered too');

// ── moving from a local server to a hosted one recovers ─────────────────────
// The remembered scheme is now ws://, so the fallback has to try the OTHER
// scheme rather than the next one in the list.
C.reset(HOSTED);
C.getCfg().scheme = 'ws://';
C.connect();
if (C.attempts[0] !== 'ws://' + HOSTED) fail('did not start from the remembered scheme');
C.lastSocket().fireClose();
C.runNextTimer();
if (C.attempts[1] !== 'wss://' + HOSTED)
  fail(`did not fall back to wss://, got ${C.attempts[1]}`);
else ok('a remembered ws:// still falls back to wss:// for a hosted room');

// ── both schemes down: one probe per cycle, then backoff ────────────────────
C.reset(HOSTED);
C.connect();
C.lastSocket().fireClose();      // wss fails
C.runNextTimer();
C.lastSocket().fireClose();      // ws fails too
if (C.attempts.length !== 2) fail('probed more than twice in one cycle');
else ok('an unreachable server is probed once per scheme, not in a loop');

const backoff = C.runNextTimer();
if (backoff !== 5000) fail(`backoff was ${backoff}ms, expected the 5000ms retry`);
else ok('after both schemes fail it falls into the normal backoff');
// and that new cycle gets a fresh probe rather than being pinned to the loser
C.lastSocket().fireClose();
C.runNextTimer();
if (C.attempts.length < 4) fail('the new cycle did not probe again');
else ok('each backoff cycle gets a fresh pair of attempts');

// ── an explicit scheme is honoured exactly, with no probing ─────────────────
for (const url of ['wss://' + HOSTED, 'ws://' + LOCAL]) {
  C.reset(url);
  C.connect();
  if (C.attempts[0] !== url) fail(`explicit ${url} was rewritten to ${C.attempts[0]}`);
  C.lastSocket().fireClose();
  const ms = C.runNextTimer();
  if (C.attempts.length > 1 && C.attempts[1] !== url)
    fail(`explicit ${url} was overridden on retry with ${C.attempts[1]}`);
  else if (ms !== 5000)
    fail(`explicit ${url} probed instead of backing off (${ms}ms)`);
  else ok(`an explicit ${url.split(':')[0]}:// address is used exactly as typed`);
}

// ── the original symptom, end to end ────────────────────────────────────────
// Before the fix the only URL ever tried was ws://multiworld.gg:56691, which
// is what filled the console with handshake failures.
C.reset(HOSTED);
C.connect();
if (C.attempts.some(u => u.startsWith('ws://')))
  fail('still opening with plain ws:// against a hosted room');
else ok('a hosted room is never contacted over plain ws:// first');

// ── a live session that drops gets a grace period ─────────────────────────
// A drop mid-game retries at once and counts down GRACE_SECS before giving up
// to the title screen, rather than reloading on the spot.
function dropMidGame(){
  C.reset(HOSTED);
  C.getCfg().scheme = 'wss://';
  C.connect();
  C.lastSocket().fireOpen();
  C.activate();
  C.lastSocket().fireClose();
}

dropMidGame();
if (C.menuReturns.length) fail('a mid-game drop went straight to the title screen');
else if (!C.inGrace()) fail('a mid-game drop did not start the grace period');
else if (C.attempts.length !== 2) fail(`a mid-game drop did not retry at once (${C.attempts.length} attempts)`);
else ok('a mid-game drop starts a grace period and retries immediately');

// Reconnecting inside the window keeps the player in the level.
C.lastSocket().fireOpen();
C.connected();
for (let i = 0; i < 12; i++) C.runTimer(1000);
if (C.menuReturns.length) fail('a reconnect inside the grace period still left the level');
else if (C.inGrace()) fail('the countdown kept running after the reconnect');
else ok('reconnecting within the grace period keeps the player in the level');

// Retries inside the window are quick and do not probe the other scheme.
dropMidGame();
C.lastSocket().fireClose();                 // the immediate retry fails
if (!C.timers.some(t => t.ms === 2000)) fail('a failed grace retry did not schedule the 2s retry');
else if (C.timers.some(t => t.ms === 300 || t.ms === 5000)) fail('a grace retry probed or backed off');
else ok('a failed retry in the grace period tries again in 2s on the same scheme');
C.runTimer(2000);
if (C.attempts[2] !== 'wss://' + HOSTED) fail(`grace retry went to ${C.attempts[2]}`);
else ok('grace retries stay on the scheme the session used');

// The server never comes back: after 10 ticks, the title screen (resuming).
dropMidGame();
for (let i = 0; i < 9; i++) {
  C.runTimer(1000);
  if (C.lastSocket().readyState === 0 && i % 2) { C.lastSocket().fireClose(); C.runTimer(2000); }
}
if (C.menuReturns.length) fail('gave up before the grace period ran out');
C.runTimer(1000);
if (C.menuReturns.length !== 1 || C.menuReturns[0] !== true)
  fail(`after the grace period menuReturns was ${JSON.stringify(C.menuReturns)}, expected [true]`);
else if (C.timers.length) fail('timers were left running after giving up: ' + JSON.stringify(C.timers.map(t=>t.ms)));
else ok('no reconnect within 10s returns to the title screen and resumes from there');
if (C.toasts.filter(t => /reconnecting/.test(t)).length !== 10)
  fail('the countdown was not shown each second');
else ok('the countdown is shown each second');

// A failed attempt is not a session: it keeps the ordinary retry loop, so a
// server that is down cannot reload the page on every attempt.
C.reset(HOSTED);
C.connect();
C.lastSocket().fireClose();
if (C.menuReturns.length) fail('a failed connect attempt reloaded the page');
else ok('a failed attempt retries in place without leaving the title screen');

// On the title screen a drop has nothing to leave: it retries in place.
// Reloading here is what looped, since the reload reconnects and lands here.
C.reset(HOSTED);
C.setInGame(false);
C.connect();
C.lastSocket().fireOpen();
C.activate();
C.lastSocket().fireClose();
if (C.menuReturns.length) fail('a drop on the title screen reloaded the page');
else if (C.timers.length !== 1) fail('a drop on the title screen did not schedule a retry');
else ok('a drop on the title screen retries in place instead of reloading');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nCONNECT SCHEME OK');
process.exit(failed ? 1 : 0);
