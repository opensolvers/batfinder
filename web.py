#!/usr/bin/env python3
"""Small page over BattyBirdNET detections on this board."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.environ.get("BATFINDER_DIR", os.path.dirname(os.path.abspath(__file__)))
OVERVIEW = os.path.join(DIR, "overview.json")
PORT = 8090
EMPTY = b'{"updated":null,"latest":null,"recent":[],"minutes":[],"hits":[]}'

PAGE = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vleermuizen</title>
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
  header { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }
  h1 { margin: 0; font-size: 34px; font-weight: 500; letter-spacing: -0.03em; }
  h2 { margin: 34px 0 10px; font-size: 18px; font-weight: 500; }
  .live, .meta, .kicker, .meter, .when, .score, .quiet, footer, .chips {
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .live { color: var(--muted); font-size: 13px; white-space: nowrap; }
  .live i {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--dim); margin-right: 6px;
  }
  .live.on i { background: var(--good); }
  .meta { color: var(--muted); margin: 6px 0 0; font-size: 14px; }
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
      <h1>Vleermuizen</h1>
      <p class="meta" id="since">BattyBirdNET op de Vleermic</p>
    </div>
    <p class="live" id="live"><i></i>wachten</p>
  </header>
  <section class="now">
    <p class="kicker" id="kicker">Sterkste soort in dit venster</p>
    <h2 class="species" id="species">Wachten op audio</h2>
    <p class="sci" id="sci"></p>
    <div class="meter">
      <div><b id="score">—</b><span>score</span></div>
      <div><b id="level">—</b><span>niveau</span></div>
      <div><b id="when">—</b><span>tijd</span></div>
    </div>
  </section>
  <h2>Boven de drempel</h2>
  <p class="meta">Vijf vensters achter elkaar, ongeveer 2 seconden, op 50% of hoger.</p>
  <div id="tally" class="chips"></div>
  <div id="hits"></div>
  <h2>Per minuut</h2>
  <div id="bars" class="bars"></div>
  <h2>Laatste vensters</h2>
  <div id="windows" class="windows"></div>
  <footer id="foot"></footer>
</main>
<script>
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
function dutch(label) {
  const bit = parts(label);
  return NAMES[bit.sci] || bit.common || bit.sci || "Onbekend";
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
function clock(iso, withSeconds) {
  if (!iso) return "—";
  const stamp = iso.length === 16 ? iso + ":00Z" : iso;
  const options = {timeZone: "Europe/Amsterdam", hour: "2-digit", minute: "2-digit"};
  if (withSeconds) options.second = "2-digit";
  return new Intl.DateTimeFormat("nl-NL", options).format(new Date(stamp));
}
function started(iso) {
  if (!iso) return "";
  return new Intl.DateTimeFormat("nl-NL", {
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
const SHOW = 0.10;
function shown(score, label) {
  return score >= SHOW ? dutch(label) : "—";
}
function render(data) {
  const latest = data.latest;
  const fresh = latest && (Date.now() - Date.parse(latest.t) < 15000);
  const live = document.getElementById("live");
  live.className = fresh ? "live on" : "live";
  live.innerHTML = "<i></i>" + (fresh ? "luistert" : "geen verse audio");
  document.getElementById("since").textContent =
    "BattyBirdNET op de Vleermic" + (data.started ? " · sinds " + started(data.started) : "");
  if (latest) {
    const named = latest.score >= SHOW;
    document.getElementById("kicker").textContent = latest.hit
      ? "Bevestigd in dit venster"
      : (named ? "Sterkste soort in dit venster" : "Onder 10%");
    document.getElementById("species").textContent = named ? dutch(latest.species) : "—";
    document.getElementById("sci").textContent = named ? sciOf(latest.species) : "";
    document.getElementById("score").textContent = pct(latest.score);
    document.getElementById("level").textContent = db(latest.rms);
    document.getElementById("when").textContent = clock(latest.t, true);
  }
  const groups = clusters(data.hits);
  const counts = new Map();
  for (const group of groups) {
    counts.set(group.species, (counts.get(group.species) || 0) + 1);
  }
  document.getElementById("tally").innerHTML = Array.from(counts, ([species, n]) =>
    "<span>" + esc(dutch(species)) + " " + n + "</span>"
  ).join("");
  const hits = document.getElementById("hits");
  hits.innerHTML = groups.length ? groups.map((group) => {
    const quiet = group.rms < 0.01 ? '<div class="quiet">stille microfoon</div>' : "";
    const extra = group.n > 1 ? " · " + group.n + " vensters" : "";
    return '<div class="hit"><div class="when">' + esc(span(group)) + '</div><div><b>'
      + esc(dutch(group.species)) + '</b><div class="sci">' + esc(sciOf(group.species))
      + extra + "</div>" + quiet + '</div><div class="score">' + pct(group.max)
      + "<br>" + db(group.rms) + "</div></div>";
  }).join("") : '<p class="empty">Nog geen bevestiging.</p>';
  const minutes = data.minutes || [];
  document.getElementById("bars").innerHTML = minutes.length ? minutes.map((minute) => {
    const height = Math.max(4, Math.round((minute.score || 0) * 104));
    const klass = minute.score >= 0.5 ? "bar hot" : minute.score >= 0.2 ? "bar warm" : "bar";
    const who = minute.score >= SHOW && minute.species ? dutch(minute.species) : "score";
    const title = clock(minute.t, false) + " " + who + " " + pct(minute.score || 0);
    return '<div class="' + klass + '" style="height:' + height + 'px" title="' + esc(title) + '"></div>';
  }).join("") : '<p class="empty">Nog geen minuten.</p>';
  const recent = (data.recent || []).slice(-8).reverse();
  document.getElementById("windows").innerHTML = recent.map((row) =>
    '<div><div class="when">' + esc(clock(row.t, true)) + "</div><div>" + esc(shown(row.score, row.species))
    + '</div><div class="score">' + pct(row.score) + "</div></div>"
  ).join("");
  document.getElementById("foot").textContent =
    (data.windows || 0) + " vensters deze sessie · naam vanaf 10% · 50% over 2 seconden · venster 0,56 s · EU-lijst";
}
async function tick() {
  try {
    const response = await fetch("/overview.json", {cache: "no-store"});
    render(await response.json());
  } catch (error) {
    document.getElementById("live").className = "live";
    document.getElementById("live").innerHTML = "<i></i>geen verbinding";
  }
}
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
            self._bytes(404, "text/plain; charset=utf-8", b"niet gevonden\n")

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
