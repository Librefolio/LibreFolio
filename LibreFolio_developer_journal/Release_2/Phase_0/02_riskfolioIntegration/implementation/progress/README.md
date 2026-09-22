# `progress/` — i piani vivi dell'esecuzione

> Questa cartella esiste per un difetto trovato durante la verifica dei mandati, ed è
> utile sapere quale: il testo diceva *«ogni mandato apre il proprio file di piano in
> `implementation/`»* — ma i **mandati stanno già lì con quei nomi**.
>
> Un agente che avesse seguito l'istruzione alla lettera avrebbe aperto il proprio
> brief e cominciato a spuntarci sopra i passi, **distruggendo l'unica copia delle
> proprie istruzioni** — e scoprendolo solo dopo un azzeramento di contesto, cioè nel
> momento peggiore possibile.

---

## La regola

| Cosa | Dove | Chi scrive | Muta? |
|---|---|---|:---:|
| **Brief** del mandato | `implementation/<LETTERA>-*.md` | il coordinatore, prima del lancio | 🚫 **sola lettura** |
| **Piano vivo** | `implementation/progress/<LETTERA>-esecuzione.md` | il mandato stesso | ✅ dopo **ogni** passo |

Se un brief deve cambiare — perché l'ambito si sposta o un contratto cambia forma — lo
cambia il **coordinatore**, e lo comunica. Mai l'agente da solo, mai in silenzio.

---

## Cosa contiene un piano vivo

Non un diario narrativo: un **punto di ripristino**. Deve permettere a un agente con la
memoria azzerata di sapere dov'era e cosa aveva già scoperto.

```markdown
# <LETTERA> — piano di esecuzione

| | |
|---|---|
| Mandato | ../<LETTERA>-*.md |
| Branch | <nome> |
| Baseline | <SHA> |
| Lane | porta <N> · data dir <path> |

## Passi

- [x] 1. <titolo>  — ✅ <data>
  > **Note implementazione**: cosa è stato fatto davvero, e dove.
  > **Fuori pista**: cosa non era previsto.

- [ ] 2. <titolo>

## Evidenza

| Comando | Esito |
|---|---|
| `PIPENV_CUSTOM_VENV_NAME=… pipenv run python dev.py test --test-port … …` | 42 passed |

## Contratti

| # | Verso | Stato |
|---|---|---|
| K<n> | <mandato> | consegnato <data> / in attesa |
```

---

## Le due righe che contano più delle altre

**`Note implementazione`** — cosa è stato fatto *davvero*, non cosa era previsto. Se il
piano diceva «modificare X» e si è finito per modificare Y, è Y che va scritto.

**`Fuori pista`** — ogni deviazione: un comando fallito, un problema d'ambiente, un
rischio scoperto, un presupposto del brief risultato falso.

> ⚠️ **Il `Fuori pista` è la riga più preziosa dell'intera campagna.** La verifica dei
> dieci mandati ha trovato tre decisioni senza proprietario e un difetto che avrebbe
> distrutto un brief: nessuna delle quattro era un errore di esecuzione, tutte erano
> **presupposti creduti veri**. Una riga «fuori pista» scritta al momento vale più di
> una ricostruzione fatta dopo.

E vale la regola del progetto: **si aggiorna dopo ogni passo, non alla fine**. Un piano
aggiornato alla fine è un resoconto; un piano aggiornato durante è una rete.

---

## Cosa non va qui

- I contratti → [`../contracts/`](../contracts/), che è del coordinatore.
- Lo stato d'insieme della campagna → [`../README.md`](../README.md), idem.
- Le decisioni → [`../../04-decisioni-e-questioni-aperte.md`](../../04-decisioni-e-questioni-aperte.md).
  Un mandato che *scopre* qualcosa che merita una decisione lo **riporta al
  coordinatore**: non scrive nel registro.
