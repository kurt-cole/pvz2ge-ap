// VERBATIM COPY from build_pvzge_ap.py -- drift_test.py asserts this still
// matches the real client. If it fails, re-copy from there; never relax it.
const FEATURE_UNLOCK_LEVELS = { feature_store: 'egypt6' };

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
      const entry = levels[FEATURE_UNLOCK_LEVELS[flag]];
      const progress = entry && entry.progress;
      if (!feats[flag] && progress >= PROGRESS_FINISHED) {
        feats[flag] = true;
        opened.push(flag);
      }
    }
    return opened;
}

module.exports = { syncFeatureFlags, FEATURE_UNLOCK_LEVELS, PROGRESS_FINISHED };
