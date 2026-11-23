// Chapters of the learning platform /lernen, in pipeline order.
export interface Chapter { slug: string; nr: number; title: string; short: string; part: string }

export const CHAPTERS: Chapter[] = [
  { slug: "daten", nr: 1, title: "Daten und Aufteilung", short: "Videos, Sequenzen, Train/Val/Test", part: "Grundlagen" },
  { slug: "labels", nr: 2, title: "Klassen und Labels", short: "4 Klassen, Mehrheit, Recheck", part: "Grundlagen" },
  { slug: "detektion", nr: 3, title: "Detektion (Chiron 2013)", short: "Hintergrundmodell, Bewegungsmasken", part: "Vom Video zur Bahn" },
  { slug: "tracking", nr: 4, title: "Tracking: Kalman + GNN", short: "Vorhersage, Zuordnung, Ungarische Methode", part: "Vom Video zur Bahn" },
  { slug: "linking", nr: 5, title: "Tracklet-Linking (Huang 2008)", short: "Bruchstücke zusammensetzen", part: "Vom Video zur Bahn" },
  { slug: "bahnen", nr: 6, title: "Flugbahnen und Merkmale", short: "Filter, Zonen, Bahnmerkmale", part: "Vom Video zur Bahn" },
  { slug: "eingabe", nr: 7, title: "Eingabe des Netzes", short: "7 Kanäle, Länge 128, Standardisierung", part: "Klassifikator" },
  { slug: "resnet", nr: 8, title: "ResNet (Fawaz 2019)", short: "Faltung, BatchNorm, Shortcut, Training", part: "Klassifikator" },
  { slug: "ensemble", nr: 9, title: "Ensemble Kombi", short: "5 Seeds mitteln, Auswahl auf Val", part: "Klassifikator" },
  { slug: "vergleich", nr: 10, title: "Vergleichsmodelle", short: "Regel, GB, InceptionTime, Video, Clustering …", part: "Klassifikator" },
  { slug: "vorfilter", nr: 11, title: "Vorfilter: Biene oder nicht", short: "YOLO26s, DINOv2, BioCLIP, Youden", part: "Klassifikator" },
  { slug: "bewertung", nr: 12, title: "Bewertung und Statistik", short: "BA, F1, Bootstrap, Wilson", part: "Ergebnis" },
  { slug: "ergebnis", nr: 13, title: "Ergebnisse und Grenzen", short: "Val, Test, was es bedeutet", part: "Ergebnis" },
];

export const chapter = (slug: string) => CHAPTERS.find((c) => c.slug === slug)!;
