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

## 🔧 GitHub Pages aktivieren (einmalig – 1 Klick)

GitHub erlaubt aus Sicherheitsgründen nicht, Pages automatisch per Skript zu
aktivieren. Du musst es **einmal** selbst einschalten:

**Repo → Settings → Pages → „Build and deployment" → Source: „Deploy from a
branch" → Branch: `main`, Ordner: `/docs` → Save.**

Nach ~1 Minute ist die App live unter:
`https://dlshad20k.github.io/Aura/`

Danach wird bei jedem Push auf `main` automatisch die neue Version ausgeliefert –
kein weiterer Klick nötig.

## ℹ️ Wichtig zu „Claude / KI"

Ein gehostetes Web-App kann **nicht** das **Claude-Pro-Abo** nutzen – das geht nur
im Chat auf claude.ai. Für KI in einer App bräuchte man einen kostenpflichtigen
**API-Key**. Deshalb nutzt diese App stattdessen eine **kostenlose On-Device-KI**
(COCO-SSD / TensorFlow.js), die direkt im Browser deines iPhones läuft – dadurch
ist alles **gratis und privat** (kein Bild verlässt dein Handy).

## 🧠 Zwei Modi

**🎯 Fokus** – Die App zielt auf **eine Sache in der Bildmitte** (Fadenkreuz),
stabilisiert sie über mehrere Frames (kein Flackern) und zeigt genau *dieses eine*
Objekt mit Kategorie + Preis-Schätzung. Sie versucht zusätzlich, das Objekt genauer
zu benennen (1000+ Kategorien).

**🏷️ Barcode** – Halte einen **Produkt-Barcode** ins Fadenkreuz. Die App liest ihn
(EAN/UPC/QR) und holt den **echten Markennamen** aus der freien Open-Food-Facts-
Datenbank + einen Link zu **echten Live-Preisen**. Das ist der zuverlässigste
kostenlose Weg zu echten Marken und Preisen.

## ⚠️ Was kostenlos NICHT geht
„Kamera auf irgendein Ding halten → Marke + exakter Preis erkennen" (wie Google Lens)
braucht eine **kostenpflichtige Cloud-Vision-API**. Kostenlose On-Device-KI erkennt
nur **Kategorien** (z. B. „Schuh", „Flasche"), keine Logos/Marken. Für echte Marken
+ Preise nutze den **Barcode-Modus**.

## 🛠 Technik
- `docs/index.html` – Oberfläche
- `docs/app.js` – Kamera + Erkennungs-Schleife
- `docs/labels.js` – Objekt-Datenbank (Namen, Emojis, Preise)
- `docs/sw.js` + `manifest.json` – PWA (installierbar / offline-Shell)
