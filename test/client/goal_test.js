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
// What actually happens in game: the level is beaten, and THAT is what
// fires the check. Kept as one helper so a test cannot advance the goal
// by accident with a check alone -- see the 'checked but not played'
// cases at the end of this file, which rely on the two being separable.
const beat = loc => { G.play(loc); G.check(loc); };

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
for (const g of GOALS) beat(g);
if (G.canAccessModernDay()) fail('completing every world opened Modern Day without the key');
else ok('keyed seed: completing worlds does not substitute for the key');

// ── older seed: no key exists, so the count is the only way in ───────────────
G.reset(legacy());
if (G.canAccessModernDay()) fail('older seed opened Modern Day with nothing done');
else ok('older seed: shut until the goal count is met');

G.reset(legacy());
beat('egypt8'); beat('pirate8');
if (G.canAccessModernDay()) fail('opened one world short of the requirement');
else ok('older seed: one world short is still shut');
beat('cowboy8');
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
beat('egypt8'); beat('pirate8');
if (G.goalMet()) fail('2 worlds met a requirement of 3');
else if (G.maybeSendGoal()) fail('sent the goal one world short');
else if (statuses().length) fail('a StatusUpdate went out one world short');
else ok('one world short sends nothing');

beat('dark10');
if (!G.goalMet()) fail('3 worlds did not meet a requirement of 3');
else if (!G.maybeSendGoal()) fail('the goal was not reported');
else if (statuses().length !== 1) fail('expected one StatusUpdate, got ' + statuses().length);
else if (statuses()[0].status !== 30) fail('wrong status: ' + statuses()[0].status);
else ok('the third world completes the run and reports status 30');

// Any worlds, in any order -- Modern Day is not special among them.
G.reset(keyed());
beat('modern16'); beat('dark10'); beat('cowboy8');
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
  beat(l);
if (G.goalMet()) fail('ordinary levels counted toward the goal');
else ok('only the seed\'s own goal locations count');

// Once is once: a repeated check must not re-announce the goal.
G.reset(keyed());
for (const g of GOALS) beat(g);
G.maybeSendGoal();
G.maybeSendGoal();
G.maybeSendGoal();
if (statuses().length !== 1) fail('sent the goal ' + statuses().length + ' times');
else ok('the goal is announced exactly once per session');

// ── the retry path ───────────────────────────────────────────────────────────
// The threshold is crossed while the socket is down. st.checked survives, the
// StatusUpdate does not, so the next poll after reconnecting has to send it.
G.reset(keyed(), { conn: false });
for (const g of GOALS) beat(g);
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
for (const g of GOALS) beat(g);
if (G.maybeSendGoal()) fail('sent the goal before the session was active');
else ok('a socket without a session sends nothing');

// ── the older seed wins on its one victory location ──────────────────────────
G.reset(legacy());
for (const g of GOALS.slice(0, 4)) beat(g);
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


// ── the goal must be PLAYED, not merely checked ──────────────────────────────
//
// A location can go checked without anyone playing it: !collect at the end of a
// run, a release, or a co-op partner sending it. Counting those would let a run
// claim the goal for levels nobody sat down and won, so goalPlayed() reads the
// game's own level progress instead of st.checked.

G.reset(keyed());
for (const g of GOALS) G.check(g);   // checked, never played
if (G.goalMet()) fail('the goal was met by checks alone, with nothing played');
else if (G.goalProgress().done !== 0)
  fail('checked-but-unplayed goals counted: ' + G.goalProgress().done);
else ok('collecting every goal check without playing does not win the run');

// ...and maybeSendGoal must not report it either, which is the packet that
// actually ends someone's run.
if (G.maybeSendGoal()) fail('the goal was REPORTED off checks alone');
else if (statuses().length) fail('a StatusUpdate went out for an unplayed goal');
else ok('nothing is reported to the multiworld for an unplayed goal');

// Playing them, without the checks ever arriving, IS the goal. This is the
// other half: the two conditions are genuinely independent, so neither test
// above passes for the wrong reason.
G.reset(keyed());
for (const g of GOALS) G.play(g);
if (!G.goalMet()) fail('playing every goal level did not meet the goal');
else ok('beating the levels is what counts, with or without the checks');

// The count moves one world at a time, and only for worlds played.
G.reset(keyed());
beat('egypt8');
if (G.goalProgress().done !== 1) fail('one world played read as ' + G.goalProgress().done);
G.check('pirate8');                  // checked only
if (G.goalProgress().done !== 1)
  fail('a checked-but-unplayed world moved the count to ' + G.goalProgress().done);
G.play('pirate8');                   // now actually beaten
if (G.goalProgress().done !== 2)
  fail('beating the checked world did not move the count');
else ok('the tracker counts worlds beaten, and a bare check does not move it');

// Modern Day access uses the same count on a legacy seed, for the same reason:
// it decides whether a world OPENS, not just whether the run ends.
G.reset(legacy());
for (const g of GOALS) G.check(g);
if (G.canAccessModernDay())
  fail('Modern Day opened on checks alone in a legacy seed');
else ok('legacy Modern Day access also requires the levels to be played');

// ── the overlay tracker ──────────────────────────────────────────────────────
// It reads the same goalProgress() the win check does, so the number a player
// sees is exactly the one that ends the run.
G.reset(keyed());
let pr = G.goalProgress();
if (pr.need !== 3) fail('tracker need is ' + pr.need + ', want the seed requirement');
if (pr.total !== GOALS.length)
  fail('tracker total is ' + pr.total + ', want ' + GOALS.length + ' goal locations');
if (pr.done !== 0) fail('a fresh seed reads as ' + pr.done + ' done');
beat('egypt8'); beat('pirate8');
pr = G.goalProgress();
if (pr.done !== 2) fail('after two worlds the tracker reads ' + pr.done);
else ok('tracker reads done/need/total off the same source as the win check');

// Before slot_data lands there is nothing to show, and nothing may be claimed.
G.reset({ modernKeyed: true });
pr = G.goalProgress();
if (pr.need || pr.total) fail('the tracker showed a goal before slot_data arrived');
else if (G.goalMet()) fail('the goal was met before slot_data arrived');
else ok('no tracker and no goal until slot_data lands');

// The rendered line, not just the numbers behind it. "3/7 World Keys" is the
// interface Kurt asked for, so the string itself is asserted -- goalProgress()
// being right does not prove the panel shows it.
G.reset(keyed({ goalType: 'world_key' }));
beat('egypt8');
G.updateGoalTracker();
let html = G.goalEl().innerHTML;
if (!/<b>1\/3<\/b> World Keys/.test(html))
  fail('tracker line is ' + JSON.stringify(html));
else if (G.goalEl().style.display !== 'block') fail('tracker stayed hidden');
else ok('the panel shows "1/3 World Keys" after one world');

// The label follows goal_type, which slot_data sends as a STRING -- so the
// option renumbering cannot reach it.
G.reset(keyed({ goalType: 'zomboss' }));
G.updateGoalTracker();
if (!/Zomboss Fights/.test(G.goalEl().innerHTML)) fail('zomboss label missing');
G.reset(keyed({ goalType: 'completion' }));
G.updateGoalTracker();
if (!/Worlds Cleared/.test(G.goalEl().innerHTML)) fail('completion label missing');
// An unknown or absent goal_type falls back rather than rendering blank.
G.reset(keyed());
G.updateGoalTracker();
if (!/World Keys/.test(G.goalEl().innerHTML)) fail('no fallback label');
else ok('the label follows goal_type, and falls back when absent');

// Done is marked, and a bare check does not mark it.
G.reset(keyed());
for (const g of GOALS.slice(0, 3)) beat(g);
G.updateGoalTracker();
if (G.goalEl().className !== 'ap-goal-done') fail('a met goal was not marked done');
else if (!/goal complete/.test(G.goalEl().innerHTML)) fail('no completion text');
else ok('the tracker marks the goal complete once it is met');

G.reset(keyed());
for (const g of GOALS) G.check(g);
G.updateGoalTracker();
if (!/<b>0\/3<\/b>/.test(G.goalEl().innerHTML))
  fail('checks alone moved the tracker: ' + G.goalEl().innerHTML);
else ok('the tracker ignores checks that were never played');

// Hidden until slot_data lands, rather than showing 0/0.
G.reset({ modernKeyed: true });
G.updateGoalTracker();
if (G.goalEl().style.display !== 'none') fail('tracker shown before slot_data');
else ok('the tracker stays hidden until slot_data lands');

// -- a goal location this client has no level for -----------------------------
// The realistic case is an old injected client meeting a new seed: slot_data
// names a goal level it has never heard of. goalPlayed() cannot ask "was this
// played" without a level id, so it FAILS CLOSED. Counting it off isChecked
// instead would reopen the exact hole -- a released goal would count as a
// world beaten, by the client that is least able to tell.
G.reset(keyed({ unknownLocs: ['modern16'] }));
for (const g of GOALS) G.check(g);   // released, or !collect'd: never played
if (G.goalMet()) fail('an unknown goal location counted off a bare check');
else ok('an unknown goal location does not count when merely checked');

// And it stays uncounted even when the level "was played" -- with no level id
// there is nothing to have played, so the only honest answer is no.
G.reset(keyed({ unknownLocs: ['egypt8', 'pirate8', 'cowboy8'] }));
for (const g of GOALS.slice(0, 3)) beat(g);
if (G.goalProgress().done !== 0)
  fail('unknown goals counted: ' + G.goalProgress().done);
else ok('unknown goal locations never reach the done count');

// Loud, not silent: the run is stranded and the player has to be told why,
// once per name rather than once per poll.
const warns = () => G.logs.filter(l => /not a level this client knows/.test(l)).length;
if (warns() !== 3) fail('warned the wrong number of times: ' + warns());
else ok('each unknown goal location warns exactly once');

G.goalProgress(); G.goalProgress();
if (warns() !== 3) fail('re-warned on a later poll');
else ok('the warning does not repeat every poll');

// Known goals still count normally alongside an unknown one, so one bad name
// costs exactly one world rather than the whole run.
G.reset(keyed({ unknownLocs: ['modern16'], worldsReq: 3 }));
for (const g of ['egypt8', 'pirate8', 'cowboy8']) beat(g);
if (!G.goalMet()) fail('known goals stopped counting because of an unknown one');
else ok('an unknown goal does not poison the goals the client does know');

// -- /send_location must not forge the save --------------------------------
// THE BUG, reported 2026-08-25: `/send_location egypt8` goaled the run outright
// instead of just checking the location. rebuildAPSave() restored levelProps
// from st.checked, so the arriving check wrote progress 3 into the save, and
// isFinished() -- the whole basis of the played-not-checked rule -- read back
// the number the check had just written. The rule was testing its own forgery.
G.reset(keyed({ worldsReq: 1 }));
G.check('egypt8');                       // the server says: this is checked
G.poll();                                // ...and a poll rebuilds the save
if (G.levelProps()['lvl:egypt8']) fail('a bare check wrote level progress into the save');
else ok('a check the player never played leaves the save unbeaten');
if (G.goalPlayed('egypt8')) fail('a bare check counted as played');
else if (G.goalMet()) fail('/send_location completed the goal');
else ok('/send_location checks the location and nothing else');

// The level still has to be playable afterwards, and playing it has to count.
// This is the case the fix could easily strand: the check is already in
// st.checked, so a detection loop that bails on isChecked would never see the
// play and that goal world could never be completed.
G.play('egypt8');
G.poll();
if (!G.isPlayed('egypt8')) fail('playing an already-checked level was not recorded');
else if (!G.goalMet()) fail('playing the level after its check did not complete the goal');
else ok('playing a level that was already checked still counts');

// The ledger, not the live save, is what survives: the game wipes levelProps
// on a fresh save and rebuildAPSave() puts back what was played.
G.reset(keyed({ worldsReq: 1 }));
G.play('egypt8'); G.poll();
G.levelProps()['lvl:egypt8'] = undefined;   // the game wipes the save
delete G.levelProps()['lvl:egypt8'];
G.poll();
if (!G.goalMet()) fail('a played level did not survive a save wipe');
else ok('the played ledger restores progress the game wiped');

// Stale entries are cleared, or a level unplayed on this save would stay
// beaten forever once anything had written it.
G.reset(keyed({ worldsReq: 1 }));
G.levelProps()['lvl:pirate8'] = { progress: 3 };
G.recordPlayed('egypt8');
G.restoreLevelProgress({ levelProps: G.levelProps() });
if (G.levelProps()['lvl:pirate8']) fail('an unplayed level kept its stale progress');
else if (!G.levelProps()['lvl:egypt8']) fail('a played level was not restored');
else ok('restore clears every AP level and puts back only what was played');

// -- resuming a run vs. being handed checks mid-run --------------------------
// The reconnect merge is the one place a check still implies play, and it has
// to be: a save with no play history at all -- wiped localStorage, a second
// machine, an AP state reset -- has nothing but the server's list to rebuild
// its map progression from, and refusing it would make the player replay the
// whole run. The line is drawn at "has this save played anything yet".
G.reset(keyed({ worldsReq: 3 }));
G.setServerChecked(['egypt8', 'pirate8', 'cowboy8']);
G.mergeServerChecks();
if (!G.isPlayed('egypt8')) fail('resuming a run did not restore its progression');
else if (!G.levelProps()['lvl:egypt8']) fail('resumed progress never reached the save');
else ok('a save with no play history restores progression from the server');

// ...and mid-run it must NOT, or /send_location is back via the reconnect path.
G.reset(keyed({ worldsReq: 3 }));
G.play('egypt8'); G.poll();               // this save has played something
G.setServerChecked(['pirate8', 'cowboy8']);
G.mergeServerChecks();
if (G.isPlayed('pirate8')) fail('a mid-run merge marked an unplayed level played');
else if (!G.isChecked('pirate8')) fail('the merge did not record the check at all');
else if (G.goalMet()) fail('a mid-run merge completed the goal');
else ok('a run already in progress takes the checks but not the progress');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nGOAL OK');
process.exit(failed ? 1 : 0);
