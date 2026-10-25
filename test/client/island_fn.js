// Copies of the world-map reward-island gate from build_pvzge_ap.py, for
// island_test.js. drift_test.py keeps them verbatim.
function _apRewardIslandFinished(island) {
  let prev = island.formalIsland;
  for (let hops = 0; prev && !prev._levelNode && hops < 8; hops++) prev = prev.formalIsland;
  // No level before it (a map opening on a reward node): the game's own answer.
  return (prev && prev._levelNode) ? !!prev._finished : island._finished;
}
function installRewardIslandGate(WM) {
  if (!WM || !WM.prototype || WM._ap_hooked_islands) return;
  const P = WM.prototype;
  const origActive = P.setIslandActive;
  if (typeof origActive !== 'function') return;
  P.setIslandActive = function () {
    try {
      const isl = (this.levelIslands || [])[0];
      const IP = isl && Object.getPrototypeOf(isl);
      if (IP && !IP._ap_hooked_reward && typeof IP.laterStart === 'function') {
        const origLater = IP.laterStart;
        IP.laterStart = function () {
          try {
            if (this._plantOnDisplay || this._upgradeOnDisplay) this._finished = _apRewardIslandFinished(this);
          } catch (e) { /* fall back to the game's own state */ }
          return origLater.apply(this, arguments);
        };
        IP._ap_hooked_reward = true;
      }
    } catch (e) { /* never stop the map from drawing over this */ }
    return origActive.apply(this, arguments);
  };
  WM._ap_hooked_islands = true;
}

module.exports = { installRewardIslandGate, _apRewardIslandFinished };
