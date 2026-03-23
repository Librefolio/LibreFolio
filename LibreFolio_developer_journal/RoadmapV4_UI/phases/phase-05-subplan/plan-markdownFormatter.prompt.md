# Plan: Markdown Formatter per MkDocs (Admonition-safe)

## ✅ SOLUZIONE TROVATA — Riga vuota dopo `!!!`/`???`

**Scoperta**: aggiungendo una **riga vuota** tra la direttiva admonition (`!!!`/`???`) e il corpo indentato, Prettier **non tocca nulla**. MkDocs renderizza **identicamente** con o senza la riga vuota.

```markdown
<!-- ✅ Prettier-safe — NON TOCCA NULLA -->
!!! note "Titolo"

    Contenuto indentato a 4 spazi.

<!-- ❌ Prettier rompe — rimuove l'indentazione -->
!!! note "Titolo"
    Contenuto indentato a 4 spazi.
```

### Test eseguiti (2026-03-23)

| Test | Risultato |
|------|-----------|
| Prettier su admonition SENZA riga vuota | ❌ Indentazione rimossa (da 4 spazi a 0) |
| Prettier su admonition CON riga vuota | ✅ File `(unchanged)` — 0 diff |
| MkDocs `markdown.Markdown` rendering CON riga vuota | ✅ HTML identico |
| MkDocs `mkdocs build --strict` dopo fix | ✅ Build riuscito |
| Fix automatico 199 admonition in 99 file | ✅ Applicato |

### Modifiche implementate

1. **Fix dati**: tutte le 199 admonition in 99 file `.md` hanno ora la riga vuota
2. **`skill_agent_note.md`**: aggiunta regola sulla riga vuota obbligatoria (sezione 7.2)
3. **`dev.py`**: `cmd_mkdocs_build` esegue `_check_admonition_empty_lines()` prima del build
4. **`validate_translations.py`**: nuovo check `admonition-empty-line` (severity WARN)
5. **`translate_docs.py`**: `_structural_diff` check `ADMONITION_EMPTY_LINE` per il critic LLM

---

## Piano di Test

### Step 0 — Reset ambiente

```bash
rm -rf /tmp/fmt-test && mkdir -p /tmp/fmt-test

DOCS=~/Documents/00_My/LibreFolio/mkdocs_src/docs
cp $DOCS/financial-theory/transaction-types.en.md /tmp/fmt-test/html-en.md      # HTML table
cp $DOCS/financial-theory/transaction-types.it.md /tmp/fmt-test/html-it.md
cp $DOCS/admin/cli_tools.en.md                    /tmp/fmt-test/adm-en.md       # Admonitions
cp $DOCS/admin/cli_tools.it.md                    /tmp/fmt-test/adm-it.md
cp $DOCS/financial-theory/returns.en.md            /tmp/fmt-test/latex-en.md     # LaTeX + tabelle MD
cp $DOCS/financial-theory/returns.it.md            /tmp/fmt-test/latex-it.md
cp $DOCS/gallery/desktop.en.md                     /tmp/fmt-test/gallery-en.md   # Div HTML
cp $DOCS/gallery/desktop.it.md                     /tmp/fmt-test/gallery-it.md

echo "Files ready" && ls /tmp/fmt-test/
```

### Test A — Esiste un plugin Prettier per admonition?

```bash
npm search prettier-plugin-admonition 2>/dev/null | head -5
npm search prettier-plugin-mkdocs 2>/dev/null | head -5
npm search prettier markdown admonition 2>/dev/null | head -10
```

Se trovato → installare e testare su `adm-en.md`. Se non esiste → Test A chiuso.

### Test B — Prettier con `<!-- prettier-ignore -->` automatico

L'idea: proteggere le admonition prima di Prettier, formattare, poi rimuovere la protezione.

```bash
cd /tmp/fmt-test && cp adm-en.md adm-B.md

# Pre-process: inserisci <!-- prettier-ignore --> prima di ogni !!! e ???
perl -i -pe 's/^(!!!|[?]{3})\s/<!-- prettier-ignore -->\n$&/' adm-B.md

# Formatta
npx prettier --parser markdown --prose-wrap preserve --tab-width 4 --write adm-B.md 2>/dev/null

# Post-process: rimuovi i commenti
sed -i '' '/^<!-- prettier-ignore -->$/d' adm-B.md

# Verifica: body indentato a 4 spazi?
echo "=== Check ===" && grep -A2 '^!!!' adm-B.md
echo "=== Diff ===" && diff adm-en.md adm-B.md
```

### Test C — mdformat-mkdocs + sed (riferimento già validato)

```bash
cd /tmp/fmt-test && cp adm-en.md adm-C.md

cd ~/Documents/00_My/LibreFolio
pipenv run mdformat --no-validate --number /tmp/fmt-test/adm-C.md
sed -i '' 's/^_\{3,\}$/---/' /tmp/fmt-test/adm-C.md

echo "=== Diff ===" && diff /tmp/fmt-test/adm-en.md /tmp/fmt-test/adm-C.md
# Atteso: 0 diff
```

### Test D — BeautifulSoup per re-indent HTML

```bash
cd ~/Documents/00_My/LibreFolio

echo "=== BEFORE ===" 
grep '<thead>' /tmp/fmt-test/html-en.md /tmp/fmt-test/html-it.md

pipenv run python3 << 'PYEOF'
import re
from bs4 import BeautifulSoup

def reformat_html_blocks(filepath):
    with open(filepath) as f:
        content = f.read()

    def reformat(match):
        soup = BeautifulSoup(match.group(0), 'html.parser')
        return soup.prettify(formatter='html5').rstrip()

    result = re.sub(r'<table[\s>].*?</table>', reformat, content, flags=re.DOTALL)
    result = re.sub(r'<div[\s>].*?</div>', reformat, result, flags=re.DOTALL)

    with open(filepath, 'w') as f:
        f.write(result)
    print(f"Done: {filepath}")

reformat_html_blocks('/tmp/fmt-test/html-en.md')
reformat_html_blocks('/tmp/fmt-test/html-it.md')
PYEOF

echo "=== AFTER ==="
grep '<thead>' /tmp/fmt-test/html-en.md /tmp/fmt-test/html-it.md

echo "=== EN vs IT identici? ==="
diff <(grep '<' /tmp/fmt-test/html-en.md) <(grep '<' /tmp/fmt-test/html-it.md)
```

### Test E — Pipeline completa (vincitore + BS4)

Dopo aver scelto il vincitore tra A/B/C, combinare con D su tutti e 4 i file campione e verificare uniformità EN vs IT.

---

## Tabella decisionale

| Scenario              | Markdown                                  | HTML            | Pro                              | Contro                    |
| --------------------- | ----------------------------------------- | --------------- | -------------------------------- | ------------------------- |
| mdformat + BS4        | mdformat-mkdocs + `sed ---`               | BS4 prettify    | Tutto Python, admonition nativi  | sed post-process per `---`|
| Prettier protect + BS4| Prettier + pre/post `<!-- ignore -->`     | BS4 prettify    | Formatta bene tabelle MD         | Fragile, dipende da npx   |
| Solo BS4              | niente                                    | BS4 prettify    | Minimalista, zero rischi MD      | Non normalizza il markdown|
