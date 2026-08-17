// VERBATIM COPY from build_pvzge_ap.py -- drift_test.py asserts this still
// matches the real client. If it fails, re-copy from there; never relax it.
const FEATURE_UNLOCK_LEVELS = {
  feature_almanac:   [['egypt2', 3]],
  feature_coins:     [['tutorial4', 3], ['egypt1', 1]],
  feature_plantfood: [['egypt1', 3]],
  feature_worldmap:  [['egypt1', 3]],
  feature_powerup:   [['egypt5', 3]],
  feature_zengarden: [['egypt5', 3]],
  feature_store:     [['egypt6', 3]],
};

// The game's LevelProgress enum: locked 0, unlocked_neverPlayed 1,
// unlocked_played 2, unlocked_willbeFinished 3, finished 4. 3 is what
// rebuildAPSave writes for a checked location and what most of the chain
// compares against; the thresholds above name their own so the two coins
// conditions stay distinguishable.
const PROGRESS_FINISHED = 3;

// Returns the flags it turned on, so the caller can log a change without
// logging every poll. Never turns one off: the game's chain does not either,
// and a flag that flickered would hide the store button mid-session.
function syncFeatureFlags(cp) {
  const opened = [];
  if (!cp) return opened;
  const levels = cp.levelProps || {};
  // getFeatureProps() builds this on demand and returns whatever is there,
  // so an object carrying only the keys below reads correctly: those are
  // set, every other flag is undefined and therefore still falsy, exactly as
  // the game's own all-false constructor leaves them.
  const feats = cp.features || (cp.features = {});
  for (const flag of Object.keys(FEATURE_UNLOCK_LEVELS)) {
    if (feats[flag]) continue;
    const met = FEATURE_UNLOCK_LEVELS[flag].some(function(cond) {
      const entry = levels[cond[0]];
      return !!entry && entry.progress >= cond[1];
    });
    if (met) {
      feats[flag] = true;
      opened.push(flag);
    }
  }
  return opened;
}

module.exports = { syncFeatureFlags, FEATURE_UNLOCK_LEVELS, PROGRESS_FINISHED };
