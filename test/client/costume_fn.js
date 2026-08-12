const window={};
let st={costumes:{},wornCostume:{},pendingCostumes:0};
function svSt(){}
function toast(){}
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
const PLANT_COSTUMES = {
    0:10, 1:8, 2:9, 3:3, 4:6, 5:3, 6:5, 7:10, 8:9, 10:2, 11:2, 12:3, 13:1, 14:1, 16:1, 17:3,
    18:2, 19:2, 20:1, 21:2, 23:1, 24:4, 25:8, 27:1, 28:5, 29:5, 30:5, 32:3, 33:1, 34:4,
    35:4, 36:3, 37:4, 38:3, 39:1, 41:2, 42:1, 43:1, 44:3, 45:3, 46:2, 49:4, 50:1, 51:2,
    54:2, 55:2, 56:3, 57:3, 58:2, 59:5, 60:1, 61:3, 62:3, 63:6, 64:1, 65:2, 66:1, 67:3,
    69:3, 70:2, 71:1, 72:2, 73:1, 74:2, 75:2, 76:1, 77:3, 78:2, 79:3, 80:2, 81:2, 82:3,
    84:1, 85:1, 86:1, 87:3, 88:3, 89:3, 90:2, 96:3, 97:4, 106:1, 107:2, 108:1, 109:1, 110:1,
    114:2, 120:1, 127:2, 128:1, 129:4, 130:1, 131:2, 132:3, 133:2, 134:2, 135:2, 136:2,
    137:2, 138:2, 139:2, 142:2, 143:2, 144:2, 145:2, 146:2, 148:2, 149:1, 150:2, 151:2,
    152:2, 153:2, 154:2, 155:1, 156:1, 157:1, 160:2, 161:1, 164:2, 165:1
  };
function ownedCostumes(pid){
    return (st.costumes || {})[pid] || [];
  }
function wornCostume(pid){
    const owned = ownedCostumes(pid);
    if(!owned.length) return -1;
    const worn = (st.wornCostume || {})[pid];
    // -1 is a real choice the trap can make: it means wearing none.
    if(worn === -1) return -1;
    if(worn === undefined || owned.indexOf(worn) < 0) return owned[owned.length-1];
    return worn;
  }
function shuffleCostumes(){
    const owned = st.costumes || {};
    const pids = Object.keys(owned).filter(pid => owned[pid].length);
    if(!pids.length) return false;
    if(!st.wornCostume) st.wornCostume = {};
    let moved = 0;
    for(const pid of pids){
      // The choices are everything that plant owns, plus taking it off.
      const choices = owned[pid].concat([-1]);
      const before = wornCostume(pid);
      const pick = choices[Math.floor(Math.random() * choices.length)];
      st.wornCostume[pid] = pick;
      if(pick !== before) moved++;
    }
    svSt();
    toast('🎭 Costume Shuffle — ' + moved + ' plant' + (moved===1?'':'s') + ' redressed', '#f66');
    return true;
  }
function grantRandomCostume(){
    const granted = window._AP_grantedPlantIds || new Set();
    const options = [];
    for(const pid of granted){
      const total = PLANT_COSTUMES[pid] || 0;
      if(!total) continue;
      const have = ownedCostumes(pid);
      for(let i = 0; i < total; i++) if(have.indexOf(i) < 0) options.push([pid, i]);
    }
    if(!options.length) return false;
    const [pid, idx] = options[Math.floor(Math.random() * options.length)];
    if(!st.costumes) st.costumes = {};
    if(!st.costumes[pid]) st.costumes[pid] = [];
    st.costumes[pid].push(idx);
    svSt();
    const cn = ID_TO_CN[pid];
    toast('👕 Costume for ' + (cn || ('plant ' + pid)), '#f0abfc');
    return true;
  }
function applyPendingCostumes(){
    let pending = st.pendingCostumes || 0;
    if(pending <= 0) return;
    let granted = 0;
    while(pending > 0 && grantRandomCostume()){ pending--; granted++; }
    if(granted){
      st.pendingCostumes = pending;
      svSt();
    }
  }
module.exports={shuffleCostumes, wornCostume, ownedCostumes, grantRandomCostume,
  applyPendingCostumes, window, setSt:s=>{st=s}, getSt:()=>st, PLANT_COSTUMES, ID_TO_CN};
