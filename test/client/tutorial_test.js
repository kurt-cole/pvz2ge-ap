// Drives the REAL isFinished()/isTutorialDone() from build_pvzge_ap.py.
//
// pollChecks() fires a location the moment isFinished() says its level is done,
// so anything isFinished() gets wrong is a check sent for a level nobody
// played. The tutorials are the hard part: they have no levelProps entry, so
// their completion is read off cp.forceLevel, which the game (and rebuildAPSave
// step 5) advances tutorial1 -> ... -> tutorial4 -> '' as they are beaten.
//
// egypt1 sits in TUTORIAL_ORDER because forceLevel names it as the step after
// the last tutorial, NOT because it is a tutorial. Reading its completion off
// forceLevel sent egypt1's check the moment tutorial4 was checked, because an
// empty forceLevel reads as "everything in the order is done".
const { isFinished, isTutorialDone, setSave } = require('./tutorial_fn.js');

let failed = 0;
const ok = m => console.log('  ok    ' + m);
const fail = m => { failed++; console.log('  FAIL  ' + m); };
const is = (got, want, m) =>
  !!got === want ? ok(m) : fail(`${m}  (got ${!!got}, want ${want})`);

console.log('\n  a tutorial is done once forceLevel has moved past it');

setSave('tutorial3', {});
is(isTutorialDone('tutorial1'), true,  'tutorial1 is done while the game asks for tutorial3');
is(isTutorialDone('tutorial2'), true,  'tutorial2 is done while the game asks for tutorial3');
is(isTutorialDone('tutorial3'), false, 'tutorial3 is not done while the game is still asking for it');
is(isTutorialDone('tutorial4'), false, 'tutorial4 is not done that early');

console.log('\n  egypt1 is an ordinary level and answers only to levelProps');

setSave('egypt1', {});
is(isFinished('tutorial4'), true,  'tutorial4 is done once forceLevel names egypt1');
is(isFinished('egypt1'),    false, 'egypt1 is not done merely because it is the next level');

// The state the bug was reported from: tutorial4 checked, so rebuildAPSave
// step 5 writes forceLevel '' and the tutorial is over.
setSave('', {});
is(isFinished('tutorial1'), true,  'every tutorial is done once forceLevel is empty');
is(isFinished('tutorial4'), true,  'tutorial4 included');
is(isFinished('egypt1'),    false, 'egypt1 is NOT done when the tutorial ends (the reported bug)');

setSave('', { egypt1: { progress: 1 } });
is(isFinished('egypt1'), false, 'egypt1 unlocked but never beaten is not done');
setSave('', { egypt1: { progress: 3 } });
is(isFinished('egypt1'), true,  'egypt1 is done once the game records progress 3');

console.log('\n  skip_tutorial leaves forceLevel empty from the start');

setSave('', { egypt2: { progress: 3 } });
is(isFinished('tutorial2'), true,  'the tutorials count as done, which is what skipping them means');
is(isFinished('egypt1'),    false, 'and egypt1 still has to be played');
is(isFinished('egypt2'),    true,  'an ordinary level reads its own progress');

console.log(failed ? `\n${failed} FAILURE(S)` : '\nTUTORIAL COMPLETION OK');
process.exit(failed ? 1 : 0);
