# Backup del cloud — lo schema e i punti d'attacco (21-22/10/2026)

Riassunto visivo di quanto discusso. Proposta, non ancora decisione. Le difese citate sono quelle lette nel codice di
`dev_release2` il 22/10; dove non ho verificato lo dico.

## 1. Ogni notte: chi fa cosa, chi ha quale chiave

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

## 2. Il ripristino: parte quando qualcuno sveglia l'istanza

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

## 3. Chi entra dove, cosa ottiene, cosa deve fare per entrarci

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

### 3.1 L'istanza di Mario

**Cosa ottiene chi entra:** i dati di Mario di oggi, in chiaro. Le chiavi di Mario (sessione, chiave d'istanza: i
segreti dei plugin). Il lucchetto aperto, che non serve a niente. **Nessuna copia** passata, né sua né di altri.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

| Strada | Cosa deve fare l'attaccante | Cosa lo ferma oggi | Quanto è probabile |
|---|---|---|---|
| **a. Le credenziali di Mario** (phishing, password riusata, PC di Mario infetto) | fare il login come Mario | il limite ai tentativi (429, F15); cookie HttpOnly + SameSite; **manca il secondo fattore** | **la più probabile**. Ma ottiene solo Mario, e Mario sarebbe nei guai comunque |
| **b. Un bug nell'app, da internet** (porta 6040 via proxy) | trovare un difetto che salta il login o esegue codice | pydantic valida la **forma** di ogni chiamata; il login è richiesto quasi ovunque; limiti alle dimensioni degli upload. Pydantic **non** protegge dai bug di logica (un controllo di permesso dimenticato) né dai **parser di file**: 29 parser dei report dei broker, immagini, zip di ripristino, YAML degli scenari (usa un SafeLoader, verificato). Quelli leggono file scelti dall'utente **dopo** il login | media-bassa: serve un bug nostro + di solito un login |
| **c. Il browser di Mario** (script iniettato, XSS) | mettere uno script in una pagina che Mario apre (es. nel nome di un asset) | `frame-ancestors` applicato; `script-src` oggi è **solo in modalità rapporto** (H-52), nella 1.3 va applicato; nessun inline script nel build. Con la CSP applicata lo script non parte; se partisse, il cookie HttpOnly non si ruba ma lo script agirebbe **come Mario** finché la pagina è aperta | bassa con la CSP applicata; sempre limitata a Mario |
| **d. Le rotte del pannello** | rubare il token di backup (L1) o falsificare un biglietto (L2, serve la chiave Ed25519 del coordinatore) | 20 rifiuti in 10 minuti per IP; con L3 lo zip scaricato è illeggibile. **Attenzione**: la nuova **rotta di ripristino** accetta uno zip e **sostituisce i dati**: deve accettare solo biglietti L2 di scopo `backup:restore`, mai il token L1 | bassa; con L2 serve il coordinatore |
| **e. Una dipendenza avvelenata** (PyPI, npm, immagine base) | far entrare codice malevolo in una libreria che usiamo | lockfile e immagine fissati per digest; nessuna scansione automatica *(non verificato)* | bassa ma **è l'unica strada che apre tutte le istanze insieme**, perché l'immagine è la stessa per tutti |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

### 3.2 Un token del pannello rubato (L1)

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

**La lista corta, in ordine di probabilità:**
1. il PC o l'email di Mario → solo Mario;
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
3. una dipendenza avvelenata → tutte le istanze insieme;
4. un bug in un parser di file dopo il login → quell'istanza;
5. XSS senza CSP applicata → quell'utente;
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
7. rompere la cifratura → in pratica zero.

**Cosa ne segue, concreto:** CSP applicata nella 1.3 (non solo rapporto); rotta di ripristino solo con biglietto L2
di scopo `backup:restore`; secondo fattore per gli admin delle istanze prima del lancio (oggi manca); scansione delle
dipendenze.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
