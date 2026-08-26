const window = {};
let st;
function syncGrantedUpgrades() {
    window._AP_shuffleUpgrades = !!st.shuffleUpgrades;
    const map = st.upgradeItems || {};
    const counts = st.upgradeCounts || {};
    const granted = new Set(), known = new Set();
    for(const name of Object.keys(map)){
      const cns = map[name] || [];
      cns.forEach(cn => known.add(cn));
      // Capped at the group's length: a pool that somehow over-delivered
      // would otherwise index past the end and add undefined to the set.
      const n = Math.min(counts[name] || 0, cns.length);
      for(let i = 0; i < n; i++) granted.add(cns[i]);
    }
    window._AP_grantedUpgrades = granted;
    // Which codenames AP manages at all, so rebuildAPSave() only ever resets
    // these -- an upgrade the game gains in a future version is left alone
    // rather than forced to 0 for not being in a map that predates it.
    window._AP_knownUpgradeCns = known;
    return granted;
  }
module.exports = { setSt: s => { st = s; }, syncGrantedUpgrades, window };
