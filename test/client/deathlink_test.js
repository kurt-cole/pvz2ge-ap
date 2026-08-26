// The DeathLink switch in the AP panel.
//
// Two flags decide it: what the seed was generated with (slot_data) and what
// the player ticked in the panel (cfg.deathLink). The switch must take in BOTH
// directions at once -- a client that stops sending deaths but keeps taking
// them is worse than one that does neither -- and it must never turn DeathLink
// ON for a seed generated without it.
const D = require('./deathlink_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);
const tags = p => (p && p.tags ? p.tags.join(',') : '');
const updates = () => D.sent.filter(p => p.cmd === 'ConnectUpdate');
const bounces = () => D.sent.filter(p => p.cmd === 'Bounce');

// ── the two flags together ───────────────────────────────────────────────────
D.reset({ seed: true, pref: true });
if (!D.deathLinkActive()) fail('seed on + box ticked was not active');
else ok('seed on and box ticked: DeathLink is live');

D.reset({ seed: true, pref: false });
if (D.deathLinkActive()) fail('the panel switch did not turn DeathLink off');
else ok('seed on and box cleared: the panel switch wins');

D.reset({ seed: false, pref: true });
if (D.deathLinkActive()) fail('ticking the box turned DeathLink on for a seed without it');
else ok('seed off: ticking the box cannot opt this slot in');

// A cfg saved before the option existed has no deathLink key at all. Absent
// must read as on, or updating the client would silently disable DeathLink on
// every seed that had it.
D.reset({ seed: true });
if (!D.deathLinkActive()) fail('a cfg with no deathLink key read as off');
else ok('a cfg predating the option keeps DeathLink on');

// ── the tag, which is what the server actually acts on ───────────────────────
D.reset({ seed: true, pref: true });
D.applyDeathLinkPref();
if (updates().length !== 1 || tags(updates()[0]) !== 'AP,DeathLink')
  fail('did not subscribe: ' + JSON.stringify(updates()));
else ok('turning it on sends ConnectUpdate with the DeathLink tag');

D.setPref(false);
D.applyDeathLinkPref();
if (updates().length !== 2 || tags(updates()[1]) !== 'AP')
  fail('did not unsubscribe: ' + JSON.stringify(updates()));
else ok('turning it off sends ConnectUpdate WITHOUT the tag');

// Dropping the tag is the only way to stop incoming deaths, so an off that
// never reaches the server is not an off at all.
D.setPref(true);
D.applyDeathLinkPref();
if (updates().length !== 3 || tags(updates()[2]) !== 'AP,DeathLink')
  fail('turning it back on did not re-subscribe');
else ok('turning it back on re-sends the tag');

D.applyDeathLinkPref();
D.applyDeathLinkPref();
if (updates().length !== 3) fail('re-sent a tag that had not changed');
else ok('no packet when the tag would not change');

// A seed without DeathLink never had the tag, so there is nothing to drop.
D.reset({ seed: false, pref: true });
D.applyDeathLinkPref();
D.setPref(false);
D.applyDeathLinkPref();
if (updates().length) fail('sent a tag update for a seed with no DeathLink');
else ok('a seed without DeathLink sends no tag either way');

// Offline the switch still records the preference; slot_data calls this again
// on the next connect, which is what puts the tag right.
D.reset({ seed: true, pref: true, conn: false });
D.applyDeathLinkPref();
if (D.sent.length) fail('sent a packet while disconnected');
else ok('no packet while disconnected');
D.connect();
D.applyDeathLinkPref();
if (updates().length !== 1 || tags(updates()[0]) !== 'AP,DeathLink')
  fail('the tag did not go out once connected');
else ok('the tag goes out on the next connect');

// ── outgoing: losing a level ─────────────────────────────────────────────────
D.reset({ seed: true, pref: true });
D.sendDeathLink();
if (bounces().length !== 1) fail('losing a level sent no death');
else if (tags(bounces()[0]) !== 'DeathLink') fail('death sent without the DeathLink tag');
else if (bounces()[0].data.source !== 'kurt') fail('death not attributed to this slot');
else ok('losing a level bounces a death to the room');

D.reset({ seed: true, pref: false });
D.sendDeathLink();
if (bounces().length) fail('sent a death with the switch off');
else ok('switch off: losing a level sends nothing');

D.reset({ seed: false, pref: true });
D.sendDeathLink();
if (bounces().length) fail('sent a death on a seed without DeathLink');
else ok('seed off: losing a level sends nothing');

// loseDarken can fire more than once for a single loss.
D.reset({ seed: true, pref: true });
D.sendDeathLink();
D.sendDeathLink();
if (bounces().length !== 1) fail('the debounce did not hold: ' + bounces().length);
else ok('a second loss within 3s is debounced');
D.advance(3001);
D.sendDeathLink();
if (bounces().length !== 2) fail('a later loss was swallowed by the debounce');
else ok('a loss after the debounce window sends again');

// ── incoming: someone else died ──────────────────────────────────────────────
D.reset({ seed: true, pref: true });
let calls = D.enterLevel();
D.applyRemoteDeath({ source: 'someone', cause: 'someone lost a level' });
if (calls.length !== 1) fail('a remote death did not kill the player');
else if (!D.toasts.length) fail('a remote death said nothing');
else ok('a remote death loses the level and toasts');

// The kill runs loseDarken, which is itself hooked to send DeathLink. Without
// the suppression that is an infinite ping-pong between two clients.
if (!D.suppressed()) fail('the outgoing send was not suppressed during the kill');
else {
  D.sendDeathLink();
  if (bounces().length) fail('a remote death bounced straight back out');
  else ok('a remote death does not echo back to the room');
}
D.runTimers();
if (D.suppressed()) fail('suppression was never lifted');
else ok('suppression lifts once the kill is done');

// Not in a level: there is nothing to kill, and it must not throw.
D.reset({ seed: true, pref: true });
D.applyRemoteDeath({ source: 'someone' });
ok('a remote death outside a level is a no-op');

// A death with no cause still has to read as something.
D.reset({ seed: true, pref: true });
calls = D.enterLevel();
D.applyRemoteDeath({ source: 'someone' });
if (!/someone died/.test(calls[0] || '')) fail('a causeless death read as: ' + calls[0]);
else ok('a death with no cause names the player who died');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nDEATHLINK OK');
process.exit(failed ? 1 : 0);
