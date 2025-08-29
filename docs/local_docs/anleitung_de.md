# Anleitung (DE): Modell einrichten, Daten geben, trainieren und sinnvolle Chat‑Antworten erhalten

Diese Anleitung beschreibt kompakt und Schritt für Schritt, wie Sie die App offline nutzen, um:
- Module auszuwählen,
- ein Modell zuzuordnen bzw. zu trainieren,
- eigene Daten einzuspeisen,
- die Readiness zu prüfen,
- im Chat sinnvolle, nicht gespiegelte Antworten zu erhalten (Anti‑Echo).

Voraussetzungen:
- Windows PowerShell, Python 3.10+, Node.js 18+.
- Dieses Repo lokal geklont; WordNet‑3.0 liegt bereits im Repo (offline).


## 1) Backend & Frontend starten

PowerShell (Terminal 1):
- python -m pip install fastapi uvicorn
- python -m uvicorn app.backend.main:app --reload --port 8000

PowerShell (Terminal 2):
- cd app\frontend
- npm install
- npm run dev
- Browser öffnen: http://localhost:5174

Hinweis: Nach Eintritt in die „AI Workspace“-Seite arbeitet die App offline (keine Netzaufrufe).


## 2) Site 1 — Module auswählen

- Gehen Sie in der UI auf „Site 1 — Module Selection“.
- Aktivieren Sie z. B. „chat-core“ (Chat) und optional „predictor-finance“.
- Speichern (Save oder Save & Continue), damit eine „pending workspace“ entsteht.


## 3) Site 2 — Modell auswählen & Ops

Ziel: Pro gewähltem Modul genau ein kompatibles Modell zuordnen.

Sie haben drei Wege (alle offline):
1. Neues Neural Network (NN) erstellen → anschließend daraus ein neues Modell erstellen.
2. Neues Modell aus bestehendem NN erstellen (NN wählen, Dataset/Hparam wählen → Modell entsteht).
3. Bestehendes Modell wählen (aus Registry).

Schnellstart (empfohlen):
- Nutzen Sie den Bootstrap‑Pfad (siehe README Quickstart) oder wählen Sie für „chat-core“ das Modell „chat_retrieval_1337“, sofern vorhanden.
- Achten Sie auf die Kompatibilität: capability/task/IO‑Schema/Resources müssen passen. Die UI filtert nicht passende Modelle automatisch aus.


## 4) Eigene Daten hinzufügen (Datensatz importieren)

Sie können eigene Chat‑Daten einspeisen, um das Lernen zu verbessern. Der Backend‑Endpunkt normalisiert die Daten in JSONL.

- Öffnen Sie Site 3 (AI Workspace) oder ein separates Tool (z. B. REST‑Client) und rufen Sie an:
  POST /api/datasets/ingest
  Payload‑Beispiel (Textzeilen):
  {
    "format": "text",
    "content": "Was ist ein Baum?\nErkläre den Begriff 'Algorithmus'"
  }

  Alternativ (JSONL):
  {
    "format": "jsonl",
    "content": "{\"prompt\":\"Was ist KI?\",\"response\":\"KI ist...\"}\n{\"prompt\":\"Definiere 'Graph'\",\"response\":\"Ein Graph ist...\"}"
  }

- Die Daten landen offline unter app\artifacts\datasets\uploads und werden in der Registry registriert.

Tipp: Für reproduzierbares Verhalten verwenden Sie feste Seeds (Standard 1337).


## 5) Training & Evaluation lokal ausführen

Nach dem Import von Daten können Sie Trainings‑/Evaluationsläufe starten. Je nach Modul stehen unterschiedliche Pipelines bereit.

Beispiel (Chat):
- POST /api/train mit Payload { "module_id": "chat-core", "seed": 1337 }
- POST /api/evaluate mit Payload { "module_id": "chat-core", "seed": 1337, "model_id": "chat_retrieval_1337" }

Die Artefakte und Metriken werden unter app\artifacts\chat bzw. app\artifacts\metrics\chat gespeichert. Alle Läufe sind deterministisch (Seed).

Fehlen Daten, fällt das System „graziös“ zurück (Retrieval‑only) und erklärt, was fehlt.


## 6) Readiness Check (Blocking Gate)

Vor dem Start des Offline‑Runtimes muss die Readiness grün sein:
- In der UI: Site 3 zeigt den Status oben an.
- Oder per API: GET /api/readiness

Wenn „not ready“, erhalten Sie klare Hinweise (human_message, hint, logs‑Pfad), z. B. fehlende Modelle oder Checksums. Beheben → erneut prüfen.


## 7) Chat benutzen — keine Spiegel‑Antworten

Sobald Readiness „ready“ ist:
- Gehen Sie in Site 3 (AI Workspace) → Chat Panel.
- Geben Sie Ihre Frage ein und senden Sie.

Warum die Antwort nicht gespiegelt wird:
- Der Backend‑Endpunkt POST /api/runtime/post nutzt ein WordNet‑basiertes Retrieval (Gloss + Synonyme) und erstellt eine **neue**, begründete Antwort (mit Provenienz, z. B. „data.noun“ Offset).
- Eine Anti‑Echo‑Logik verhindert, dass die Ausgabe dem Input (nach Normalisierung) exakt entspricht. Falls ein Echo droht, wird die Antwort angepasst (z. B. „Answer: …“ Präfix) oder über das LM/Guardrails modifiziert.
- Das Frontend rendert jetzt explizit die generierte Antwort (answer.guarded bzw. answer.raw), nicht mehr die verarbeitete Eingabe.

Zusätzlicher Lerneffekt:
- Das System zählt benutzte Lemmata (update_counts) und kann ein kleines lokales N‑Gram‑LM aus synthetischen Dialogen/Uploads aufbauen. So wird das Verhalten sukzessive besser, bleibt aber deterministisch.


## 8) Guardrails (Sicherheit & Kontrolle)

- GET /api/guardrails zeigt die aktuellen Regeln (max tokens, PII‑Regex etc.).
- POST /api/guardrails setzt neue Regeln. Die Guardrails werden auch auf die generierte Antwort angewandt und dokumentieren Aktionen (actions).
- Wenn Guardrails eingreifen, sehen Sie dies im Chat (Actions‑Liste) und in lokalen Logs.


## 9) Troubleshooting (kurz)

- Readiness rot/orange: In Site 3 auf „Retry Readiness Check“ klicken oder GET /api/readiness prüfen; Hinweise befolgen.
- „Antwort klingt leer/zu kurz“: Stellen Sie sicher, dass die WordNet‑Indizes unter app\artifacts\indices vorhanden sind (werden beim ersten Run erstellt) und dass Sie nach dem Import eigener Daten ein kurzes Training + Evaluation gefahren haben.
- „Echo trotz allem?“: Prüfen Sie, dass die Frontend‑Version answer.guarded rendert (dies ist in diesem Repo bereits gefixt) und dass Guardrails aktiv sind. Außerdem sollte die Anti‑Echo‑Aktion im Backend in der Antwort „actions“ auftauchen, wenn sie griff.
- Logs & Artefakte: app\artifacts\logs und app\artifacts\metrics; Registry unter app\registry.


## 10) Kurzablauf (Cheat‑Sheet)

1) Backend & Frontend starten (siehe Abschnitt 1)
2) Site 1: Module wählen → speichern
3) Site 2: Pro Modul 1 kompatibles Modell zuordnen (oder trainieren)
4) Eigene Daten per POST /api/datasets/ingest einspeisen
5) Training/Evaluation starten (POST /api/train, /api/evaluate mit seed)
6) Readiness grün prüfen (GET /api/readiness)
7) Site 3 Chat nutzen — Antworten stammen aus WordNet‑Retrieval (+ optional LM), nicht als Echo
8) Guardrails nach Bedarf anpassen

Stand: 2025‑08‑29 17:02 (lokal)