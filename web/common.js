// Shared by mac.html and phone.html: clock sync with the server, scheduling
// in the AudioContext, commands and events.
const $ = id => document.getElementById(id);
let clockOffset = 0; // server clock − this device's clock, ms
let clockRtt = null;

async function syncClock() {
  let best = null;
  for (let i = 0; i < 6; i++) {
    const t0 = Date.now();
    const { t } = await (await fetch('/time', { cache: 'no-store' })).json();
    const t1 = Date.now();
    if (!best || t1 - t0 < best.rtt) best = { rtt: t1 - t0, offset: t - (t0 + t1) / 2 };
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

// The slot (1-based) playing at t seconds into the test.
function slotAt(info, t) {
  let k = 0;
  info.schedule.forEach((s, i) => { if (t >= s.at) k = i + 1; });
  return k;
}

function slotLabel(info, k) {
  const system = info.timeline.some(x => x.slot === k && x.track === 'system');
  const mic = info.timeline.some(x => x.slot === k && x.track === 'mic');
  const vol = info.schedule[k - 1]?.volume;
  return `第 ${k} 段：系统 ${system ? '说话 ' + vol + '%' : '无声'} · 麦克风 ${mic ? '说话' : '无声'}`;
}
