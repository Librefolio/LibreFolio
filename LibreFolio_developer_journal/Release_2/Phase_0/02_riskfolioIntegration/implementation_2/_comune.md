# Vincoli comuni a tutte le superfici della fase 2

> Incluso per riferimento in ogni briefing S1–S5. **Il coordinatore è l'unico che scrive qui.**

## Corsie

| | mandato | porta | cartella dati |
|---|---|---|---|
| S1 | L1 | `6153` | `/tmp/librefolio-r2-s1` |
| S2 | L2 | `6154` | `/tmp/librefolio-r2-s2` |
| S3 | L3 | `6155` | `/tmp/librefolio-r2-s3` |
| S4 | L4 | `6156` | `/tmp/librefolio-r2-s4` |
| S5 | Asset Global | `6157` | `/tmp/librefolio-r2-s5` |

⚠️ **Il coordinatore usa `6150` con la cartella dati predefinita.** Nessuno la tocchi.

## Scrittori unici delle superfici condivise

| superficie | chi scrive | gli altri |
|---|---|---|
| `levels/RiskLevelsPanel.svelte` | **S1** | chiedono a S1 |
| `levels/levelHelpers.ts` | **S1** | chiedono a S1 |
| `i18n/*.json` | ciascuno **solo** nel proprio namespace | il coordinatore verifica l'unione |
| `scripts/test_runner/*` | **T3** | nessun altro |
| `frontend/e2e/portfolio/*.spec.ts` | **T3** | nessun altro |
| `implementation_2/PRIMITIVE.md` | **F2** (chiuso) | lo leggono tutti |

## I quattro vincoli misurati

**① `api sync` dopo ogni aggiornamento di baseline**, forma canonica:
```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```
`generated.ts` **e** `openapi.json` sono entrambi in `.gitignore`: non viaggiano col merge.

**② Niente `toFixed` nuovi.** Esiste `utils/core/formatPercent`. I 16 (o 26, secondo il perimetro)
esistenti sono di **T4**, non tuoi.

**③ I `DocsLink` sono rotti in due modi** — percorso inesistente **e** forma `.md#ancora` invece
che directory. Ripararli è di **T2**. **Non aggiungerne di nuovi sbagliati.**

**④ Gli avvisi in inglese sono 17 messaggi in prosa del backend**, non traduzioni mancanti.
Sono di **T1**. Non incorporarli come testo definitivo.

## Definizione di finito

**Il coordinatore guarda la tua superficie nel browser, in italiano, prima che tu chiuda.**
Non «i test passano».

## Processo

- **Analisi prima del codice.** Nessuna riga prima della revisione.
- **Non fidarti del briefing.** Nella fase 1 cinque numeri del coordinatore o di F2 sono
  risultati sbagliati, ciascuno trovato dall'altro. Una divergenza segnalata è un'informazione.
- **Lo stage è l'ultimo atto, e lo dichiari tu** con `FROZEN`. Nella fase 1 la finestra fra
  «stagio» e «l'agente finisce» si è riaperta **sei volte**.
- **Il controllo che non mente** è dimensionale: `git show :file | wc -l` contro `wc -l file`.
  Non cerca una stringa, quindi non può tacere su un'altra.
- **Aggiorna il piano vivo dopo ogni passo**, in `implementation_2/progress/SN-esecuzione.md`,
  e **nominalo a ogni handoff**: nel round 1 gli otto `*-esecuzione.md` sono stati gli unici file
  a esistere solo sul disco, perché il piano si aggiorna *dopo* il passo e nessun checkpoint
  automatico lo contiene mai.
