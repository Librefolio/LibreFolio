#!/usr/bin/env python3
"""Generatore del contratto K7 — gli slug di `risk-metrics/` per la prop `path` di DocsLink.

PERCHE' QUESTO FILE ESISTE NEL REPOSITORY E NON IN /tmp
-------------------------------------------------------
K7 e' nato come tabella scritta a mano ed e' andato fuori sincrono con la sua sorgente
due volte: una sul numero di righe (14 dichiarate contro 18 reali), una sull'ordine dei
livelli. La diagnosi registrata dal coordinatore:

    Il difetto non e' di nessuno dei due: il contratto e la sua sorgente si sono mossi
    in momenti diversi. Il generatore va rieseguito a ogni cambio di slug, altrimenti
    K7 torna a essere una trascrizione — cioe' il problema che esiste per risolvere.

Uno strumento che genera un contratto e vive in /tmp e' un contratto che torna a essere
una trascrizione al primo riavvio della macchina. Quindi sta qui, versionato.

COME SI USA
-----------
    PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build
    PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python \
        LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/\
implementation/progress/I-k7-genera.py

Va eseguito dalla radice del worktree e DOPO un build: legge `mkdocs_src/site/`, cioe'
le pagine COSTRUITE, non i sorgenti. E' deliberato — il contratto deve descrivere cio'
che l'utente riceve, non cio' che sta in `docs/`. Le due cose divergono: una pagina
senza voce di nav esiste come file e non come URL.

ATTENZIONE: non eseguirlo mentre un agente delegato sta scrivendo in mkdocs_src/.
Misurare durante una scrittura ha gia' prodotto una ritrattazione in questa campagna.

IL CONTROLLO CHE CONTA E' NEI DUE SENSI
---------------------------------------
Non basta che ogni riga del contratto abbia una pagina: serve anche che ogni pagina
costruita abbia una riga. Un contratto che dimentica una pagina non fallisce a
compilazione — fallisce quando E, F o H cercano uno slug che non c'e' e ne inventano uno.
Percio' `unmapped` non ha eccezioni: se compare qualcosa, il contratto e' incompleto.

Aggiornare LEVELS quando si aggiunge una pagina; il controllo nei due sensi segnala
l'omissione al primo passaggio.
"""

from pathlib import Path

SITE = Path("mkdocs_src/site/financial-theory/technical-analysis/risk-metrics")
PREFIX = "financial-theory/technical-analysis/risk-metrics"

# Livelli presi da 03-mappa-livelli-pagine.md:29-32 (sono DOMANDE, non difficolta')
LEVELS = [
    ("L1", "Quanto può fare male?", [
        ("Max Drawdown", "max-drawdown"),
        ("Current Drawdown", "current-drawdown"),
        ("Drawdown at Risk", "drawdown-at-risk"),
        ("Conditional Drawdown at Risk", "conditional-drawdown-at-risk"),
        ("Ulcer Index", "ulcer-index"),
        ("Value at Risk", "value-at-risk"),
        ("Conditional VaR", "conditional-value-at-risk"),
        ("Worst Realization", "worst-realization"),
    ]),
    ("L2", "Sono diversificato?", [
        ("Correlation", "correlation"),
        ("Risk Contribution", "risk-contribution"),
        ("Concentration (NEA + DR)", "concentration"),
    ]),
    ("L3", "Sono pagato per il rischio?", [
        ("Volatility", "volatility"),
        ("Sharpe Ratio", "sharpe-ratio"),
        ("Sortino Ratio", "sortino-ratio"),
        ("Beta & Active Return", "beta-active-return"),
        ("Benchmark Selection", "benchmark-selection"),
    ]),
    ("L4", "Cosa succede se…?", [
        ("Historical Replay", "historical-replay"),
        ("Hypothetical Shock", "hypothetical-shock"),
        ("Simulation Modes", "simulation-modes"),
    ]),
    ("—", "Metodo (trasversale)", [
        ("Observed Annualization", "observed-annualization"),
        ("Data Quality", "data-quality"),
    ]),
]

# L'hub. Non e' una metrica, ma e' la pagina a cui ogni livello rimanda: senza una
# riga qui resta l'unica senza `path` sanzionato. In `site/` e' la cartella stessa,
# quindi lo slug e' vuoto e il path termina su risk-metrics/.
HUB = ("Risk Metrics — Overview", "")

on_disk = {d.name for d in SITE.iterdir() if d.is_dir() and (d / "index.html").exists()}
on_disk.add("index")                # l'hub esiste come index.html della cartella
mapped = {s for _, _, rows in LEVELS for _, s in rows}
mapped.add("index")                 # ...e ora ha la sua riga nel contratto

missing = mapped - on_disk          # slug nel contratto senza pagina
unmapped = on_disk - mapped         # pagina senza riga nel contratto — nessuna eccezione

print("## Slug (generati da site/, nessuna trascrizione a mano)\n")
print("| Livello | Domanda | Metrica | `path` |")
print("|---|---|---|---|")
print(f"| — | Hub | {HUB[0]} | `{PREFIX}/` |")
for code, question, rows in LEVELS:
    for i, (label, slug) in enumerate(rows):
        lv = f"**{code}**" if i == 0 else ""
        q = question if i == 0 else ""
        print(f"| {lv} | {q} | {label} | `{PREFIX}/{slug}/` |")
print(f"\n**{len(mapped)} righe** ({len(mapped) - 1} metriche + hub). Durata *e* recupero del drawdown -> `{PREFIX}/max-drawdown/#recovery-time`\n")
print("### Controllo nei due sensi")
print(f"- slug nel contratto senza pagina costruita: **{sorted(missing) or 'nessuno'}**")
print(f"- pagine costruite senza riga nel contratto: **{sorted(unmapped) or 'nessuna'}**")
print(f"- pagine costruite su disco: **{len(on_disk)}** | righe nel contratto: **{len(mapped)}**")
