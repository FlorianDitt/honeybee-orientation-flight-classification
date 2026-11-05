---
marp: true
theme: hive
paginate: true
lang: de
footer: "Orientierungsflug oder Sammelflug? · WDS224 · Florian Dittmann"
---

<!-- Folie 1 · Motivation & Daten -->

<style scoped>
.kicker { font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.head { margin: 4px 0 20px; }
.head h1 { font-size: 42px; margin: 0 0 2px; }
.head span { font-size: 19px; color: var(--muted); }
section { padding-top: 48px; }
.grid { display: grid; grid-template-columns: 1fr 392px; gap: 48px; }
.q { font-size: 23px; font-weight: 600; line-height: 1.3; margin-bottom: 14px; }
ul.m { font-size: 17px; line-height: 1.4; margin: 0 0 14px; }
ul.m li { margin-bottom: 7px; }
.lit { font-size: 14px; line-height: 1.45; color: var(--muted); border-left: 3px solid var(--line); padding-left: 12px; }
.lit b { color: var(--ink); font-weight: 600; }
.hero img { width: 392px; border-radius: 6px; display: block; }
.hero .cap { font-size: 13px; color: var(--muted); margin-top: 5px; line-height: 1.35; }
.hero .cap b { font-weight: 600; }
.facts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px 20px; margin-top: 14px; }
.fact { border-top: 1px solid var(--line); padding-top: 6px; font-size: 14px; color: var(--muted); line-height: 1.3; }
.fact b { display: block; font-size: 20px; color: var(--ink); }
</style>

<div class="kicker">WDS224 · Machine Learning System Design and Operations</div>
<div class="head"><h1>Orientierungsflug oder Sammelflug?</h1><span>Flugbahnen vor dem Flugloch als Indikator für neue Sammlerinnen</span></div>

<div class="grid">
<div>
  <div class="q">Erkennt ein Modell an der Flugbahn, ob eine junge Biene gerade ihren Stock kennenlernt?</div>
  <ul class="m">
    <li><strong>Orientierungsflug:</strong> Vor dem ersten Sammelflug fliegen junge Arbeiterinnen mehrere Erkundungsflüge. Am Flugloch wenden sie sich zum Stock und fliegen <strong>Bögen und Schleifen</strong>; mit jedem Flug schneller und weiter, abhängig von Erfahrung, nicht Alter</li>
    <li><strong>Zweck:</strong> Sie lernen Landschaftsmerkmale, mit denen sie später heimfinden. Ohne Orientierungsflüge keine Sammlerin</li>
    <li><strong>Indikator:</strong> Anteil Orientierungsflüge ≈ Nachschub an Sammlerinnen. Eine Kamera am Flugloch misst das <strong>nicht-invasiv</strong>, ohne Radar oder RFID, z. B. als Frühwarnsignal bei Pestiziden</li>
  </ul>
  <div class="lit"><b>Capaldi et al. (2000)</b>: Ontogenese des Orientierungsflugs, Harmonic Radar, <i>Nature</i><br><b>Degen et al. (2016)</b>: Bienen lernen Landschaftsmerkmale beim Orientierungsflug, <i>Curr. Biol.</i><br><b>Henry et al. (2012)</b>: Pestizid senkt Heimkehrrate von Sammlerinnen, <i>Science</i></div>
  <div class="facts">
    <div class="fact"><b>96 × 30 s</b>75 Seq. Stock A, 21 Stock B</div>
    <div class="fact"><b>59,94 fps</b>1080 × 1920, GoPro</div>
    <div class="fact"><b>Keine Labels</b>Start/Ziel der Bahn liefern Selbst-Labels</div>
    <div class="fact"><b>A ≫ B</b>~75 vs. ~9 Flugbahnen pro 30 s</div>
  </div>
</div>
<div class="hero">
  <img src="assets/flights_seq050.jpg">
  <div class="cap"><b>Stock A</b>, Seq. 050, automatisch getrackt: <b style="color:#e0662a">kurvige Bahnen</b> kreisen vor dem Flugloch, <b style="color:#3d93c9">gerade Bahnen</b> queren die Flugzone</div>
</div>
</div>

---

<!-- Folie 2 · System -->

## System: vom Rohvideo zum Indikator

<style scoped>
h2 { margin-bottom: 18px; }
.flow { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 20px; }
.step { position: relative; background: #f1efe9; border-radius: 8px; padding: 10px 12px 9px; }
.step:not(:last-child)::after { content: "→"; position: absolute; right: -13px; top: 50%; transform: translateY(-50%);
  color: var(--accent); font-weight: 700; font-size: 18px; }
.step .n { font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: 0.08em; }
.step b { display: block; font-size: 16px; margin: 1px 0 3px; }
.step span { display: block; font-size: 13px; line-height: 1.3; color: var(--muted); }
.step code { display: inline-block; margin-top: 5px; font-size: 11px; }
.grid { display: grid; grid-template-columns: 1fr 430px; gap: 36px; }
ul.d { font-size: 16px; line-height: 1.36; margin: 0; }
ul.d li { margin-bottom: 7px; }
.shot img { width: 430px; border-radius: 6px; display: block; border: 1px solid var(--line); }
.shot .cap { font-size: 12.5px; color: var(--muted); margin-top: 4px; line-height: 1.35; }
.split { margin-top: 12px; }
.bars { display: flex; gap: 14px; }
.bar { display: flex; height: 22px; border-radius: 5px; overflow: hidden; }
.bar div { height: 100%; color: #fff; font-size: 11.5px; font-weight: 600; display: flex; align-items: center;
  padding-left: 8px; box-sizing: border-box; white-space: nowrap; overflow: hidden; border-right: 2px solid var(--bg); }
.bar div:last-child { border-right: none; }
.a { flex: 75; } .b { flex: 21; }
.tr { width: 73.3%; background: #2f4858; } .bu { width: 1.4%; background: #d1d5db; }
.va { width: 18.7%; background: #6b8fa3; } .ta { width: 5.2%; background: #d99a1e; } .tb { width: 100%; background: #b5541c; }
.legend { display: flex; gap: 16px; font-size: 12.5px; color: var(--muted); margin-top: 5px; flex-wrap: wrap; }
.legend b { color: var(--ink); font-weight: 600; }
</style>

<div class="flow">
  <div class="step"><div class="n">1</div><b>Tracking</b><span>Hintergrundmodell, Hungarian-Zuordnung, Fragmente verbinden</span><code>beeflight-tracks</code></div>
  <div class="step"><div class="n">2</div><b>Selbst-Labels</b><span>Start/Ziel am Brett, Geradheit, Windung → stratifizierte Stichprobe</span><code>beeflight-sample</code></div>
  <div class="step"><div class="n">3</div><b>Handlabels</b><span>Web-App, 4 Klassen, 3 Stimmen pro Bahn, Mehrheit entscheidet</span><code>labeler/ · beeflight-vote</code></div>
  <div class="step"><div class="n">4</div><b>Modell</b><span>GRU auf der Bahn vs. Krümmungs-Baseline, Macro-F1</span><code>PyTorch</code></div>
  <div class="step"><div class="n">5</div><b>Indikator</b><span>Anteil Orientierungsflüge pro Sequenz über die Zeit</span><code>beeflight-run</code></div>
</div>

<div class="grid">
<div>
  <h3>Designentscheidungen</h3>
  <ul class="d">
    <li><strong>Labels überleben Tracker-Updates:</strong> jedes Label speichert die Bahn und die Tracker-Version; nach v2 und v3 wurden die Labels automatisch auf dieselben Flüge übertragen</li>
    <li><strong>Mehrere Labelnde:</strong> Freunde labeln online kurze Clips (GitHub Pages), nach einer Übungsrunde mit Rückmeldung; Übereinstimmung als Krippendorffs α</li>
    <li><strong>Kein Leck:</strong> Split nach Zeitblöcken mit Puffer, Schwellen nur auf Validierung, eigene Testlabels und Auswertung erst nach dem Einfrieren</li>
  </ul>
</div>
<div class="shot">
  <img src="assets/labeler.png">
  <div class="cap"><b>Label-App:</b> Zeitlupe in Schleife, Bahn synchron eingezeichnet, Tasten 1–4</div>
</div>
</div>

<div class="split">
  <div class="bars">
    <div class="bar a"><div class="tr">Training · Seq. 015–069</div><div class="bu"></div><div class="va">Validierung</div><div class="bu"></div><div class="ta"></div></div>
    <div class="bar b"><div class="tb">Test B · Stock B</div></div>
  </div>
  <div class="legend"><span><b>Split nach Zeitblöcken</b>, nie nach Frames</span><span>grau: Puffer, verworfen</span><span><b style="color:#d99a1e">Test A</b> gleicher Stock, 2 min</span><span><b style="color:#b5541c">Test B</b> neuer Stock, 10,5 min</span></div>
</div>

---

<!-- Folie 3 · Ergebnisse & Diskussion -->

## Ergebnisse und Diskussion

<style scoped>
h2 { margin-bottom: 16px; }
.top { display: grid; grid-template-columns: 480px 1fr; gap: 36px; margin-bottom: 14px; }
.chart img { width: 480px; display: block; }
.chart .cap { font-size: 13px; color: var(--muted); line-height: 1.35; margin-top: 2px; }
.chart .cap b { color: var(--ink); }
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-content: start; }
.card { border-radius: 8px; padding: 10px 14px; background: #f1efe9; }
.card .k { font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 600; }
.card .v { font-size: 27px; font-weight: 700; margin: 2px 0 0; line-height: 1.2; }
.card .s { font-size: 13px; color: var(--muted); line-height: 1.3; }
.card.todo { background: none; border: 2px dashed var(--line); }
.card.todo .v { color: #c4c7cc; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
ul { font-size: 16px; line-height: 1.36; margin: 0; }
ul li { margin-bottom: 6px; }
.ask { margin-top: 10px; font-size: 16px; border-left: 3px solid var(--accent); padding: 3px 0 3px 12px; }
</style>

<div class="top">
<div class="chart">
  <img src="assets/tracker_versions.png">
  <div class="cap"><b>Fehleranalyse statt Bauchgefühl:</b> Anteil vollständiger Bahnen (Start und Ende am Brett oder Bildrand). v2: Zonen zu eng, Schwelle zu hoch. v3: geteilte Blobs, enge Kurven, Neustarts.</div>
</div>
<div class="cards">
  <div class="card"><div class="k">Flugbahnen</div><div class="v">4923</div><div class="s">Training + Validierung, Stock A, 34,5 min</div></div>
  <div class="card"><div class="k">Kurvige Abflüge</div><div class="v">168</div><div class="s">plus 677 Brett → Brett (Schleifen oder kurze Hüpfer)</div></div>
  <div class="card"><div class="k">Handlabels</div><div class="v">165 <span style="font-size:16px;color:var(--muted);font-weight:400">/ 380</span></div><div class="s">Ziel: 3 Stimmen pro Bahn, Krippendorffs α</div></div>
  <div class="card todo"><div class="k">Test A / B · Macro-F1</div><div class="v">– / –</div><div class="s">GRU vs. Krümmungs-Baseline</div></div>
</div>
</div>

<div class="cols">
<div>
  <h3>Erkenntnisse und Grenzen</h3>
  <ul>
    <li><strong>Kurvig ≠ Orientierung:</strong> auch suchende Anflüge kurven, genau das muss das Modell trennen. Auch Menschen: erste Zweitstimmen 65 % gleich, 22 von 31 Abweichungen sind „Orientierung“</li>
    <li><strong>Tarnung:</strong> über dem Gras reißen noch 33 % der Bahnen an einem Ende ab</li>
    <li><strong>Stock B bedeckt:</strong> ~9 Bahnen pro 30 s, Test B klein</li>
  </ul>
</div>
<div>
  <h3>Nächste Schritte</h3>
  <ul>
    <li>380 Bahnen mit je 3 Stimmen labeln, α berichten</li>
    <li>GRU gegen Baseline auf Test A und B, Indikator über die Zeit</li>
    <li>Gelernter Detektor gegen die restlichen Abrisse, wenn Zeit bleibt</li>
  </ul>
  <div class="ask"><strong>Offene Frage:</strong> Reicht die Bahnform, oder braucht es den Startpunkt?</div>
</div>
</div>
