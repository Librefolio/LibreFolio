/**
 * Shared response-style instructions — included in the header of every
 * instruction-bearing AI export prompt (portfolio-level and asset-level).
 *
 * PROMPT_CONCISE_RESPONSE is inspired by the repository's own `caveman` skill
 * (terse, no filler/hedging/preamble, lead with the conclusion) but phrased in
 * plain professional English rather than actual "caveman" shorthand — this text
 * is read by an external AI *and* by the user reviewing its answer, so it must
 * stay natural language, not compressed jargon.
 */

export const PROMPT_CONCISE_RESPONSE = `Respond concisely.
Avoid preamble, filler, hedging, and restating the provided data verbatim.
Lead with the conclusion or answer, then add supporting detail only if it changes the takeaway.
Prefer short, direct sentences and structured lists over long prose paragraphs.
Do not re-describe charts, numbers, or tables that are already visible to the user in the app — reference them briefly, only when needed to support a conclusion.`;

export const PROMPT_ASSET_NAMING = `Refer to assets only by their "name" field (as given in the data) in your response text.
Never use ticker, ISIN, or other identifier codes to refer to an asset when talking to the user — those fields ("identifiers") are provided only to support accurate web research.`;
