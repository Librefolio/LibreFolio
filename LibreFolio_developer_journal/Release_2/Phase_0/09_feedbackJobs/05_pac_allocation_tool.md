# 05 — PAC Allocation Tool (feature grande)

**Complessità**: M–L · **Tipo**: la "feature-faro" del round (self-contained)
**Origine**: nota utente · **Studio di riferimento**: `Release_2/guida_allocazione_pac_multi_etf.md`

## Richiesta (dalla nota utente)

Un tool per aiutare nell'allocazione del PAC (Piano di Accumulo), usando lo studio di riferimento
pensato per Directa — che ha **vincolo di acquisto intero** (quote intere) e **allocazione in euro**.

Il tool:
- Prende in input vari parametri risultanti dalla decisione di allocazione PAC.
- Flag per attivare la **variante intera** (quote intere), il **metodo di inserimento**
  (numero quote oppure ammontare massimo in euro), ecc.
- Deve confluire in una **funzionalità backend esposta via API** + un **frontend** con cui
  l'utente interagisce.
- In seguito (fase successiva): lo stesso tool esportabile a un agente AI via **server MCP**,
  così che dopo l'analisi PAC possa far eseguire al backend — possibilmente in forma
  ottimizzata — i calcoli, riportando tutte le colonne e le informazioni, facendo poi decidere
  all'AI o all'utente.

## Note per chi la pianifica

- Leggere prima lo studio `guida_allocazione_pac_multi_etf.md` (vincolo intero Directa,
  allocazione in euro, esempi numerici).
- È una feature self-contained: nessuna dipendenza dai task in corso; va bene come "la cosa
  grossa" di un round, con piano dedicato in `Phase_0/<NN>/`.
- La fase MCP è un'estensione futura della stessa feature: progettare l'API del backend in
  modo che sia già pulita e documentabile (response_model, tipi espliciti) per non doverla
  riaprire quando arriverà il server MCP.
