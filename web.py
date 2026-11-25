#!/usr/bin/env python3
"""Small page over BattyBirdNET detections on this board."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.environ.get("BATFINDER_DIR", os.path.dirname(os.path.abspath(__file__)))
OVERVIEW = os.path.join(DIR, "overview.json")
PORT = 8090
EMPTY = b'{"updated":null,"latest":null,"recent":[],"minutes":[],"hits":[]}'

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bats</title>
<style>
  :root {
    --bg: #14160f;
    --card: #1e2418;
    --ink: #e8eedf;
    --muted: #a3ad96;
    --good: #c6e072;
    --warm: #e2b15a;
    --dim: #66705c;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 17px/1.45 Georgia, "Iowan Old Style", Palatino, serif;
  }
  main { max-width: 860px; margin: 0 auto; padding: 28px 18px 72px; }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
  h1 { margin: 0; font-size: 34px; font-weight: 500; letter-spacing: -0.03em; }
  h2 { margin: 34px 0 10px; font-size: 18px; font-weight: 500; }
  .tools { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
  .lang { display: flex; gap: 6px; }
  .lang button {
    font: 12px/1 ui-sans-serif, system-ui, sans-serif;
    color: var(--muted);
    background: transparent;
    border: 1px solid var(--dim);
    border-radius: 999px;
    padding: 4px 8px;
    cursor: pointer;
  }
  .lang button.on { color: var(--ink); border-color: var(--good); }
  .live, .meta, .kicker, .meter, .when, .score, .quiet, footer, .chips {
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .live { color: var(--muted); font-size: 13px; white-space: nowrap; margin: 0; }
  .live i {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--dim); margin-right: 6px;
  }
  .live.on i { background: var(--good); }
  .meta { color: var(--muted); margin: 6px 0 0; font-size: 14px; }
  .meta a { color: var(--ink); }
  .meta a:hover { color: var(--good); }
  .now { margin-top: 26px; padding: 22px; background: var(--card); border-radius: 16px; }
  .kicker { margin: 0; color: var(--muted); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }
  .species { margin: 8px 0 0; font-size: 40px; letter-spacing: -0.03em; }
  .sci { margin: 2px 0 0; color: var(--muted); font-style: italic; }
  .meter { display: flex; gap: 28px; margin-top: 18px; }
  .meter b { display: block; font-size: 22px; font-weight: 600; }
  .meter span { color: var(--muted); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .chips span, .hit, .windows div {
    background: var(--card);
    border-radius: 10px;
  }
  .chips span { padding: 6px 10px; font-size: 14px; }
  .hit, .windows div {
    display: grid;
    grid-template-columns: 108px 1fr auto;
    gap: 10px 12px;
    align-items: baseline;
    padding: 10px 12px;
    margin-top: 8px;
  }
  .when { color: var(--muted); font-size: 13px; }
  .score { font-size: 15px; }
  .quiet { color: var(--warm); font-size: 12px; }
  .bars {
    display: flex; align-items: flex-end; gap: 3px; height: 128px;
    padding: 12px; background: var(--card); border-radius: 12px; overflow-x: auto;
  }
  .bar { flex: 1 0 7px; min-width: 7px; border-radius: 2px 2px 0 0; background: var(--dim); }
  .bar.warm { background: var(--warm); }
  .bar.hot { background: var(--good); }
  .empty { color: var(--muted); }
  footer { margin-top: 28px; color: var(--muted); font-size: 13px; }
  @media (max-width: 560px) {
    h1 { font-size: 28px; }
    .species { font-size: 32px; }
    .hit, .windows div { grid-template-columns: 1fr auto; }
    .when { grid-column: 1 / -1; }
  }
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1 id="title">Bats</h1>
      <p class="meta" id="since">BattyBirdNET on the <a href="https://www.veldshop.nl/en/vleermic-384khz-ultrasonic-microphone.html" target="_blank" rel="noopener">Vleermic</a> · <a href="https://cdn.webshopapp.com/shops/39297/files/493997606/vleermic-nl-en-v03.pdf" target="_blank" rel="noopener">Manual</a></p>
    </div>
    <div class="tools">
      <div class="lang" role="group" aria-label="Language">
        <button type="button" id="lang-en" class="on">EN</button>
        <button type="button" id="lang-nl">NL</button>
      </div>
      <p class="live" id="live"><i></i>waiting</p>
    </div>
  </header>
  <section class="now">
    <p class="kicker" id="kicker">Strongest species in this window</p>
    <h2 class="species" id="species">Waiting for audio</h2>
    <p class="sci" id="sci"></p>
    <div class="meter">
      <div><b id="score">—</b><span id="score-label">score</span></div>
      <div><b id="level">—</b><span id="level-label">level</span></div>
      <div><b id="when">—</b><span id="time-label">time</span></div>
    </div>
  </section>
  <h2 id="h-above">Above the threshold</h2>
  <p class="meta" id="rule">Five windows in a row, about 2 seconds, at 50% or higher.</p>
  <div id="tally" class="chips"></div>
  <div id="hits"></div>
  <h2 id="h-minutes">Per minute</h2>
  <div id="bars" class="bars"></div>
  <h2 id="h-windows">Recent windows</h2>
  <div id="windows" class="windows"></div>
  <footer id="foot"></footer>
</main>
<script>
const COPY = {
  en: {
    title: "Bats",
    on: "BattyBirdNET on the",
    sinceAt: "since",
    manual: "Manual",
    waiting: "waiting",
    listening: "listening",
    stale: "no fresh audio",
    offline: "no connection",
    waitAudio: "Waiting for audio",
    confirmed: "Confirmed in this window",
    strongest: "Strongest species in this window",
    below: "Below 10%",
    score: "score",
    level: "level",
    time: "time",
    above: "Above the threshold",
    rule: "Five windows in a row, about 2 seconds, at 50% or higher.",
    none: "No confirmation yet.",
    perMinute: "Per minute",
    noMinutes: "No minutes yet.",
    recent: "Recent windows",
    quiet: "quiet microphone",
    oneWindow: "window",
    manyWindows: "windows",
    foot: "windows this session · names from 10% · 50% over 2 seconds · 0.56 s window · EU list",
    unknown: "Unknown",
    noise: "Noise"
  },
  nl: {
    title: "Vleermuizen",
    on: "BattyBirdNET op de",
    sinceAt: "sinds",
    manual: "Handleiding",
    waiting: "wachten",
    listening: "luistert",
    stale: "geen verse audio",
    offline: "geen verbinding",
    waitAudio: "Wachten op audio",
    confirmed: "Bevestigd in dit venster",
    strongest: "Sterkste soort in dit venster",
    below: "Onder 10%",
    score: "score",
    level: "niveau",
    time: "tijd",
    above: "Boven de drempel",
    rule: "Vijf vensters achter elkaar, ongeveer 2 seconden, op 50% of hoger.",
    none: "Nog geen bevestiging.",
    perMinute: "Per minuut",
    noMinutes: "Nog geen minuten.",
    recent: "Laatste vensters",
    quiet: "stille microfoon",
    oneWindow: "venster",
    manyWindows: "vensters",
    foot: "vensters deze sessie · naam vanaf 10% · 50% over 2 seconden · venster 0,56 s · EU-lijst",
    unknown: "Onbekend",
    noise: "Ruis"
  }
};
const NAMES = {
  "Barbastella barbastellus": "Mopsvleermuis",
  "Eptesicus nilssonii": "Noordse vleermuis",
  "Eptesicus serotinus": "Laatvlieger",
  "Hypsugo savii": "Savi's dwergvleermuis",
  "Miniopterus schreibersii": "Langvleugelvleermuis",
  "Myotis alcathoe": "Nimfvleermuis",
  "Myotis bechsteinii": "Bechsteins vleermuis",
  "Myotis brandtii": "Brandts vleermuis",
  "Myotis capaccinii": "Langvingerige vleermuis",
  "Myotis dasycneme": "Meervleermuis",
  "Myotis daubentonii": "Watervleermuis",
  "Myotis emarginatus": "Ingekorven vleermuis",
  "Myotis myotis": "Vale vleermuis",
  "Myotis mystacinus": "Baardvleermuis",
  "Myotis nattereri": "Franjestaart",
  "NOISE": "Ruis",
  "Nyctalus lasiopterus": "Grote rosse vleermuis",
  "Nyctalus leisleri": "Bosvleermuis",
  "Nyctalus noctula": "Rosse vleermuis",
  "Pipistrellus kuhlii": "Kuhls dwergvleermuis",
  "Pipistrellus maderensis": "Madeiradwergvleermuis",
  "Pipistrellus nathusii": "Ruige dwergvleermuis",
  "Pipistrellus pipistrellus": "Gewone dwergvleermuis",
  "Pipistrellus pygmaeus": "Kleine dwergvleermuis",
  "Plecotus spec.": "Grootoorvleermuis",
  "Rhinolophus blasii": "Blasius' hoefijzerneus",
  "Rhinolophus ferrumequinum": "Grote hoefijzerneus",
  "Rhinolophus hipposideros": "Kleine hoefijzerneus",
  "Tadarida teniotis": "Bulvleermuis",
  "Vespertilio murinus": "Tweekleurige vleermuis"
};
const MIC = {
  en: "https://www.veldshop.nl/en/vleermic-384khz-ultrasonic-microphone.html",
  nl: "https://www.veldshop.nl/nl/vleermic-384khz-ultrasone-microfoon.html"
};
const MANUAL = "https://cdn.webshopapp.com/shops/39297/files/493997606/vleermic-nl-en-v03.pdf";
let lang = "en";
let lastData = null;
function t(key) {
  return COPY[lang][key];
}
function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"
  }[ch]));
}
function parts(label) {
  const text = label || "";
  const cut = text.indexOf("_");
  if (cut < 0) return {sci: text, common: ""};
  return {sci: text.slice(0, cut), common: text.slice(cut + 1)};
}
function common(label) {
  const bit = parts(label);
  if (!bit.sci && !bit.common) return t("unknown");
  if (bit.sci === "NOISE") return t("noise");
  if (lang === "nl") return NAMES[bit.sci] || bit.common || bit.sci;
  return bit.common || bit.sci;
}
function sciOf(label) {
  const sci = parts(label).sci;
  return sci && sci !== "NOISE" ? sci : "";
}
function pct(score) {
  return (score * 100).toFixed(1) + "%";
}
function db(rms) {
  if (!rms || rms <= 0) return "—";
  return (20 * Math.log10(rms)).toFixed(0) + " dB";
}
function localeTag() {
  return lang === "nl" ? "nl-NL" : "en-GB";
}
function clock(iso, withSeconds) {
  if (!iso) return "—";
  const stamp = iso.length === 16 ? iso + ":00Z" : iso;
  const options = {timeZone: "Europe/Amsterdam", hour: "2-digit", minute: "2-digit"};
  if (withSeconds) options.second = "2-digit";
  return new Intl.DateTimeFormat(localeTag(), options).format(new Date(stamp));
}
function started(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat(localeTag(), {
    timeZone: "Europe/Amsterdam", hour: "2-digit", minute: "2-digit",
    day: "numeric", month: "short"
  }).format(new Date(iso));
}
function clusters(hits) {
  const groups = [];
  for (const hit of hits || []) {
    const at = Date.parse(hit.t);
    const prev = groups[groups.length - 1];
    if (prev && prev.species === hit.species && at - prev.end <= 30000) {
      prev.end = at;
      prev.endIso = hit.t;
      prev.max = Math.max(prev.max, hit.score);
      prev.rms = Math.max(prev.rms, hit.rms);
      prev.n += 1;
    } else {
      groups.push({
        species: hit.species, start: at, end: at, startIso: hit.t, endIso: hit.t,
        max: hit.score, rms: hit.rms, n: 1
      });
    }
  }
  return groups.reverse();
}
function span(group) {
  const a = clock(group.startIso, true);
  const b = clock(group.endIso, true);
  return a === b ? a : a + "–" + b.slice(0, 5);
}
function windowWord(n) {
  return n + " " + (n === 1 ? t("oneWindow") : t("manyWindows"));
}
const SHOW = 0.10;
function shown(score, label) {
  return score >= SHOW ? common(label) : "—";
}
function subtitle(startedIso) {
  const when = startedIso ? " · " + t("sinceAt") + " " + started(startedIso) : "";
  return t("on")
    + ' <a href="' + esc(MIC[lang]) + '" target="_blank" rel="noopener">Vleermic</a>'
    + when
    + ' · <a href="' + esc(MANUAL) + '" target="_blank" rel="noopener">' + esc(t("manual")) + "</a>";
}
function applyChrome() {
  document.documentElement.lang = lang;
  document.title = t("title");
  document.getElementById("title").textContent = t("title");
  document.getElementById("lang-en").className = lang === "en" ? "on" : "";
  document.getElementById("lang-nl").className = lang === "nl" ? "on" : "";
  document.getElementById("score-label").textContent = t("score");
  document.getElementById("level-label").textContent = t("level");
  document.getElementById("time-label").textContent = t("time");
  document.getElementById("h-above").textContent = t("above");
  document.getElementById("rule").textContent = t("rule");
  document.getElementById("h-minutes").textContent = t("perMinute");
  document.getElementById("h-windows").textContent = t("recent");
  document.getElementById("since").innerHTML = subtitle(lastData && lastData.started);
}
function setLang(next) {
  lang = next === "nl" ? "nl" : "en";
  localStorage.setItem("batfinder-lang", lang);
  applyChrome();
  if (lastData) render(lastData);
}
function render(data) {
  lastData = data;
  const latest = data.latest;
  const fresh = latest && (Date.now() - Date.parse(latest.t) < 15000);
  const live = document.getElementById("live");
  live.className = fresh ? "live on" : "live";
  live.innerHTML = "<i></i>" + (fresh ? t("listening") : t("stale"));
  document.getElementById("since").innerHTML = subtitle(data.started);
  if (latest) {
    const named = latest.score >= SHOW;
    document.getElementById("kicker").textContent = latest.hit
      ? t("confirmed")
      : (named ? t("strongest") : t("below"));
    document.getElementById("species").textContent = named ? common(latest.species) : "—";
    document.getElementById("sci").textContent = named ? sciOf(latest.species) : "";
    document.getElementById("score").textContent = pct(latest.score);
    document.getElementById("level").textContent = db(latest.rms);
    document.getElementById("when").textContent = clock(latest.t, true);
  } else {
    document.getElementById("kicker").textContent = t("strongest");
    document.getElementById("species").textContent = t("waitAudio");
  }
  const groups = clusters(data.hits);
  const counts = new Map();
  for (const group of groups) {
    counts.set(group.species, (counts.get(group.species) || 0) + 1);
  }
  document.getElementById("tally").innerHTML = Array.from(counts, ([species, n]) =>
    "<span>" + esc(common(species)) + " " + n + "</span>"
  ).join("");
  const hits = document.getElementById("hits");
  hits.innerHTML = groups.length ? groups.map((group) => {
    const quiet = group.rms < 0.01 ? '<div class="quiet">' + esc(t("quiet")) + "</div>" : "";
    const extra = group.n > 1 ? " · " + esc(windowWord(group.n)) : "";
    return '<div class="hit"><div class="when">' + esc(span(group)) + '</div><div><b>'
      + esc(common(group.species)) + '</b><div class="sci">' + esc(sciOf(group.species))
      + extra + "</div>" + quiet + '</div><div class="score">' + pct(group.max)
      + "<br>" + db(group.rms) + "</div></div>";
  }).join("") : '<p class="empty">' + esc(t("none")) + "</p>";
  const minutes = data.minutes || [];
  document.getElementById("bars").innerHTML = minutes.length ? minutes.map((minute) => {
    const height = Math.max(4, Math.round((minute.score || 0) * 104));
    const klass = minute.score >= 0.5 ? "bar hot" : minute.score >= 0.2 ? "bar warm" : "bar";
    const who = minute.score >= SHOW && minute.species ? common(minute.species) : t("score");
    const title = clock(minute.t, false) + " " + who + " " + pct(minute.score || 0);
    return '<div class="' + klass + '" style="height:' + height + 'px" title="' + esc(title) + '"></div>';
  }).join("") : '<p class="empty">' + esc(t("noMinutes")) + "</p>";
  const recent = (data.recent || []).slice(-8).reverse();
  document.getElementById("windows").innerHTML = recent.map((row) =>
    '<div><div class="when">' + esc(clock(row.t, true)) + "</div><div>" + esc(shown(row.score, row.species))
    + '</div><div class="score">' + pct(row.score) + "</div></div>"
  ).join("");
  document.getElementById("foot").textContent =
    (data.windows || 0) + " " + t("foot");
}
async function tick() {
  try {
    const response = await fetch("/overview.json", {cache: "no-store"});
    render(await response.json());
  } catch (error) {
    document.getElementById("live").className = "live";
    document.getElementById("live").innerHTML = "<i></i>" + t("offline");
  }
}
const stored = localStorage.getItem("batfinder-lang");
lang = stored === "nl" ? "nl" : "en";
applyChrome();
document.getElementById("lang-en").addEventListener("click", () => setLang("en"));
document.getElementById("lang-nl").addEventListener("click", () => setLang("nl"));
tick();
setInterval(tick, 3000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/overview.json":
            self._overview()
        elif path in ("/", "/index.html"):
            self._bytes(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
        else:
            self._bytes(404, "text/plain; charset=utf-8", b"not found\n")

    def _overview(self):
        try:
            with open(OVERVIEW, "rb") as handle:
                body = handle.read()
        except OSError:
            body = EMPTY
        self._bytes(200, "application/json; charset=utf-8", body)

    def _bytes(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("overview on port %s" % PORT, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
