const INLINE_MARKDOWN_CHARACTERS = new Set(['\\', '`', '*', '_', '[', ']', '<', '>']);
const FENCE_LANGUAGE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._+-]*$/;

export interface FencedSectionOptions {
    heading: string;
    language?: string;
    content: string;
}

export function createBacktickFence(content: string): string {
    let longestRun = 0;
    let currentRun = 0;

    for (const character of content) {
        if (character === '`') {
            currentRun += 1;
            longestRun = Math.max(longestRun, currentRun);
        } else {
            currentRun = 0;
        }
    }

    return '`'.repeat(Math.max(3, longestRun + 1));
}

export function escapeMarkdownTableCell(value: string): string {
    return value.replaceAll('\\', '\\\\').replaceAll('|', '\\|').replaceAll('\n', '\\n').replaceAll('\r', '\\r');
}

export function escapeMarkdownInlineLabel(value: string): string {
    let escaped = '';
    for (const character of value) {
        if (INLINE_MARKDOWN_CHARACTERS.has(character)) escaped += '\\';
        escaped += character;
    }
    return escaped;
}

export function renderFencedSection({heading, language = '', content}: FencedSectionOptions): string {
    if (heading.length === 0 || heading.includes('\n') || heading.includes('\r')) {
        throw new TypeError('Markdown section heading must be a non-empty single line');
    }
    if (language.length > 0 && !FENCE_LANGUAGE_PATTERN.test(language)) {
        throw new TypeError('Markdown fence language must be a trusted single token');
    }

    const fence = createBacktickFence(content);
    const contentTerminator = content.endsWith('\n') ? '' : '\n';
    return `## ${escapeMarkdownInlineLabel(heading)}\n\n${fence}${language}\n${content}${contentTerminator}${fence}`;
}
