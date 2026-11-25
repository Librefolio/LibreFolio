---
name: user-replies
description: Use this skill when drafting a reply to a LibreFolio user or contributor on GitHub (issue, pull request, discussion) or by email — answering a feature request or a bug report, asking for an export or screenshots, reviewing an external PR, giving a status update or a post-release note. It holds the developer's voice, the structure of a good reply, how to ask for a masked export safely, and what never goes in a public comment.
---

# Replying to users

LibreFolio's replies come from the developer (GitHub `Alfystar`), even when an agent drafts them. They read like a
person who is glad the user wrote: warm, concrete, honest about dates, never corporate. Drawn from the replies on
#25, #26, #33, #35, #86, #87, #89, #90 and on `borsaItaliana-scraping` #5, #6, #7 (2026-09 → 2026-11).

**Every draft is shown to the developer before it is posted.** Posting, editing or closing anything on GitHub, or sending
an email, needs his explicit yes for that text.

## 1. Voice

- **The user's language.** Italian to an Italian user (#89), English otherwise (French and other users write English:
  #90). Never machine-sounding: short sentences, the words a person would say.
- **Call people by their GitHub handle**, `@nick`, never by their first name, in the greeting and whenever you name
  them (developer, 24/11/2026): «Ciao @giulioboffo», «grazie a @giulioboffo per …».
- **Open with the person**: «Hi @user, thanks for …!» / «Ciao @user, grazie davvero per …! 🙂». Name what they did well
  (a clear report, a good idea, a careful PR) in a few words, not a paragraph of praise.
- **One or two emoji at most**, where a person would put them (👋, 🙂, 😊, 🎉, 🚀). None in a bug acknowledgement that is
  serious.
- **Honest about time.** «No date yet», «it did not make it into 1.3, sorry», «ci potrebbe volere un mesetto». Never
  promise a release you do not control; say which release it is *planned* for only when the plan says so.
- **Say what you learned from them** when it is true (#26: «Your two exports taught me something I didn't expect»).
- **Close warmly and briefly**: «Thanks again!», «Grazie ancora!», «I'll keep you posted». Offer the thread for more
  ideas when it fits.

## 2. Structure

- **Short paragraphs, one idea each.** A new topic gets a new paragraph, and a question the user must answer gets its
  own line, introduced naturally: «Ah, while we're at it, I wanted to ask you …» / «Ah, già che ci siamo, volevo
  chiederti …». A question buried in a bullet list gets missed (developer, 24/11/2026).
- **Bold** only the few things the user must not miss: the decision, the address to write to, the masking rules.
- Lists for steps or for items the user has to provide; prose for explanations.
- **Questions numbered** when there are several and you need each answered (#25, #26).
- A concrete example with numbers when you ask about behaviour (#25: «say you spent 105 €: 100 € shares + 5 € fee»).
- Link the guide page or the issue that shows what you mean (the Crédit Agricole or Directa import guide).

## 3. Asking for an export (data from a real account)

Always the same rules, written plainly (#86, #87, #90):

- **Where**: by email to **alfanoing@gmail.com** — never attached publicly to the issue. (A reply sent by email to a
  GitHub notification loses its attachments: #33/#35. If a user insists on GitHub, ask them to drag the file into the
  comment box from the browser, and only after masking.)
- **How to mask it** — the file must stay usable:
  - **personal identifiers** (names, account numbers, IBANs, wallet addresses, order and position IDs): replace freely;
  - **dates**: if they want, shift them, but **all by the same offset** (e.g. every date moved back by 37 days);
  - **amounts**: if they want, scale them, but **all by the same factor** (e.g. every value × 0.73), so the numbers
    stay consistent with each other;
  - **keep everything else exactly as the broker writes it**: file type, sheet names, header rows, column order,
    separator, date and number formats, and the **words** — transaction type labels, descriptions, comments («Stocks/ETF
    purchase», «Deposit», «Distributed»…). The layout and the labels are what the importer reads.
- **What we do with it**: we use it **only internally** to build and test the importer. The repository never gets their
  file: the sample committed is a further, **synthetic** file, invented by us on the same structure (or rebuilt from
  theirs by a script that keeps no real value, as for XTB, lane 83).
- **Also useful**: which language their broker interface uses (labels may be translated); a few **screenshots of how to
  reach the export button**, for the import guide — offered as a favour, «if you have the time and feel like it».
- **Invite contributions**: if they use a broker we do not support, one that imports badly for them, or one whose guide
  lacks detail or screenshots, say we would be glad of the same kind of material.

## 4. Reviewing an external pull request

- Thank them for the specific contribution; say what is good before what must change (#87, `borsaItaliana-scraping`
  #6/#7).
- Number the requested changes; mark the minor ones «(Minor)».
- Explain *why* (an API that is public, a test that fails, a dependency that weighs on everyone).
- «Refs #N» instead of «Fixes #N» when the PR covers only part of an issue.
- Never run an external PR's code locally; read the diff.
- When we finish a PR ourselves, say so kindly and tell them what to do next (e.g. «wait for our fix commits, then sync
  your branch»).

## 5. Never in a public reply

- The developer's or another user's personal data beyond what is already public; real figures from anyone's portfolio
  (screenshots of the app use the demo data or invented numbers).
- Internal names: lanes, lots, journal paths, agent names, the AI that helped. «We» or «I» is enough.
- Promises of a date the plan does not hold.

## 6. Status updates and after the release

- When something ships, go back to the issue and say so, with what changed and anything the user must do (re-import,
  delete old rows…). The list of these replies lives in the journal, `ATTIVITA_POST_RILASCIO_<release>.md`.
- When something slips, say it plainly and say what did ship instead (#25, 10/11/2026).

## Lessons learned (append, one dated line each)

- 24/11/2026 — A question for the user must stand in its own paragraph, introduced naturally («Ah, while we're at it…»),
  not as the first bullet of a list of things to send: in #90 the question «which wallet or exchange?» was missed.
- 24/11/2026 — The masking rules are always the full ones of §3 (same offset, same factor, words untouched, a synthetic
  sample in the repository): «anonymised» alone makes users change labels and amounts at random.
- 24/11/2026 — Closing an issue after a PR (`borsaItaliana-scraping` #5): say what the merged PR covers, leave each idea
  still open to its own new issue, and renew the invitation to contributors who are still working on it. The developer
  approved this style («ora va bene»).
