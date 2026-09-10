# PAC P1 - ASCII PILOT-01

**Stato:** P1-U1 aperto. Solo proposta/ASCII; nessuna UI eseguibile nel worktree.

L'approvazione di questo file sbloccherebbe solo la vista manuale P1. Non approva BC01,
solver, copie dominio, Broker, full-v4 o ordini.

## 1. Desktop - input manuale

```text
+--------------------------------------------------------------------+
| Tool > PAC - analisi situazione iniziale                           |
| P1 manuale: nessun Asset/Broker creato nel DB                       |
| Valuta report [EUR v]   Data [2026-09-08 / facoltativa]             |
|--------------------------------------------------------------------|
| Riga     | Q iniziale | Prezzo | Valuta / Q | Target               |
| Alfa / X | [10.125  ] | [10  ] | [EUR] /[1] | [50]%                |
| Alfa / Y | [0       ] | [10  ] | [EUR] /[1] | [50]%                |
| X: intere passo [1]       Y: frazioni passo [0.001]                 |
| [Nuovo asset locale] [Stesso asset, altro contesto]                 |
|--------------------------------------------------------------------|
| CASSA ESISTENTE                | NUOVI CONTRIBUTI                   |
| EUR [0.005]  USD [10]          | EUR [5]                            |
| [+ valuta] [Nessuna cassa]     | [+ valuta] [Nessun contributo]    |
|--------------------------------------------------------------------|
| CAMBI DI VALORIZZAZIONE, NON CONVERSIONI                            |
| 1 USD = [0.9] EUR   data [2026-09-08 / facoltativa]                 |
|--------------------------------------------------------------------|
| Revisione 7 [Controlla situazione] [Interrompi attesa]              |
| Ordini, soglie e ottimizzazione non inclusi in P1.                  |
+--------------------------------------------------------------------+
```

Regole:

- testo Decimal raw preservato durante editing;
- quote basis solo 1/100;
- nessun calcolo economico frontend;
- array cash/contributi vuoto solo tramite azione esplicita;
- risposta vecchia non sovrascrive una revisione nuova;
- label non determina identita riga/strumento.

## 2. Desktop - risultato

```text
+--------------------------------------------------------------------+
| READY - situazione iniziale valutabile - revisione 7                |
| Non significa target raggiunto, ordini fattibili o ottimo.          |
| [Vista esatta] [Vista formattata]                                   |
|--------------------------------------------------------------------|
| Investito iniziale: 101.25 EUR                                      |
| Cassa esistente: 9.005 EUR   Contributi: 5 EUR                      |
| Cassa + contributi: 14.005 EUR                                      |
| Nativo: EUR 0.005 + EUR 5; USD 10 + USD 0                           |
| Nessuna cassa USD convertita o trasferita.                          |
|--------------------------------------------------------------------|
| Riga     | Q0 esatta | Valore EUR | Peso | Target | Gap pp          |
| Alfa / X | 10.125    | 101.25     | 100% | 50%    | +50            |
| Alfa / Y | 0         | 0          | 0%   | 50%    | -50            |
|--------------------------------------------------------------------|
| Dinf: 50 pp               D2: 5000 pp^2                             |
| Info: Q0 fuori dal passo buy; inventario non arrotondato.           |
| [Rapporti esatti] [Input normalizzato] [Date e unita]               |
+--------------------------------------------------------------------+
```

Vista formattata usa convenzioni UI esistenti. Vista esatta mostra stringhe backend,
senza conversione `Number`. Percentuali arrivano gia in unita percentuale. `pp` e
`pp^2` restano espliciti.

## 3. Stati richiesti

```text
NEEDS INPUT                         INVALID
+-------------------------------+  +-------------------------------+
| FX USD/EUR mancante           |  | Prezzo "1e3" non valido      |
| Casse native ancora visibili  |  | Testo preservato             |
| Totale report indisponibile   |  | Non diventa 1000 o 13        |
+-------------------------------+  +-------------------------------+

READY, INVESTITO ZERO              BUSY / STALE
+-------------------------------+  +-------------------------------+
| Investito 0 disponibile       |  | Richiesta revisione 7        |
| Pesi/score non definiti       |  | Bozza ora revisione 8        |
| Nessun no-op/ottimo           |  | Risposta 7 ignorata          |
+-------------------------------+  +-------------------------------+

UNSUPPORTED                        PLATFORM ERROR
+-------------------------------+  +-------------------------------+
| Quote basis 3 fuori P1        |  | Timeout/worker/codec         |
| Ammesse 1 e 100               |  | Analisi non completata       |
| Non significa infeasible      |  | Draft conservato             |
+-------------------------------+  +-------------------------------+
```

Missing row FX blocca denominatore, pesi e score completi. Non si rinormalizzano le
righe note. Errori platform non diventano issue finanziarie.

## 4. Mobile

```text
+----------------------------------+
| [Menu] PAC - stato iniziale      |
| Report [EUR] Data [facoltativa]  |
|----------------------------------|
| Alfa / X                         |
| Q0 [10.125] Prezzo [10] [EUR]    |
| Q base [1] Target [50]%          |
| Buy intere, passo [1]            |
|----------------------------------|
| Alfa / Y                         |
| Q0 [0] Prezzo [10] [EUR]         |
| Target [50]% Frazioni [0.001]    |
|----------------------------------|
| Cash EUR[0.005] USD[10]          |
| Contributi EUR[5]                |
| 1 USD = [0.9] EUR                |
| [Controlla situazione]           |
|----------------------------------|
| READY r7 [Esatto/Formattato]     |
| Investito 101.25 EUR             |
| Cash + contributi 14.005 EUR     |
| X: 100% / 50% / +50 pp           |
| Y:   0% / 50% / -50 pp           |
| Dinf 50 pp; D2 5000 pp^2         |
| Nessun ordine/fattibilita        |
+----------------------------------+
```

## 5. Guardie UI future

- `data-testid` per selettori; mai testo tradotto o classi.
- `aria-busy`, revisione richiesta/risultato e stato visibili.
- Nessun valore personale in attributi, log o telemetria.
- Issue index risolta solo contro la stessa risposta/revisione.
- Chart svuotato su no-data/stale; nessun dato precedente residuo.
- Copie future separate: iniziale, prezzi, distribuzione corrente.
- Ogni copia applica preview atomica; nessun binding live.

## 6. Review dev futura

Il runbook operativo nasce solo quando la UI esiste. Dovra partire dalla sidebar Tool
in ambiente, ruolo e fixture dichiarati, usando dati sintetici. Scenari minimi:

1. manuale ready;
2. investito zero;
3. FX mancante;
4. numero invalido;
5. dominio unsupported;
6. risposta stale;
7. errore platform;
8. desktop/mobile/privacy/accessibilita.

Test verdi non sostituiscono il feedback dev. Nessuna istruzione di questo file implica
che oggi esista una pagina PAC navigabile.
