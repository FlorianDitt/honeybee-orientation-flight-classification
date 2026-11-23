---
marp: true
theme: hive
paginate: true
lang: de
footer: "Orientierungsflug oder Sammelflug? · WDS224 · Florian Dittmann"
---

<!-- Folie 1 · Frage -->

<style scoped>
section { padding-top: 48px; }
.wrap { display: grid; grid-template-columns: 1fr 500px; gap: 40px; align-items: start; }
.kicker { font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
h1 { font-size: 46px; margin: 8px 0 18px; }
.q { font-size: 23px; line-height: 1.35; margin-bottom: 26px; }
.cls { display: grid; grid-template-columns: 14px 1fr; gap: 10px 12px; align-items: center; font-size: 19px; }
.cls i { width: 14px; height: 14px; border-radius: 50%; display: block; }
.cls span { color: var(--muted); }
.why4 { margin-top: 26px; font-size: 17px; color: var(--muted); border-left: 3px solid var(--accent); padding-left: 12px; line-height: 1.35; }
.hero { width: 500px; height: 520px; object-fit: cover; object-position: top; border-radius: 8px; display: block; }
.media { position: relative; width: 500px; height: 520px; }
.media video { position: absolute; inset: 0; opacity: 0; transition: opacity 0.6s; }
.frag { display: none; }
</style>

<div class="wrap">
<div>
  <div class="kicker">WDS224 · Machine Learning System Design and Operations</div>
  <h1>Orientierungsflug oder Sammelflug?</h1>
  <div class="q">Bevor eine Biene sammelt, fliegt sie Orientierungsflüge<sup>1</sup>: Sie schwebt mit Blick zum Flugloch<sup>1</sup> und lernt die Umgebung des Stocks<sup>2</sup>. <b>Erkennt ein Modell das allein an der Flugbahn?</b></div>
  <div class="cls">
    <i style="background:#e0662a"></i><div><b>Orientierungsflug</b> <span>Schleifen, kehrt zurück</span></div>
    <i style="background:#3d93c9"></i><div><b>Sammelabflug</b> <span>fliegt weg</span></div>
    <i style="background:#6b8f5a"></i><div><b>Anflug</b> <span>landet</span></div>
    <i style="background:#a8adb5"></i><div><b>Artefakt</b> <span>keine echte Bienenbahn</span></div>
  </div>
</div>
<div class="media">
  <img class="hero" src="assets/leer.png">
  <video class="hero" src="assets/bahn1.mp4" muted playsinline preload="auto"></video>
  <video class="hero" src="assets/bahn2.mp4" muted playsinline preload="auto"></video>
  <video class="hero" src="assets/bahn3.mp4" muted playsinline preload="auto"></video>
  <video class="hero" src="assets/bahn4.mp4" muted playsinline preload="auto"></video>
</div>
</div>

<div class="frag">

* Orientierungsflug
* Sammelabflug
* Anflug
* Artefakt

</div>

<script>
/* Folie 1: vier versteckte Listenpunkte sind Marp-Fragmente. Jeder Tastendruck spielt die nächste Bahn als Video;
   das letzte Bild bleibt stehen und zeigt alle Bahnen bis dahin. Zurück blendet die Bahn wieder aus. */
document.querySelectorAll(".frag li").forEach((li, k) => {
  const v = li.closest("section").querySelectorAll("video.hero")[k];
  new MutationObserver(() => {
    if (li.getAttribute("data-bespoke-marp-fragment") === "active") { v.currentTime = 0; v.style.opacity = 1; v.play(); }
    else { v.pause(); v.style.opacity = 0; }
  }).observe(li, { attributes: true, attributeFilter: ["data-bespoke-marp-fragment"] });
});
</script>

<div class="fn"><sup>1</sup> Capaldi et al. (2000). Ontogeny of orientation flight in the honeybee revealed by harmonic radar. <i>Nature</i> 403, 537–540 · <sup>2</sup> Degen et al. (2016). Honeybees learn landscape features during exploratory orientation flights. <i>Current Biology</i> 26(20), 2800–2804. doi:10.1016/j.cub.2016.08.013</div>

<!--
Bild leer: Flugloch, Brett, Wiese
→ Taste: Orientierungsflug (halbe Geschw.), bleibt
→ Taste: Sammelabflug, bleibt
→ Taste: Anflug, bleibt
→ Taste: Artefakt (Blatt), bleibt
→ Taste: Folie 2
→ vor dem Sammeln: Orientierungsflüge, 1–18 pro Biene, ab Tag 3–14 (Capaldi)
→ Start: Schweben, Blick zum Flugloch (Capaldi)
→ lernt Umgebung; ohne Orientierungsflug: 14 von 14 verloren (Degen)
→ beide mit Radar: Transponder, eine Biene pro Flug
→ Kamera vorm Stock sieht alle
→ Frage: reicht die Bahn?
-->
<!-- Nicht sagen "Anteil = Zahl neuer Sammlerinnen": eine Biene fliegt 1–18 Orientierungsflüge, und Sammlerinnen orientieren sich neu, wenn sich die Umgebung ändert (Capaldi, Methods). Der Anteil ist Motivation, kein Zähler. -->

---

<!-- Folie 2 · Weg -->

## Von der Bahn zur Klasse, getestet auf einem neuen Stock

<style scoped>
h2 { margin-bottom: 40px; }
.flow { display: grid; grid-template-columns: repeat(4, 1fr); margin-bottom: 80px; }
.step { background: #f1efe9; padding: 14px 18px 14px 32px; font-size: 18px; line-height: 1.4; color: var(--muted); min-height: 190px; clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 50%, calc(100% - 18px) 100%, 0 100%, 18px 50%); }
.step:first-child { clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 50%, calc(100% - 18px) 100%, 0 100%); padding-left: 18px; }
.step b { display: block; font-size: 25px; color: var(--ink); margin-bottom: 4px; }
.step .big { display: block; font-size: 30px; font-weight: 700; color: var(--accent); margin-top: 6px; }
.step.hi { background: #f7e7c3; }
.bars { display: flex; gap: 4px; height: 56px; margin-bottom: 8px; }
.bars div { border-radius: 4px; color: #fff; font-size: 16px; font-weight: 600; display: flex; align-items: center; padding-left: 12px; box-sizing: border-box; overflow: hidden; white-space: nowrap; }
.tr { background: var(--train); } .va { background: var(--val); } .ta { background: var(--test-a); } .tb { background: var(--test-b); } .bu { background: var(--buffer); padding: 0 !important; }
.sub { font-size: 18px; color: var(--muted); }
</style>

<div class="flow">
  <div class="step"><b>Tracking</b>Chiron 2013<sup>1</sup> + Huang 2008<sup>2</sup>, ohne Training<span class="big">73 % korrekt<sup>3</sup></span></div>
  <div class="step"><b>Labeln</b>Web-App, 4 Klassen; Test: 3 Personen, Mehrheit<span class="big">1428 Bahnen</span></div>
  <div class="step hi"><b>Klassifizieren</b>ResNet<sup>4</sup> auf der Bahn, 5 Seeds gemittelt<sup>5</sup>, Bienenfilter<sup>6</sup></div>
  <div class="step"><b>Indikator</b>Anteil Orientierungsflüge pro Aufnahme</div>
</div>

<h3>Aufteilung nach Zeitblöcken, Test nur einmal nach dem Einfrieren</h3>
<div class="bars">
  <div class="tr" style="flex:55">Training · Stock A</div><div class="bu" style="flex:1"></div>
  <div class="va" style="flex:14">Val</div><div class="bu" style="flex:1"></div>
  <div class="ta" style="flex:5">A</div>
  <div class="tb" style="flex:21;margin-left:14px">Test B · Stock B</div>
</div>
<div class="sub">Test A: gleicher Stock, später aufgenommen · Test B: neuer Stock, nie gesehen · grau: Puffer, verworfen</div>

<div class="fn"><sup>1</sup> Chiron, Gomez-Krämer, Ménard (2013). <i>EURASIP J. Image and Video Processing</i> 2013:59 · <sup>2</sup> Huang, Wu, Nevatia (2008). <i>ECCV 2008</i> · <sup>3</sup> 33 zufällige Val-Bahnen, blind bewertet, 95 %-Intervall 56–85 % nach Wilson (1927). <i>J. Am. Stat. Assoc.</i> 22, 209–212 · <sup>4</sup> Ismail Fawaz et al. (2019). <i>Data Min. Knowl. Disc.</i> 33, 917–963 · <sup>5</sup> Lakshminarayanan, Pritzel, Blundell (2017). Deep Ensembles. <i>NeurIPS 2017</i> · <sup>6</sup> Ultralytics YOLO26 (2026): Bahn ohne erkannte Biene = Artefakt</div>

<!--
4 Schritte
→ Tracker: Literatur, kein Training, 73 %
→ Labels: alles selbst, Test mit 3 Personen
→ Modell sieht nur Bahn
→ Test: neuer Stock, einmal
-->

---

<!-- Folie 3 · Antwort -->

## Auf dem neuen Stock tendenziell besser als die Regel

<style scoped>
h2 { margin-bottom: 22px; }
.grid3 { display: grid; grid-template-columns: 1fr 400px; gap: 44px; }
.cap { font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 600; margin-bottom: 10px; }
.grp { font-size: 17px; font-weight: 700; margin: 16px 0 4px; }
.grp:first-of-type { margin-top: 0; }
.dr { display: grid; grid-template-columns: 210px 1fr 56px; align-items: center; height: 41px; font-size: 16px; }
.dr .l { color: var(--muted); }
.dr .t { position: relative; height: 100%; border-left: 1px solid var(--line); background: linear-gradient(90deg, transparent calc(50% - 1px), var(--line) calc(50% - 1px) 50%, transparent 50% calc(75% - 1px), var(--line) calc(75% - 1px) 75%, transparent 75% calc(100% - 1px), var(--line) calc(100% - 1px)); }
.dr .z { position: absolute; top: 0; bottom: 0; left: 25%; border-left: 2px dashed #b9bdc4; }
.dr .ci { position: absolute; top: 50%; height: 8px; margin-top: -4px; border-radius: 4px; opacity: .35; }
.dr .dot { position: absolute; top: 50%; width: 16px; height: 16px; margin: -8px 0 0 -8px; border-radius: 50%; }
.dr b { text-align: right; font-size: 18px; }
.dr.r .ci, .dr.r .dot { background: #a8adb5; } .dr.r b { color: var(--muted); font-weight: 600; }
.dr.m .ci, .dr.m .dot { background: var(--accent); }
.dr.u .ci, .dr.u .dot { background: #8a5a00; }
.axis { display: grid; grid-template-columns: 210px 1fr 56px; font-size: 13px; color: var(--muted); margin-top: 6px; }
.axis .ax { position: relative; height: 18px; } .axis i { font-style: normal; position: absolute; transform: translateX(-50%); white-space: nowrap; }
.card { background: #f1efe9; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; }
table.ind { border-collapse: collapse; width: 100%; font-size: 16px; }
table.ind th { font-weight: 600; color: var(--muted); text-align: right; font-size: 13px; padding: 0 0 4px; }
table.ind th:first-child, table.ind td:first-child { text-align: left; }
table.ind td { text-align: right; padding: 2px 0; }
table.ind td.big { font-size: 30px; font-weight: 700; color: var(--accent); line-height: 1.1; }
table.ind td.lab { font-size: 22px; color: var(--muted); }
.f1 { font-size: 14px; color: var(--muted); margin-top: 8px; border-top: 1px solid #e2ded4; padding-top: 8px; }
.kr { display: grid; grid-template-columns: 86px 1fr 46px 96px; align-items: center; height: 30px; font-size: 15px; }
.kr .bar { height: 14px; border-radius: 7px; background: #e2ded4; position: relative; }
.kr .bar i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 7px; background: #a8adb5; }
.kr.best .bar i { background: var(--accent); }
.kr b { text-align: right; }
.kr span.pp { text-align: right; color: var(--muted); font-size: 13px; }
.kr.hd { height: 18px; font-size: 12px; color: var(--muted); }
.take { margin-top: 20px; font-size: 20px; border-left: 3px solid var(--accent); padding-left: 14px; }
</style>

<div class="grid3">
<div>
<div class="cap">Balanced Accuracy auf Test · Balken = Unsicherheit (Fußnote)</div>
<div class="grp">Test A · gleicher Stock</div>
<div class="dr r"><span class="l">Regel</span><span class="t"><i class="z"></i><i class="ci" style="left:61.6%;width:calc(65.3% - 61.6%)"></i><i class="dot" style="left:64.2%"></i></span><b>0,64</b></div>
<div class="dr m"><span class="l">Modell</span><span class="t"><i class="z"></i><i class="ci" style="left:64.3%;width:calc(67.2% - 64.3%)"></i><i class="dot" style="left:65.8%"></i></span><b>0,66</b></div>
<div class="dr u"><span class="l">Modell, Labels einstimmig</span><span class="t"><i class="z"></i><i class="ci" style="left:78.9%;width:calc(83.5% - 78.9%)"></i><i class="dot" style="left:80.0%"></i></span><b>0,80</b></div>
<div class="grp">Test B · neuer Stock</div>
<div class="dr r"><span class="l">Regel</span><span class="t"><i class="z"></i><i class="ci" style="left:60.7%;width:calc(75.8% - 60.7%)"></i><i class="dot" style="left:67.7%"></i></span><b>0,68</b></div>
<div class="dr m"><span class="l">Modell</span><span class="t"><i class="z"></i><i class="ci" style="left:70.3%;width:calc(81.2% - 70.3%)"></i><i class="dot" style="left:75.8%"></i></span><b>0,76</b></div>
<div class="dr u"><span class="l">Modell, Labels einstimmig</span><span class="t"><i class="z"></i><i class="ci" style="left:74.2%;width:calc(98.8% - 74.2%)"></i><i class="dot" style="left:91.0%"></i></span><b>0,91</b></div>
<div class="axis"><span></span><span class="ax"><i style="left:0">0</i><i style="left:25%">0,25 Zufall</i><i style="left:50%">0,5</i><i style="left:75%">0,75</i><i style="left:100%">1</i></span><span></span></div>
</div>
<div>
<div class="card">
<div class="cap">Indikator · Anteil Orientierungsflüge</div>
<table class="ind">
<tr><th></th><th>Modell</th><th>Labels</th></tr>
<tr><td>Stock A</td><td class="big">26 %</td><td class="lab">26 %</td></tr>
<tr><td>Stock B</td><td class="big">20 %</td><td class="lab">23 %</td></tr>
</table>
<div class="f1">F1 Orientierung auf Test: 0,58 (A und B)</div>
</div>
<div class="card">
<div class="cap">Wie viele Klassen? · F1 Orientierung, Val</div>
<div class="kr hd"><span></span><span></span><span style="text-align:right">F1</span><span style="text-align:right">Fehler Anteil</span></div>
<div class="kr"><span>2 Klassen</span><span class="bar"><i style="width:58.1%"></i></span><b>0,58</b><span class="pp">−9,5 PP</span></div>
<div class="kr"><span>3 Klassen</span><span class="bar"><i style="width:58.8%"></i></span><b>0,59</b><span class="pp">+2,7 PP</span></div>
<div class="kr best"><span>4 Klassen</span><span class="bar"><i style="width:68.2%"></i></span><b>0,68</b><span class="pp">+4,5 PP</span></div>
</div>
</div>
</div>

<div class="take"><b>Die Grenze sind die Labels:</b> wo sich alle Labelnden einig sind, liegt das Modell bei 0,80 und 0,91.</div>

<div class="fn">Balanced Accuracy<sup>1,2</sup>, Zufall = 0,25 · Test B: 95 %-Intervall, Cluster-Bootstrap über 21 Aufnahmen<sup>3</sup> · Test A: nur 4 Aufnahmen, Balken = Spanne ohne je eine Aufnahme · Regel: Start- und Endzone, Schwellen auf Train gewählt · F1 = harmonisches Mittel aus Precision und Recall<sup>2</sup> · Klassenvergleich: gleiches Setup mit 2/3/4 Klassen trainiert, Fehler Anteil = geschätzter minus wahrer Anteil Orientierungsflüge in Prozentpunkten · <sup>1</sup> Opitz (2024). <i>TACL</i> 12 · <sup>2</sup> Maier-Hein et al. (2024). Metrics Reloaded. <i>Nature Methods</i> 21, 195–212 · <sup>3</sup> Field, Welsh (2007). Bootstrapping clustered data. <i>J. R. Stat. Soc. B</i> 69(3), 369–390</div>

<!--
Antwort: ja, mit Grenze
→ Klassen: 2/3/4 auf Val, nachträglich; 4 am besten (F1 0,68), 2 unterschätzt Anteil
→ Stock B: 0,76 vs Regel 0,68
→ Stock A: kaum Unterschied
→ Indikator: Anteil fast richtig
→ einig: 0,80 / 0,91
→ Fehler = unklare Bahnen
-->
