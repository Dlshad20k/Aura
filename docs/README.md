# 📷 Aura Vision – Live Objekt- & Preis-Scanner

Eine **iPhone Web-App**, die durch die Kamera **live Objekte erkennt** und dir
**sofort einen Preis** anzeigt. Läuft **komplett auf dem Gerät** (On-Device-KI mit
TensorFlow.js), **kostenlos**, **ohne Anmeldung**, **ohne API-Key**, **ohne Server**.

## 🚀 So startest du sie

1. Öffne die App-URL in **Safari** auf dem iPhone (URL siehe unten).
2. Tippe auf **„📷 Kamera starten"** und erlaube den Kamerazugriff.
3. Richte die Kamera auf Dinge – Objekte werden live mit Namen + Preis markiert.
4. Tippe auf **„Live-Preise ›"**, um echte aktuelle Preise (Google Shopping) zu sehen.

### Als App aufs Home-Bildschirm (empfohlen)
Safari → Teilen-Symbol → **„Zum Home-Bildschirm"**. Dann startet sie wie eine
echte App im Vollbild.

## 🔧 GitHub Pages aktivieren (einmalig)

Die App wird automatisch veröffentlicht. Falls die URL noch nicht geht:

**Variante A – automatisch (empfohlen):**
Repo → **Settings → Pages → Build and deployment → Source: „GitHub Actions"**.
Der Workflow `.github/workflows/pages.yml` veröffentlicht dann bei jedem Push.

**Variante B – ohne Actions:**
Repo → **Settings → Pages → Source: „Deploy from a branch"** →
Branch `claude/iphone-camera-recognition-6oj1qa`, Ordner **`/docs`** → Save.

Die URL lautet danach in etwa:
`https://<dein-github-name>.github.io/aura/`

## ℹ️ Wichtig zu „Claude / KI"

Ein gehostetes Web-App kann **nicht** das **Claude-Pro-Abo** nutzen – das geht nur
im Chat auf claude.ai. Für KI in einer App bräuchte man einen kostenpflichtigen
**API-Key**. Deshalb nutzt diese App stattdessen eine **kostenlose On-Device-KI**
(COCO-SSD / TensorFlow.js), die direkt im Browser deines iPhones läuft – dadurch
ist alles **gratis und privat** (kein Bild verlässt dein Handy).

## 🧠 Was wird erkannt?
80 gängige Objektklassen (Handy, Laptop, Flasche, Auto, Stuhl, Obst, Tiere, u. v. m.)
in Echtzeit. Für jedes Objekt gibt es einen Preis-Schätzwert und einen Link zu
echten Live-Preisen.

## 🛠 Technik
- `docs/index.html` – Oberfläche
- `docs/app.js` – Kamera + Erkennungs-Schleife
- `docs/labels.js` – Objekt-Datenbank (Namen, Emojis, Preise)
- `docs/sw.js` + `manifest.json` – PWA (installierbar / offline-Shell)
