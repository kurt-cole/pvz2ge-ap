const window={};
const ID_TO_CN = {
    0:'peashooter', 1:'sunflower', 2:'wallnut', 3:'potatomine',
    4:'cabbagepult', 5:'bloomerang', 6:'iceburg', 7:'bonkchoy',
    8:'repeater', 10:'scaredyshroom', 11:'fumeshroom',
    12:'gravebuster', 13:'pumpkin', 14:'pvine',
    16:'firepeashooter', 17:'threepeater', 18:'primalpeashooter',
    19:'rotobaga', 20:'homingthistle', 21:'starfruit', 22:'shootingstarfruit',
    23:'lilypad', 24:'sunshroom', 25:'twinsunflower', 26:'dragonbruit',
    27:'moonflower', 28:'snowpea', 29:'lightningreed', 30:'kernelpult',
    31:'meteorflower', 32:'springbean', 33:'umbrellaleaf',
    34:'melonpult', 35:'wintermelon', 36:'blover', 37:'spikeweed',
    38:'spikerock', 39:'chomper', 40:'glaciershroom',
    41:'primalwallnut', 42:'buttercup',
    43:'banana', 44:'missiletoe', 45:'cherry_bomb', 46:'doomshroom',
    47:'cranjelly', 49:'torchwood', 50:'jalapeno', 51:'puffshroom',
    52:'gloomvine', 53:'vamporcini', 54:'primalpotatomine',
    55:'cactus', 56:'powerlily', 57:'coconutcannon', 58:'peapod',
    59:'snapdragon', 60:'gatling', 61:'splitpea', 62:'chilibean',
    63:'tallnut', 64:'hurrikale', 65:'stallia', 66:'electricpeashooter',
    67:'squash', 68:'gloomshroom', 69:'magnifyinggrass', 70:'celerystalker',
    71:'sapfling', 72:'parsnip', 73:'explodeonut', 74:'grapeshot',
    75:'plantern', 76:'peach', 77:'jackolantern', 78:'dandelion',
    79:'chardguard', 80:'hypnoshroom', 81:'electriccurrant',
    82:'escaperoot', 83:'imitater', 84:'shadowshroom', 85:'magnetshroom',
    86:'turnip', 87:'empea', 88:'citron', 89:'laser_bean', 90:'solartomato',
    96:'holonut', 97:'powerplant', 106:'applemortar', 107:'redstinger', 108:'skyshooter',
    109:'sunbean', 110:'peanut', 114:'tanglekelp', 115:'bowlingbulb',
    120:'guacodile', 127:'ghostpepper', 128:'sweetpotato', 129:'pepperpult',
    130:'hotpotato', 131:'stunion', 132:'goldleaf', 133:'akee',
    134:'endurian', 135:'toadstool', 136:'lavaguava', 137:'phatbeet',
    138:'strawburst', 139:'thymewarp', 141:'seashroom', 142:'garlic',
    143:'electricblueberry', 144:'sporeshroom', 145:'intensivecarrot',
    146:'primalsunflower', 147:'moonbean', 148:'coldsnapdragon',
    149:'nightshade', 150:'dusklobber', 151:'grimrose', 152:'goldbloom',
    153:'bloominghearts', 154:'shrinkingviolet', 155:'hotdate',
    156:'firegourd', 157:'bambooshoot', 158:'snowdrop', 159:'lychee',
    160:'perfumeshroom', 161:'solarsage', 162:'bamboozle',
    164:'cantaloupe', 165:'iceweed',
  };
const CONVEYOR_GROUPS = {
    'sustained:mid': [
      'akee', 'bambooshoot', 'bamboozle', 'bloomerang', 'bloominghearts', 'bonkchoy',
      'bowlingbulb', 'cactus', 'chomper', 'coldsnapdragon', 'doomshroom', 'dragonbruit',
      'dusklobber', 'electricblueberry', 'electriccurrant', 'electricpeashooter',
      'firegourd', 'firepeashooter', 'hotdate', 'iceweed', 'jackolantern', 'laser_bean',
      'lychee', 'parsnip', 'peanut', 'pepperpult', 'phatbeet', 'primalpeashooter',
      'pumpkin', 'pvine', 'redstinger', 'repeater', 'skyshooter', 'snapdragon',
      'snowdrop', 'snowpea', 'sporeshroom', 'starfruit', 'sweetpotato', 'torchwood'
    ],
    'sustained:low': [
      'cabbagepult', 'chardguard', 'cranjelly', 'endurian', 'fumeshroom', 'gloomvine',
      'guacodile', 'intensivecarrot', 'kernelpult', 'lightningreed', 'magnetshroom',
      'nightshade', 'peach', 'peapod', 'peashooter', 'primalwallnut', 'sapfling',
      'spikeweed', 'splitpea', 'tallnut', 'umbrellaleaf', 'vamporcini'
    ],
    'single-use:budget': [
      'blover', 'chilibean', 'empea', 'escaperoot', 'goldbloom', 'goldleaf',
      'gravebuster', 'hotpotato', 'iceburg', 'potatomine', 'primalpotatomine',
      'shadowshroom', 'shrinkingviolet', 'solarsage', 'squash', 'stallia', 'stunion',
      'sunbean', 'tanglekelp'
    ],
    'sustained:high': [
      'applemortar', 'banana', 'cantaloupe', 'citron', 'coconutcannon', 'dandelion',
      'gatling', 'glaciershroom', 'gloomshroom', 'homingthistle', 'melonpult',
      'meteorflower', 'missiletoe', 'shootingstarfruit', 'spikerock', 'strawburst',
      'threepeater', 'wintermelon'
    ],
    'sustained:budget': [
      'buttercup', 'celerystalker', 'explodeonut', 'garlic', 'imitater', 'lilypad',
      'moonflower', 'puffshroom', 'scaredyshroom', 'seashroom', 'springbean', 'turnip',
      'wallnut'
    ],
    'single-use:low': [
      'ghostpepper', 'grimrose', 'hurrikale', 'hypnoshroom', 'jalapeno', 'lavaguava',
      'solartomato', 'thymewarp'
    ],
    'single-use:mid': [
      'cherry_bomb', 'grapeshot', 'perfumeshroom', 'powerlily'
    ],
    'sun:budget': [
      'magnifyinggrass', 'moonbean', 'sunflower', 'sunshroom'
    ],
    'sun:low': [
      'plantern', 'primalsunflower', 'twinsunflower'
    ],
    'sun:mid': [
      'toadstool'
    ]
  };
function _apHash(str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
function _apRng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
function installConveyorHook(LC) {
    if (!LC || LC._ap_hooked_conveyor || !LC.prototype || !LC.prototype.module_SetConveyor) return;
    const _origSetConveyor = LC.prototype.module_SetConveyor;
    LC.prototype.module_SetConveyor = function (props) {
      let patched = props;
      try {
        const pool  = window._AP_conveyorPool;
        const swaps = window._AP_conveyorSwaps || {};
        if (window._AP_randomizeConveyor && props &&
            Array.isArray(props.InitialPlantList) && pool && pool.length) {
          const list  = props.InitialPlantList;
          const known = window._AP_conveyorKnown;
          // Seeded off the ORIGINAL plant types, which is what makes the roll
          // stable: the same level always produces the same belt, and a retry
          // is not a reroll. That only holds because nothing below writes back
          // to props -- the entries are copied, see the map() further down.
          const rnd = _apRng(_apHash(String(window._AP_conveyorSeed || 0) + '|' +
                                     list.map(e => (e && e.PlantType) || '').join('|')));
          // Does this lawn have deep water? Two signals, because the grid may
          // not be built yet when the conveyor is set: the game's own flag, and
          // failing that the level's own belt -- a level handing out a water
          // plant self-evidently has water. Fails CLOSED to "no water", so an
          // unreadable level loses aquatic swaps rather than gaining dead slots.
          let hasWater = false;
          try {
            const lc = window._AP_levelController;
            hasWater = !!(lc && lc.component && lc.component.haveWater);
          } catch (e) { /* fall through to the belt signal */ }
          if (!hasWater) {
            hasWater = list.some(e => e && window._AP_conveyorTerrainLocked.has(e.PlantType) &&
                                      e.PlantType !== 'goldleaf');
          }
          const used = new Set();
          const newList = list.map(function (entry) {
            // Only genuine plants are swapped. A conveyor also delivers
            // bowling projectiles, power tiles and potions on the minigame
            // levels (tool_projectile_*, tool_powertile_*, zombiepotion_*),
            // and turning those into plants makes the level unplayable.
            if (!entry || !known || !known.has(entry.PlantType)) return entry;
            // Swap within the plant's own group, so a belt keeps the shape the
            // level was built around: a sun producer stays a sun producer, a
            // one-shot stays a one-shot, and the replacement costs about what
            // the original did. A plant with no group -- nothing comparable to
            // trade it for -- is left as the level had it.
            const candidates = swaps[entry.PlantType];
            if (!candidates) return entry;
            // A terrain-locked plant the level placed itself is left exactly as
            // it was. Swapping a Big Wave Beach belt's Lily Pad for a Wall-nut
            // takes away the only thing that makes its water columns usable,
            // which is the same class of bug in the other direction.
            if (window._AP_conveyorTerrainLocked.has(entry.PlantType)) return entry;
            // Drop candidates this lawn cannot host, then apply the group rule
            // that a plant with nothing left to trade for stays put -- the
            // original is always in its own group, so fewer than two survivors
            // means there is no alternative.
            const usable = candidates.filter(cn => window._AP_conveyorPlantable(cn, hasWater));
            if (usable.length < 2) return entry;
            let pick = entry.PlantType;
            for (let tries = 0; tries < 20; tries++) {
              const candidate = usable[Math.floor(rnd() * usable.length)];
              // Keep one belt from being three copies of the same plant while
              // the group has alternatives. Bounded, so a small group still
              // terminates rather than spinning.
              if (!used.has(candidate)) { pick = candidate; break; }
              pick = candidate;
            }
            used.add(pick);
            return Object.assign({}, entry, { PlantType: pick });
          });
          // Copy rather than mutate. The level's properties object is cached
          // and handed back on a replay, so writing to it would feed the next
          // roll its own output and the level would drift on every attempt.
          patched = Object.assign(Object.create(Object.getPrototypeOf(props) || Object.prototype), props);
          patched.InitialPlantList = newList;
        }
      } catch (e) { /* never stop a level from loading over this */ }
      const args = Array.prototype.slice.call(arguments);
      args[0] = patched;
      return _origSetConveyor.apply(this, args);
    };
    LC._ap_hooked_conveyor = true;
  }
const EX=new Set(['powerplant','holonut']);
window._AP_conveyorPool=Object.values(ID_TO_CN).filter(c=>!EX.has(c));
window._AP_conveyorKnown=new Set(window._AP_conveyorPool);
window._AP_conveyorSwaps={};
for(const k of Object.keys(CONVEYOR_GROUPS)){
  const m=CONVEYOR_GROUPS[k].filter(c=>!EX.has(c));
  if(m.length<2) continue;
  for(const c of m) window._AP_conveyorSwaps[c]=m;
}

// Terrain gate, mirroring the client's declarations. These are const/window
// assignments rather than named functions, so drift_test cannot check them --
// keep them identical to build_pvzge_ap.py by hand.
const CONVEYOR_WATER_ONLY = new Set(['lilypad', 'tanglekelp']);
const CONVEYOR_TILE_LOCKED = new Set(['goldleaf']);
window._AP_conveyorPlantable = function (cn, hasWater) {
  if (CONVEYOR_TILE_LOCKED.has(cn)) return false;
  if (CONVEYOR_WATER_ONLY.has(cn)) return !!hasWater;
  return true;
};
window._AP_conveyorTerrainLocked = new Set([
  ...CONVEYOR_WATER_ONLY, ...CONVEYOR_TILE_LOCKED,
]);

// Sets the game's own per-level water flag the hook reads. Pass undefined to
// model a level whose grid is not built yet, which must fail closed.
function setLevelWater(haveWater) {
  window._AP_levelController = { component: { haveWater: haveWater } };
}

module.exports={installConveyorHook, window, CONVEYOR_GROUPS, setLevelWater,
  CONVEYOR_WATER_ONLY, CONVEYOR_TILE_LOCKED};
