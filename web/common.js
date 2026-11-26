// Shared by mac.html and phone.html: the UI language, clock sync with the
// server, scheduling in the AudioContext, commands and events.
const $ = id => document.getElementById(id);

// --- Language: ?lang=en|zh, else the last choice, else English ---

const STRINGS = {
  en: {
    switchLang: '中文',
    macTitle: 'Echo test · Mac',
    connecting: 'Connecting…',
    phoneArmed: 'Phone ready',
    phoneConnected: 'Phone connected; tap “Ready” on it',
    phoneMissing: 'Phone not connected',
    step1: '1. Connect the phone',
    step1Body: 'On the same Wi-Fi as the Mac, open <b id="phoneUrl"></b> in Safari on the phone (or scan the code) and tap “Ready”.',
    step2: '2. Get the Mac ready',
    arm: 'Ready (load the audio, open the microphone)',
    loading: 'Loading…',
    ready: 'Ready',
    step3: '3. Match the levels',
    placement: 'Put the phone where your mouth is in a meeting, its speaker facing the Mac, and sit where you usually sit.',
    readThis: 'Read this at your usual meeting volume:',
    measureMe: 'Measure my voice',
    measurePhone: 'Measure the phone',
    readNow: 'Read the line above (10 s)…',
    noVoice: 'Heard nothing',
    myVoice: d => `Your voice: ${d} dB`,
    phonePlaying: 'The phone is playing…',
    noPhone: 'Did not hear the phone (is it ready?)',
    phoneLevel: d => `Phone: ${d} dB`,
    matched: d => `✓ Matched (${d} dB apart)`,
    mismatch: (louder, d) => `The phone is ${d} dB ${louder ? 'louder' : 'quieter'} than you → turn the phone ${louder ? 'down' : 'up'} and measure it again`,
    step4: '4. Test',
    step4Body: '<b>Start the meeting</b> in Voxt first, then press “Start test”. Do not touch the phone’s volume during the test.',
    start: 'Start test',
    stop: 'Stop',
    stopped: 'Stopped',
    doneMac: 'Done: you can end the meeting.',
    macNotReady: 'The Mac is not ready',
    startsIn: s => `Starts in ${s} s`,
    progress: (t, total, slot) => `${t} / ${total} s · ${slot}`,
    lead: 'lead-in',
    slot: 'Slot', system: 'System', mic: 'Microphone',
    speaks: 'speaks', silent: 'silent',
    slotLabel: (k, sys, mic) => `Slot ${k}: system ${sys} · microphone ${mic}`,
    phoneTitle: 'Echo test · Phone (the near end)',
    phoneArm: 'Ready',
    notReady: 'Not ready',
    waiting: ms => `Waiting for the Mac to start (clock within ±${ms} ms)`,
    error: m => `Error: ${m}`,
    calibrating: 'Calibration: playing once',
    testing: 'Testing',
    playsIn: s => `Plays in ${s} s`,
    playing: 'Playing',
    calibrated: 'Calibration done',
    done: 'Done',
    phoneHints: '· Turn off silent mode. Set the volume with the side buttons while the Mac measures the phone, then leave it during the test.<br>· Keep the screen on and stay in Safari during the test.<br>· Put the phone where your mouth is in a meeting, its speaker facing the Mac.',
  },
  zh: {
    switchLang: 'English',
    macTitle: '回声测试 · Mac',
    connecting: '连接中…',
    phoneArmed: '手机已准备',
    phoneConnected: '手机已连接，等它点“准备”',
    phoneMissing: '手机未连接',
    step1: '1. 连接手机',
    step1Body: '手机和 Mac 连同一个 Wi-Fi，用手机 Safari 打开 <b id="phoneUrl"></b>（或扫码），点“准备”。',
    step2: '2. 准备 Mac',
    arm: '准备（加载音频、打开麦克风）',
    loading: '加载中…',
    ready: '已准备',
    step3: '3. 匹配响度',
    placement: '手机放在你平时开会时嘴的位置，扬声器朝向 Mac；你也坐在平时的位置说话。',
    readThis: '用平时开会的音量读：',
    measureMe: '测我的声音',
    measurePhone: '测手机',
    readNow: '请读上面那句话（10 秒）…',
    noVoice: '没听到声音',
    myVoice: d => `你的声音：${d} dB`,
    phonePlaying: '手机播放中…',
    noPhone: '没听到手机（手机准备好了吗？）',
    phoneLevel: d => `手机：${d} dB`,
    matched: d => `✓ 匹配（相差 ${d} dB）`,
    mismatch: (louder, d) => `手机比你${louder ? '大' : '小'} ${d} dB → ${louder ? '调小' : '调大'}手机音量，再测手机`,
    step4: '4. 测试',
    step4Body: '先在 Voxt 里<b>开始会议</b>，再点“开始测试”。测试时手机音量不要动。',
    start: '开始测试',
    stop: '停止',
    stopped: '已停止',
    doneMac: '完成，可以结束会议了。',
    macNotReady: 'Mac 还没准备',
    startsIn: s => `${s} 秒后开始`,
    progress: (t, total, slot) => `${t} / ${total} 秒 · ${slot}`,
    lead: '开头',
    slot: '段', system: '系统', mic: '麦克风',
    speaks: '说话', silent: '无声',
    slotLabel: (k, sys, mic) => `第 ${k} 段：系统 ${sys} · 麦克风 ${mic}`,
    phoneTitle: '回声测试 · 手机端（近端说话人）',
    phoneArm: '准备',
    notReady: '未准备',
    waiting: ms => `等待 Mac 开始（时钟误差约 ±${ms} ms）`,
    error: m => `出错：${m}`,
    calibrating: '校准：播放一遍',
    testing: '测试中',
    playsIn: s => `${s} 秒后播放`,
    playing: '播放中',
    calibrated: '校准播放完了',
    done: '完成',
    phoneHints: '· 关掉静音开关，音量用侧键调，在 Mac 页面上“测手机”时匹配好，测试时不要再动。<br>· 测试过程中屏幕保持亮着，别切到别的 App。<br>· 手机放在你平时开会时嘴的位置，扬声器朝向 Mac。',
  },
};

const LANG = (() => {
  const asked = new URLSearchParams(location.search).get('lang');
  let saved = null;
  try {
    if (asked) localStorage.setItem('lang', asked);
    saved = localStorage.getItem('lang');
  } catch (e) {}
  const lang = asked || saved;
  return lang in STRINGS ? lang : 'en';
})();
document.documentElement.lang = LANG;

const t = (key, ...args) => {
  const s = STRINGS[LANG][key];
  return typeof s === 'function' ? s(...args) : s;
};

// Fills [data-t] elements and adds the language switch.
function applyStrings() {
  document.title = t(document.body.dataset.title);
  document.querySelectorAll('[data-t]').forEach(el => { el.innerHTML = t(el.dataset.t); });
  const a = document.createElement('a');
  a.id = 'lang';
  a.textContent = t('switchLang');
  a.href = '?lang=' + (LANG === 'en' ? 'zh' : 'en');
  document.body.prepend(a);
}

// --- Clock and scheduling ---

let clockOffset = 0; // server clock − this device's clock, ms
let clockRtt = null;

async function syncClock() {
  let best = null;
  for (let i = 0; i < 6; i++) {
    const t0 = Date.now();
    const { t: server } = await (await fetch('/time', { cache: 'no-store' })).json();
    const t1 = Date.now();
    if (!best || t1 - t0 < best.rtt) best = { rtt: t1 - t0, offset: server - (t0 + t1) / 2 };
  }
  clockOffset = best.offset;
  clockRtt = best.rtt;
  return best;
}

const serverNow = () => Date.now() + clockOffset;
// The AudioContext time at a server time.
const ctxTimeAt = (ctx, serverMs) => ctx.currentTime + Math.max(0, serverMs - serverNow()) / 1000;
const msUntil = serverMs => Math.max(0, serverMs - serverNow());

async function post(body) {
  await fetch('/cmd', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

async function loadBuffer(ctx, url) {
  const data = await (await fetch(url)).arrayBuffer();
  return await new Promise((resolve, reject) => ctx.decodeAudioData(data, resolve, reject));
}

function listen(role, on) {
  const es = new EventSource('/events?role=' + role);
  es.onmessage = e => on(JSON.parse(e.data));
  return es;
}

// --- Slots ---

// The slot (1-based) playing at s seconds into the test.
function slotAt(info, s) {
  let k = 0;
  info.schedule.forEach((step, i) => { if (s >= step.at) k = i + 1; });
  return k;
}

function slotParts(info, k) {
  const has = track => info.timeline.some(x => x.slot === k && x.track === track);
  return {
    system: has('system') ? `${t('speaks')} ${info.schedule[k - 1].volume}%` : t('silent'),
    mic: has('mic') ? t('speaks') : t('silent'),
  };
}

function slotLabel(info, k) {
  const p = slotParts(info, k);
  return t('slotLabel', k, p.system, p.mic);
}
