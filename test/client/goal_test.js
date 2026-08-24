// The win condition, and what opens Modern Day.
//
// Two models are live at once. A seed rolled from 2026-08-23 on sets
// modern_day_keyed: Modern Day sits behind its own key like every other world,
// and the run is won by completing worlds_required worlds. An older seed has
// no Modern Day Key in its pool at all -- Modern Day opens on that same count
// instead, and the run ends on one specific Modern Day level. Reading a
// missing flag as "keyed" would leave those seeds with a world nothing can
// ever open, so the absent case is tested as carefully as the present one.
const G = require('./goal_fn.js');

let failed = 0;
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const ok = m => console.log('  ok    ' + m);
const statuses = () => G.sent.filter(p => p.cmd === 'StatusUpdate');

const GOALS = ['egypt8', 'pirate8', 'cowboy8', 'dark10', 'modern16'];
// A keyed seed. worldGates is what a seed generated on or after 2026-08-23
// sends: Modern Day is opened by the first Progressive Modern Day now, and
// the receivedKeys path is only there for a run started before that.
const MD_GATE = { 'Modern Day': { item: 'Progressive Modern Day', stretches: [[]] } };
const keyed = extra => Object.assign(
  { modernKeyed: true, goalLocs: GOALS, worldsReq: 3, receivedKeys: [],
    worldGates: MD_GATE }, extra);
const legacy = extra => Object.assign(
  { goalLocs: GOALS.slice(0, 4), worldsReq: 3,
    victoryLoc: 'modern_zomboss_01_egypt' }, extra);

// ── keyed seed: Modern Day is an ordinary world ──────────────────────────────
G.reset(keyed());
if (G.canAccessModernDay()) fail('Modern Day opened with no key held');
else ok('keyed seed: Modern Day stays shut without its key');

G.reset(keyed({ receivedKeys: ['Pirate Seas Key', 'Dark Ages Key'],
                worldUnlocks: { 'Progressive Pirate Seas': 3 } }));
if (G.canAccessModernDay()) fail('another world\'s unlock opened Modern Day');
else ok('keyed seed: another world\'s unlocks do not open it');

G.reset(keyed({ worldUnlocks: { 'Progressive Modern Day': 1 } }));
if (!G.canAccessModernDay()) fail('the first unlock did not open Modern Day');
else ok('keyed seed: the first Progressive Modern Day opens it');

// The World Key stopped being generated on 2026-08-23, but a run started
// before then still has one in flight and has to keep working.
G.reset(keyed({ receivedKeys: ['Modern Day Key'] }));
if (!G.canAccessModernDay()) fail('a Modern Day Key from an older seed no longer works');
else ok('a Modern Day Key still opens it, for a seed that shipped one');

// The goal count must have nothing to do with access any more, or a player who
// completed the required worlds walks into Modern Day without its key.
G.reset(keyed({ receivedKeys: [] }));
for (const g of GOALS) G.check(g);
if (G.canAccessModernDay()) fail('completing every world opened Modern Day without the key');
else ok('keyed seed: completing worlds does not substitute for the key');

// ── older seed: no key exists, so the count is the only way in ───────────────
G.reset(legacy());
if (G.canAccessModernDay()) fail('older seed opened Modern Day with nothing done');
else ok('older seed: shut until the goal count is met');

G.reset(legacy());
G.check('egypt8'); G.check('pirate8');
if (G.canAccessModernDay()) fail('opened one world short of the requirement');
else ok('older seed: one world short is still shut');
G.check('cowboy8');
if (!G.canAccessModernDay()) fail('did not open once the count was met');
else ok('older seed: the count opens it');

// The flag is absent, not false, on those seeds -- this is the exact shape
// that would strand them if a missing key read as keyed.
G.reset(legacy());
if ('modernKeyed' in G.state()) fail('the legacy fixture set the flag');
else ok('older seed really has no modern_day_keyed key at all');

// Nothing at all yet: slot_data has not landed. Opening on a default here
// would show a world the seed may not even have.
G.reset({});
if (G.canAccessModernDay()) fail('opened Modern Day before slot_data arrived');
else ok('no slot_data yet: Modern Day stays shut');

// ── the win: worlds_required worlds completed ────────────────────────────────
G.reset(keyed());
if (G.goalMet()) fail('the goal was met with nothing checked');
else ok('nothing checked is not a win');

G.reset(keyed());
G.check('egypt8'); G.check('pirate8');
if (G.goalMet()) fail('2 worlds met a requirement of 3');
else if (G.maybeSendGoal()) fail('sent the goal one world short');
else if (statuses().length) fail('a StatusUpdate went out one world short');
else ok('one world short sends nothing');

G.check('dark10');
if (!G.goalMet()) fail('3 worlds did not meet a requirement of 3');
else if (!G.maybeSendGoal()) fail('the goal was not reported');
else if (statuses().length !== 1) fail('expected one StatusUpdate, got ' + statuses().length);
else if (statuses()[0].status !== 30) fail('wrong status: ' + statuses()[0].status);
else ok('the third world completes the run and reports status 30');

// Any worlds, in any order -- Modern Day is not special among them.
G.reset(keyed());
G.check('modern16'); G.check('dark10'); G.check('cowboy8');
if (!G.goalMet()) fail('a win that included Modern Day was not recognised');
else ok('Modern Day counts toward the requirement like any other world');

// slot_data half-landed: goal locations, but no requirement to compare them
// against. "done >= 0" is true with nothing checked, so a missing or zero
// requirement must not read as met -- that would claim the goal on connect,
// before the player had done anything at all.
G.reset({ modernKeyed: true, goalLocs: GOALS });
if (G.goalMet()) fail('a missing worlds_required read as an instant win');
else if (G.maybeSendGoal()) fail('claimed the goal with no requirement to meet');
else ok('goal locations with no requirement is not a win');

G.reset({ modernKeyed: true, goalLocs: GOALS, worldsReq: 0 });
if (G.goalMet()) fail('a worlds_required of 0 read as an instant win');
else ok('a zero requirement is not a win either');

// Checks that are not goal locations must not count, or a world is "complete"
// on the strength of levels the goal never asked for.
G.reset(keyed());
for (const l of ['egypt1', 'egypt2', 'pirate3', 'dark4', 'modern1', 'kongfu8'])
  G.check(l);
if (G.goalMet()) fail('ordinary levels counted toward the goal');
else ok('only the seed\'s own goal locations count');

// Once is once: a repeated check must not re-announce the goal.
G.reset(keyed());
for (const g of GOALS) G.check(g);
G.maybeSendGoal();
G.maybeSendGoal();
G.maybeSendGoal();
if (statuses().length !== 1) fail('sent the goal ' + statuses().length + ' times');
else ok('the goal is announced exactly once per session');

// ── the retry path ───────────────────────────────────────────────────────────
// The threshold is crossed while the socket is down. st.checked survives, the
// StatusUpdate does not, so the next poll after reconnecting has to send it.
G.reset(keyed(), { conn: false });
for (const g of GOALS) G.check(g);
if (G.maybeSendGoal()) fail('sent a StatusUpdate with no socket');
else if (statuses().length) fail('a packet went out while disconnected');
else ok('offline: the goal is not sent');
G.reconnect();
if (!G.maybeSendGoal()) fail('the goal was never retried after reconnecting');
else if (statuses().length !== 1) fail('expected exactly one retry');
else ok('reconnecting sends the goal that was missed');

// Connected but not through the handshake yet: sessionActive gates it, the
// same way it gates location sends.
G.reset(keyed(), { sessionActive: false });
for (const g of GOALS) G.check(g);
if (G.maybeSendGoal()) fail('sent the goal before the session was active');
else ok('a socket without a session sends nothing');

// ── the older seed wins on its one victory location ──────────────────────────
G.reset(legacy());
for (const g of GOALS.slice(0, 4)) G.check(g);
if (G.maybeSendGoal()) fail('an older seed won on the goal count alone');
else ok('older seed: completing worlds is not the win');
G.check('modern_zomboss_01_egypt');
if (!G.maybeSendGoal()) fail('the victory location did not end the run');
else if (statuses().length !== 1) fail('expected one StatusUpdate');
else ok('older seed: the victory location ends the run');

// A seed older still, from before modern_day_victory existed: the Zomboss is
// the fallback, and it has to keep working.
G.reset({ goalLocs: GOALS, worldsReq: 3 });
if (G.victoryLoc() !== 'modern_zomboss_01_egypt')
  fail('fallback victory location is ' + G.victoryLoc());
else ok('a seed with no victory location falls back to the Zomboss');
G.check('modern_zomboss_01_egypt');
if (!G.maybeSendGoal()) fail('the fallback victory location did not end the run');
else ok('older seed: the fallback location ends the run too');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nGOAL OK');
process.exit(failed ? 1 : 0);
