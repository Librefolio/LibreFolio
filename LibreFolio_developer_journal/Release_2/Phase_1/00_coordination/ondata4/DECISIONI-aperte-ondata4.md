# Ondata 4 — le decisioni che aspettano te (22/10/2026, pomeriggio)

Rispondi pure per numero. Per ognuna: la questione con un esempio, le opzioni, il consiglio. Il backup è deciso (§10 di
`BACKUP-decisioni-20261022.md`), qui non c'è.

---

## 1. W · Q-N78-1k — una coppia di rettifiche collegate fra due tuoi broker: P o M?

**La situazione.** Hai 10 azioni in Directa (A) comprate a 50, oggi valgono 80. Le sposti in Fineco (B) non con un
TRANSFER ma con **due rettifiche collegate**: −10 in A, +10 in B. (Dal form non si crea più: il form la trasforma in
TRANSFER. Arriva da dati vecchi o dall'API.) Oggi, con la regola «una rettifica in uscita non ha valore», A perde tutto il
costo e il totale mostra una perdita finta.

**P — «la gamba che esce va al PMC»** (era la tua idea): A cede le azioni al suo costo medio, B le riceve con il costo
scritto sulla sua gamba. **M — «la coppia è uno spostamento, come un TRANSFER»**: le azioni viaggiano con il loro costo
e la loro storia, come in un TRANSFER.

Nell'esempio semplice (un lotto, stesso giorno, gamba di B a costo 50) danno lo stesso totale:

| | Oggi | P | M |
|---|---|---|---|
| Tutti i broker: P&L | −200 | +300 | +300 |
| Solo A: P&L | −500 | 0 | +300 |
| Solo A: rendimento del giorno | −100 % | **−37,5 %** (finto) | 0 % |
| Solo B: P&L | +300 | +300 | 0 |

**Ma MF ha trovato tre casi reali in cui P sbaglia il totale** (M li regge tutti):
- **la gamba di B senza costo, o con un costo diverso** (succede: l'app non lo controlla per le rettifiche). Esempio
  senza costo: con tutti i broker il P&L diventa +800 invece di +300 (+500 inventati);
- **spostamento parziale da più lotti a prezzi diversi** (5 a 40 e 5 a 60, ne sposti 5): la Dashboard dice «neutro», la
  vista dei lotti no (−50 dal nulla);
- **le due gambe in giorni diversi** (esce il 1°, entra il 5): per quattro giorni il totale non è neutro.

**Consiglio: M** (anche MF). Costa un po' di più (otto punti del codice invece di cinque) ma il totale torna sempre.
Con P servirebbe in più che l'Auto cost della gamba di B prenda il costo del partner, più un avviso sui dati vecchi.

Tre conferme minori di W (consiglio sì a tutte):
- **1b.** Le coppie di rettifiche collegate restano creabili dall'API.
- **1c.** Nell'import, le impostazioni personali di un plugin BRIM sono quelle dell'utente che importa.
- **1d.** Il plugin BRIM «di prova» per le impostazioni vive solo dentro i test.

---

## 2. H · tre domande sulla parte finale (R5, docs dell'API)

**2a (Q-A). Il visore PDF quando il suo motore non risponde.** Oggi, se la copia locale del motore non risponde, l'anteprima
mostra il **visore del browser** in un riquadro (Chrome e Firefox ne hanno uno), con il messaggio che esiste già nelle 4
lingue. Alternativa: un messaggio nuovo «anteprima non disponibile», da tradurre. **Consiglio: tenere il visore del
browser** (il PDF lo vedi comunque).

**2b (Q-C). Da dove prendiamo Swagger e ReDoc** (le pagine `/api/v1/docs` e `/api/v1/redoc`, che oggi scaricano librerie da
un CDN senza versione fissa): (a) **due pacchetti npm a versione fissata** (`swagger-ui-dist`, `redoc`), copiati
nell'immagine dalla build e aggiornati con il lock come tutto il resto — l'installazione la faccio io; (b) i file messi a
mano nel repository, con un test sull'hash. **Consiglio: (a).**

**2c (Q-D). Nel profilo managed (il cloud) spegniamo anche `openapi.json`**, la «mappa» completa dell'API, oltre alle due
pagine? Il frontend non la usa mentre gira (serve solo agli sviluppatori per generare il client). **Consiglio: sì**: non
regaliamo la mappa dell'API di un'istanza del cloud; il self-hosted la tiene.

---

## 3. Y · Q-Y41-1 — confronto «asset su cambio» nella vista assoluta

Su una scheda dei cambi in **vista assoluta**, un asset da 340 USD disegnato sopra un tasso da 1,08 schiaccia la linea del
tasso (le due scale sono lontanissime). (a) **lasciarlo così**, come fa già il dettaglio dei cambi: nella vista % il
problema non c'è; (b) convertire l'asset nella valuta della coppia (qualche richiesta in più). **Consiglio: (a)**; Y è
partito così, (b) si aggiunge dopo se serve.

---

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

---

## 5. Già deciso da me (te lo segnalo, puoi cambiarlo)

- **D, le dipendenze**: strada «1b» — le date restano UTC come oggi, si dichiara solo alla libreria come sono salvate (un
  file, nessun cambio di dati o numeri). Il passaggio a date con l'etichetta UTC esplicita va nel backlog per la 1.4.
- **E**: i testi che hai scelto erano già nel codice; il dubbio «nell'email / dell'email» l'ho chiuso tenendo il testo
  attuale.
- **J**: R1 rimandata dopo la 1.3 (dipende dalle formule veloci di X, che hai lasciato fuori).
- **A**: per l'E2E di N69c uno «stub» del server invece di un giro completo (scelta di test, invisibile all'utente).
