# `kickoff/` — i prompt di avvio delle sessioni

> **Documento del coordinatore.** Nessun mandato lo legge: contiene ciò che il
> coordinatore *dice* a un mandato per farlo nascere.

Il contratto `release-coordinator` chiede che ogni prompt di avvio sia **autonomo**:
un agente appena creato non ha la nostra conversazione, non sa chi siamo, non sa da
quale commit è nato e non sa cosa gli è vietato. Se una di queste cose manca, la
ricostruisce da sé — e la ricostruisce sbagliata.

---

## 0. Il cancello che precede tutto

> ## 🔑 Nessuna sessione si crea prima che la baseline esista **come commit**.
>
> Un worktree eredita **commit**, non file di lavoro. Creare una sessione mentre i
> mandati sono ancora in staging la farebbe nascere **senza le proprie istruzioni**.

Sequenza, e non è negoziabile:

1. il developer committa;
2. il coordinatore legge lo SHA: `git rev-parse HEAD`;
3. lo SHA sostituisce `<BASELINE>` qui sotto;
4. **solo allora** si creano le sessioni.

Conseguenza utile: con `base_branch: e-alfy-risk-management-replan` **non serve alcun
merge** verso i figli. Il merge servirebbe solo committando *dopo* la creazione — che è
precisamente lo scenario da evitare, perché costerebbe undici merge invece di zero.

---

## 1. I parametri di `create_session`

Identici per tutti tranne le ultime due righe.

```text
workspace_type           worktree
base_branch              e-alfy-risk-management-replan
coordinate_with_creator  true
notify_on_idle           always
kickoff.agent            coordinated-workstream
kickoff.mode             plan
kickoff.context_tier     default          ← finestra ridotta, per preservare le capacità
────────────────────────────────────────
name                     "<L> - <titolo>"  ← lettera stabile + " - ", per tutta la vita del flusso
kickoff.prompt           <preambolo comune> + <delta del mandato>
```

⚠️ `context_tier: default` è una **scelta esplicita del developer**, non un'omissione:
finestra ridotta ai figli per preservarne le capacità, finestra estesa al coordinatore
per preservarne la memoria.

---

## 2. Il preambolo comune

Uguale per tutti e undici. `<L>`, `<TITOLO>`, `<FILE>`, `<PORTA>`, `<DIR>` si
sostituiscono dalla tabella §3.

```markdown
Sei il mandato <L> — <TITOLO> — della ripianificazione del sottosistema Risk Analysis
di LibreFolio.

## Chi ti ha creato
Il coordinatore della campagna, che gira sul branch `e-alfy-risk-management-replan`
nel worktree `e-alfy-ideal-eureka`. Riferisci a lui, non al developer direttamente.

## Da dove nasci
Branch base: `e-alfy-risk-management-replan`
Baseline attesa: `<BASELINE>`

⚠️ **Prima cosa da fare**: `git rev-parse HEAD`. Se non coincide con la baseline
attesa, **fermati e riportalo**. Non continuare l'analisi su una base diversa da
quella su cui il piano è stato costruito.

## Il tuo mandato
`LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/<FILE>`

È un **brief in sola lettura**: non spuntarci sopra i passi, non modificarlo. Contiene
le tue istruzioni ed è l'unica copia che ne hai. Se deve cambiare, lo cambia il
coordinatore.

Il tuo piano vivo è un file **nuovo** che crei tu:
`.../implementation/progress/<L>-esecuzione.md` — convenzioni in `progress/README.md`.
Lo aggiorni **dopo ogni passo**, non alla fine.

## Cosa leggere prima di toccare qualunque cosa
1. `.github/copilot-instructions.md`
2. Il tuo mandato, per intero, compresi i link che contiene
3. `.../implementation/README.md` — lane, proprietà dei file, contratti, regole comuni
4. I documenti da `00` a `07` che il tuo mandato ti indica, nell'ordine che ti indica
5. `wiki-search` sui domini con storia che il tuo mandato nomina

## La tua lane
porta `<PORTA>` · data dir `<DIR>`

Forma canonica, senza eccezioni:
    PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
      pipenv run python dev.py test --test-port <PORTA> --data-dir <DIR> <CAT> <AZIONE>

Mai `./dev.py` nudo. Mai `6040`, `6041`, `6042`. Mai la banda `6150`-`6199`, che è di
un altro worktree. Mai due comandi in parallelo dentro la tua lane. Mai
`server --force`. A fine lavoro provi che la porta è libera con
`lsof -nP -iTCP:<PORTA> -sTCP:LISTEN`.

## Come troverai il worktree, e perché non è rotto
- **`.env` assente**: è corretto. Nessun worktree coordinato ne ha uno. Non copiarlo
  mai da un altro checkout.
- **`backend/data/` vuoto**: normale finché non lanci un test. I data dir sono
  worktree-locali.
- **`frontend/node_modules` assente**: 636 MB, lo installa il **coordinatore** se il
  tuo mandato ne ha bisogno. Non installarlo tu.
- **output graphify assente**: non è un blocco. Leggi le pagine devWiki committate.
- Mai `pipenv install`, `npm install`, `npm update`, `npm audit fix`, `./dev.py install`.
  Se manca una dipendenza, **riporta l'errore esatto**.

## Git — quello che non fai mai
Mai `git commit`, `push`, `merge`, `rebase`, `cherry-pick`, `reset`, cancellazione o
forzatura di branch, `worktree remove`. I messaggi di commit si **propongono**.
`git add` solo se il coordinatore te lo chiede esplicitamente per una risoluzione di
conflitto. Comandi Git in sola lettura: liberi.

## La tua prima consegna è un'ANALISI, non codice
⚠️ **Non scrivere una riga di codice prima che il coordinatore ti autorizzi.**

L'analisi deve contenere:
1. verifica dello stato attuale **sul codice**, non sui numeri di riga del piano —
   che possono essere invecchiati;
2. cosa è già fatto, cosa è andato alla deriva, cosa manca, cosa contraddice il piano;
3. le superfici esatte: codice, test, documentazione;
4. dipendenze e decisioni ancora da prendere;
5. previsione di conflitto con gli altri mandati attivi;
6. complessità e rischi principali;
7. passi di implementazione ordinati, e la definizione di finito;
8. strategia di test e quali specialisti servono (`test-author`, `docs-writer`);
9. dove vivrà il tuo piano in `progress/`.

Se durante l'analisi trovi che un presupposto del mandato è **falso**, quella è la
scoperta più preziosa che puoi consegnare: riportala, non aggirarla.

## Quando hai finito un pezzo
Dichiari `FROZEN` — nessuna altra modifica, nessun test, nessun server — e consegni
l'evidenza: comandi esatti ed esiti, non «verde».
```

---

## 3. I delta, uno per mandato

| `<L>` | `name` | `<TITOLO>` | `<FILE>` | `<PORTA>` | `<DIR>` | `node_modules` |
|---|---|---|---|---:|---|:---:|
| **A** | `A - Oracolo e migrazione` | Oracolo di test e migrazione matematica | `A-backend-oracolo-e-migrazione.md` | 6240 | `backend/data/test-risk-a` | — |
| **B** | `B - Tassonomia e benchmark` | Tassonomia degli asset e catalogo dei benchmark | `B-tassonomia-e-benchmark.md` | 6241 | `…-b` | ✅ |
| **C** | `C - Affettamento portafoglio` | Affettamento del portafoglio per asset | `C-backend-affettamento-portafoglio.md` | 6242 | `…-c` | — |
| **D** | `D - Primitive e card` | Primitive promosse e card del rischio | `D-frontend-primitive-e-card.md` | 6243 | `…-d` | ✅ |
| **E** | `E - Quattro livelli` | I quattro livelli su Dashboard e Broker Detail | `E-frontend-quattro-livelli.md` | 6244 | `…-e` | ✅ |
| **F** | `F - Laboratorio` | Asset Global, il laboratorio | `F-frontend-laboratorio.md` | 6245 | `…-f` | ✅ |
| **G** | `G - Colori allocazione` | Gerarchia cromatica nei grafici di allocazione | `G-frontend-colori-allocazione.md` | 6246 | `…-g` | ✅ |
| **H** | `H - Monte Carlo` | Rifondazione del Monte Carlo | `H-backend-montecarlo.md` | 6247 | `…-h` | — |
| **I** | `I - Documentazione` | Documentazione | `I-documentazione.md` | — | — | — |
| **N** | `N - Acquisizioni` | Acquisizioni backend per L1, L2 e L3 | `N-backend-acquisizioni.md` | 6248 | `…-n` | — |
| **J** | `J - Chiusura` | Chiusura e rilascio | `J-chiusura-e-rilascio.md` | 6249 | `…-j` | ✅ |

### 3.1 Le righe aggiuntive, per i mandati che ne hanno bisogno

Si appendono al preambolo. Solo dove elencato.

| `<L>` | Da aggiungere |
|---|---|
| **A** | *«Consegni **K1** a E — i due campi di schema — **prima** di cominciare M2. È l'unica parte del tuo lavoro che blocca qualcun altro. E `Sharpe(rm=…)` / D39 è **tuo**, come coda di M5: non è di N.»* |
| **B** | *«Prima decisione da prendere e comunicare: il naming dei sottotipi, `ETF_STOCK` o `ETF_EQUITY`. Scegline uno e usalo ovunque. Consegni **K2** a G e **K3** a E ed F.»* |
| **C** | *«Consegni **K4** a E. Se senti il bisogno di toccare un plugin, **è il segnale che stai sbagliando strada**: fermati e riporta.»* |
| **D** | *«**Blocchi E ed F**, i due mandati frontend più grandi: il tuo K5 è ciò che li fa partire. Comprende la divisione dello spec E2E da 817 righe — vedi §5.1 del tuo mandato.»* |
| **E** | *«Ricevi K1, K3, K4, K5, K6, K7, K8. **Non aspettarli**: costruisci lasciando il posto e innesta quando arrivano. Possiedi `risk-mocks.ts`, che F consuma.»* |
| **F** | *«Ricevi K3, K5, K7. `CorrelationHeatmap.svelte` sta dentro `risk/` ma è **tuo**: eccezione concordata con E. Consumi `risk-mocks.ts` di E, non lo scrivi.»* |
| **G** | *«Aspetti **K2** da B. Non scrivi `assetTypes.ts`: lo consumi. E invalidi gli screenshot della galleria — dichiaralo, non rigenerarli.»* |
| **H** | *«Sei un XL che **non aspetta nessuno e non blocca nessuno**: per questo parti presto. Se parti tardi diventi tu il percorso critico. Consegni **K6** a E.»* |
| **I** | *«**Nessuna lane, nessun server**: `mkdocs serve` usa la porta fissa 6042, fuori dal modello. Validi con `mkdocs build` e `check-links`. Il primo tempo va fatto **subito**: i mock d'indice, poi **K7** a E, F e H. Lavori tramite l'agente `docs-writer`. Solo inglese.»* |
| **N** | *«Nasci da un buco trovato verificando gli altri dieci mandati: leggi §1 del tuo file prima di tutto. Consegni **K8** a E. Attenzione alla trappola di segno di §3: riskfolio restituisce magnitudini positive, il nostro schema usa negativi.»* |
| **J** | *«Parti per ultimo, a catena completa. Sei il mandato dove è più facile barare, perché arrivi quando tutti sono stanchi: un cancello che si apre per stanchezza non è un cancello.»* |

---

## 4. Dopo la creazione — le due verifiche che non si saltano

Per ogni sessione creata, il coordinatore esegue:

```bash
git -C <worktree> rev-parse HEAD
git -C <worktree> ls-files .github/agents/coordinated-workstream.agent.md
```

La prima prova che il figlio è nato dalla baseline attesa. La seconda che l'agente
esiste **nel commit**, non solo sul disco del coordinatore — ed è già verificata su
`619c2d79e`, insieme a `release-coordinator` e alle skill citate (`test-triage`,
`testing-*`, `lint-format-*`, `plan-archive`, `wiki-*`).

Se la prima dà uno SHA diverso da `<BASELINE>`, **ci si ferma e si riconcilia**. Il
figlio deve fare la stessa verifica e riportare la discrepanza invece di continuare:
per questo è il primo punto del preambolo.

---

## 5. Le ondate

| Ondata | Mandati | Criterio |
|---|---|---|
| **1** | A · B · D · H · I | Chi **blocca qualcuno** o è **XL** |
| **1.5** | C · N | Indipendenti, consegnano solo innesti a E |
| **2** | E · F (dopo K5) · G (dopo K2) | A contratto ricevuto |
| **3** | J | A catena completa (**D46**) |

⚠️ **Il vincolo non è la macchina.** Le porte sono libere e i database isolati: dieci
backend simultanei girerebbero. Il collo di bottiglia è il **cancello analisi-prima**,
che è a firma del developer — e cinque analisi da revisionare insieme sono già molte.

---

## 6. L'autorizzazione a implementare

Regola del contratto `release-coordinator`, e non si aggira:

- il coordinatore può **respingere** o chiedere revisioni al piano di un figlio
  liberamente;
- il coordinatore può **approvare** solo dopo il **sign-off esplicito del developer**;
- alla prima autorizzazione **mai** `autopilot` né `autopilot_fleet`: si continua in
  `interactive`;
- l'autorizzazione del developer si **riporta alla lettera**, non si parafrasa.
