// Copies of the tutorial/level completion functions from build_pvzge_ap.py,
// kept in sync by drift_test.py. Do not edit the copied functions here: edit
// the client and re-copy (everything from the "forceLevel order" comment to the
// "WebSocket / AP Protocol" banner). Everything above them is harness
// scaffolding.

// Harness stub for the game's save. setSave() puts the player where a test
// wants them: forceLevel is what the game advances through the tutorial, and
// levelProps is where every ordinary level records that it was beaten.
const window = {};

function setSave(forceLevel, levelProps) {
  window._AP_AllPlayerProperties = {
    currentPlayer: { forceLevel: forceLevel, levelProps: levelProps || {} },
  };
}

// forceLevel order for tutorial progression. egypt1 is in it because it is the
// step AFTER the last tutorial -- forceLevel reads 'egypt1' while tutorial4 is
// the level just beaten -- and NOT because it is a tutorial.
const TUTORIAL_ORDER = ['tutorial1','tutorial2','tutorial3','tutorial4','egypt1'];
// The four that really are tutorials, and the only ones whose completion may
// be read off forceLevel. Routing egypt1 through isTutorialDone() sent its
// check the moment the tutorial ended: rebuildAPSave step 5 sets forceLevel to
// '' once tutorial4 is checked, and isTutorialDone() reads an empty forceLevel
// as "everything in the order is done" -- egypt1 included, unplayed.
const TUTORIAL_LEVELS = TUTORIAL_ORDER.slice(0, 4);

function isTutorialComplete() {
  const APP = window._AP_AllPlayerProperties;
  const fl = (APP && APP.currentPlayer ? APP.currentPlayer.forceLevel : null) || '';
  return !['tutorial1','tutorial2','tutorial3','tutorial4'].includes(fl);
}

function isTutorialDone(tutorialId) {
  const APP = window._AP_AllPlayerProperties;
  const forceLevel = (APP && APP.currentPlayer ? APP.currentPlayer.forceLevel : null) || '';
  const myIdx = TUTORIAL_ORDER.indexOf(tutorialId);
  if(myIdx < 0) return false;
  if(forceLevel === '') return true;
  const forceLevelIdx = TUTORIAL_ORDER.indexOf(forceLevel);
  if(forceLevelIdx < 0) return true;
  return forceLevelIdx > myIdx;
}

function isFinished(levelId) {
  if(TUTORIAL_LEVELS.includes(levelId)) return isTutorialDone(levelId);
  const APP = window._AP_AllPlayerProperties;
  const cp = APP ? APP.currentPlayer : null;
  const lp = cp ? cp.levelProps : null;
  if(!lp) return false;
  const e = lp[levelId]; return e && (e.progress||0) >= 3;
}

module.exports = { isFinished, isTutorialDone, isTutorialComplete, setSave,
                   TUTORIAL_ORDER, TUTORIAL_LEVELS };
