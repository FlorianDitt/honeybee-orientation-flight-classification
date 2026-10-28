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
    <li>Vor dem ersten Sammelflug lernen junge Bienen die Lage ihres Stocks: <strong>Schleifen und Bögen</strong> mit Blick zum Flugloch statt direktem Abflug</li>
    <li>Anteil Orientierungsflüge ≈ <strong>Nachschub an Sammlerinnen</strong>, ein Maß für die Vitalität des Volkes</li>
    <li>Pestizide (Neonicotinoide) stören Orientierung und Heimfindung: ein Monitor am Flugloch wäre ein <strong>nicht-invasives Frühwarnsignal</strong></li>
  </ul>
  <div class="lit"><b>Capaldi et al. (2000)</b>: Orientierungsflüge per Harmonic Radar, <i>Nature</i><br><b>Degen et al. (2015)</b>: Erkundungsverhalten bei Orientierungsflügen, <i>Animal Behaviour</i><br><b>Henry et al. (2012)</b>: Pestizid senkt Heimkehrrate von Sammlerinnen, <i>Science</i></div>
  <div class="facts">
    <div class="fact"><b>96 × 30 s</b>75 Seq. Stock A, 21 Stock B</div>
    <div class="fact"><b>59,94 fps</b>1080 × 1920, GoPro</div>
    <div class="fact"><b>Keine Labels</b>Start/Ziel der Bahn liefern Selbst-Labels</div>
    <div class="fact"><b>A ≫ B</b>~70 vs. ~9 Flugbahnen pro 30 s</div>
  </div>
</div>
<div class="hero">
  <img src="assets/flights_seq050.jpg">
  <div class="cap"><b>Stock A</b>, Seq. 050, automatisch getrackt: <b style="color:#e0662a">kurvige Bahnen</b> kreisen vor dem Flugloch, <b style="color:#3d93c9">gerade Bahnen</b> queren die Flugzone</div>
</div>
</div>

---

<!-- Folie 2 · Methode -->

## Methode: Flugbahnen selbst erzeugen, dann klassifizieren

<style scoped>
h2 { margin-bottom: 20px; }
.grid { display: grid; grid-template-columns: 1fr 520px; gap: 44px; }
ol { font-size: 17px; line-height: 1.36; padding-left: 1.3em; margin: 0; }
ol li { margin-bottom: 8px; }
ol li::marker { color: var(--accent); font-weight: 700; }
.plot img { width: 520px; display: block; }
.plot .cap { font-size: 14px; color: var(--muted); margin-top: 2px; line-height: 1.4; }
.plot .cap b { color: var(--ink); }
.split { margin-top: 14px; }
.bar { display: flex; height: 26px; }
.seg { height: 100%; border-right: 2px solid var(--bg); color: #fff; font-size: 13px; font-weight: 600;
       display: flex; align-items: center; padding-left: 10px; box-sizing: border-box; white-space: nowrap; overflow: hidden; }
.seg:first-child { border-radius: 5px 0 0 5px; }
.seg:last-child { border-radius: 0 5px 5px 0; border-right: none; }
.gap { width: 18px; }
.legend { display: flex; gap: 18px; font-size: 13px; color: var(--muted); margin-top: 6px; }
.legend b { color: var(--ink); font-weight: 600; }
</style>

<div class="grid">
<div>
  <ol>
    <li><strong>Vordergrund:</strong> Median-Hintergrund abziehen; Gras-Maske aus Pixeln, die &gt; 8 % der Zeit „bewegt“ sind</li>
    <li><strong>Tracking:</strong> Hungarian-Zuordnung mit Geschwindigkeitsvorhersage, Lücken bis 3 Frames</li>
    <li><strong>Selbst-Labels:</strong> Start auf dem Brett → Abflug, Ende auf dem Brett → Anflug; dazu Geradheit, Windung, Dauer</li>
    <li><strong>Handlabels:</strong> ~300 Bahnen in 4 Klassen: Orientierung · Sammelabflug · suchender Anflug · Artefakt</li>
    <li><strong>Lernen:</strong> Trajektorien-Encoder (GRU) gegen Baseline Krümmungsschwelle; Macro-F1, daraus Anteil Orientierungsflüge pro Sequenz</li>
  </ol>
</div>
<div class="plot">
  <img src="assets/flight_counts.png">
  <div class="cap"><b>Vorstudie</b> auf Trainings- und Validierungsdaten (Stock A, 7 × 30 s): kurvige Abflüge in 5 von 7 Sequenzen; die meisten Bahnen reißen im Gras ab.</div>
</div>
</div>

<div class="split">
  <div style="display:flex; gap:0">
    <div class="bar" style="flex:75">
      <div class="seg" style="width:73.33%; background:var(--train)">Training · Seq. 015–069</div>
      <div class="seg" style="width:1.33%; background:var(--buffer)"></div>
      <div class="seg" style="width:18.67%; background:var(--val)">Validierung</div>
      <div class="seg" style="width:1.33%; background:var(--buffer)"></div>
      <div class="seg" style="width:5.34%; background:var(--test-a)"></div>
    </div>
    <div class="gap"></div>
    <div class="bar" style="flex:21">
      <div class="seg" style="width:100%; background:var(--test-b)">Test B · Stock B</div>
    </div>
  </div>
  <div class="legend"><span><b>Split nach Zeitblöcken</b>, nie nach Frames</span><span>grau: Puffer, verworfen</span><span><b style="color:var(--test-a)">Test A</b> gleicher Stock, 2 min</span><span><b style="color:var(--test-b)">Test B</b> neuer Stock, 10,5 min</span><span>Tuning nur auf Validierung</span></div>
</div>

---

<!-- Folie 3 · Ergebnisse & Diskussion -->

## Ergebnisse und Diskussion

<style scoped>
h2 { margin-bottom: 22px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 26px; }
.card { border-radius: 8px; padding: 14px 16px; background: #f1efe9; }
.card .k { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 600; }
.card .v { font-size: 30px; font-weight: 700; margin: 4px 0 2px; }
.card .s { font-size: 14px; color: var(--muted); line-height: 1.35; }
.card.todo { background: none; border: 2px dashed var(--line); }
.card.todo .v { color: #c4c7cc; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 44px; }
h3 { margin-bottom: 8px; }
ul { font-size: 17px; line-height: 1.4; margin: 0; }
ul li { margin-bottom: 7px; }
.ask { margin-top: 14px; font-size: 17px; border-left: 3px solid var(--accent); padding: 4px 0 4px 14px; }
</style>

<div class="cards">
  <div class="card"><div class="k">Flugbahnen</div><div class="v">509</div><div class="s">in 7 × 30 s Stock A, davon 70 Abflüge und 76 Anflüge</div></div>
  <div class="card"><div class="k">Kurvige Abflüge</div><div class="v">21</div><div class="s">≈ 3 pro 30 s → ~165 Kandidaten im Training (Vorstudie)</div></div>
  <div class="card"><div class="k">Fragmente</div><div class="v">71 %</div><div class="s">Bahn beginnt oder endet im Gras: Biene geht verloren</div></div>
  <div class="card todo" style="border-color:var(--test-b)"><div class="k">Test A / B · Macro-F1</div><div class="v">– / –</div><div class="s">GRU vs. Krümmungs-Baseline</div></div>
</div>

<div class="cols">
<div>
  <h3>Erkenntnisse und Grenzen</h3>
  <ul>
    <li><strong>Kurvig ≠ Orientierung:</strong> auch suchende Anflüge und Ausweichmanöver kurven, genau das muss das Modell trennen</li>
    <li><strong>Tarnung:</strong> Bienen über Gras kaum sichtbar, daher 71 % Fragmente</li>
    <li><strong>Blickrichtung</strong> zum Stock bei ~30 px Körperlänge nicht sicher messbar</li>
    <li><strong>Stock B bedeckt:</strong> ~9 Flugbahnen pro 30 s, Test B klein; Wetter als Störgröße</li>
  </ul>
</div>
<div>
  <h3>Nächste Schritte</h3>
  <ul>
    <li>Detektor für die Flugzone trainieren, Fragmente zu ganzen Bahnen verbinden</li>
    <li>~300 Bahnen von Hand labeln, Inter-Rater-Check an 50 Bahnen</li>
    <li>GRU gegen Baseline auf Test A und B, Anteil Orientierungsflüge über die Zeit</li>
  </ul>
  <div class="ask"><strong>Offene Frage:</strong> Trennt die Bahnform allein Orientierung von suchender Landung, oder braucht es den Startpunkt?</div>
</div>
</div>
