/**
 * Prompt template — shared static English sections reused across the
 * instruction-bearing prompts in the catalog (see promptTemplates.ts for the
 * per-prompt role/task text).
 */

export const PROMPT_WEB_RESEARCH = `If you have web access, research only the most relevant assets, sectors, or themes based on concentration, recent performance, volatility, or technical context. Do not research every asset.
Clearly separate conclusions based on the provided portfolio data from conclusions based on web research.
If you do not have web access, state it and rely only on the provided data.`;

export const PROMPT_TECHNICAL_DISCLAIMER = `Technical indicators are descriptive context only.
Do not treat them as deterministic buy/sell signals.`;

export const PROMPT_INVESTOR_ASSUMPTIONS_NOTE = `Do not assume the user's risk tolerance, investment horizon, income, age, or target allocation. Ask clarifying questions when needed.`;

export function buildResponseLanguageLine(language: string): string {
    return `Please provide your answer in: ${language}.`;
}
