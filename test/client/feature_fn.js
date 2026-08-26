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

const FEATURE_PROMPT_FLAGS = {
  feature_store:     ['store_open', 'store_intro'],
  feature_almanac:   ['almanac_open', 'almanac_intro'],
  feature_zengarden: ['zengarden_open', 'zengarden_intro'],
};

const PROGRESS_FINISHED = 3;

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
  // Mark the first-time prompt seen for every feature that is ON, not just
  // the ones turned on just now: a save where the feature was already true
  // would otherwise never pass through the branch above, and the flow would
  // still be waiting to fire on it.
  for (const flag of Object.keys(FEATURE_PROMPT_FLAGS)) {
    if (!feats[flag]) continue;
    const tut = cp.tutorial || (cp.tutorial = {});
    for (const t of FEATURE_PROMPT_FLAGS[flag]) tut[t] = true;
  }
  return opened;
}

module.exports = { syncFeatureFlags, FEATURE_UNLOCK_LEVELS,
                   FEATURE_PROMPT_FLAGS, PROGRESS_FINISHED };
