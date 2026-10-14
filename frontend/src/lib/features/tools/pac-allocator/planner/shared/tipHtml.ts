/**
 * The HTML of a planner explanation, for `Tooltip` with `math` (R11.2). The text is escaped
 * first; a run of lines that start with «• » becomes one bulleted list, the other lines keep
 * their line breaks. No other markup is produced.
 */
import {escapeHtml} from '$lib/utils/inlineMath';

const LIST = 'my-1 list-disc space-y-0.5 pl-4';

export function tipHtml(text: string): string {
    const blocks: string[] = [];
    let lines: string[] = [];
    let items: string[] = [];
    const flushLines = () => {
        if (lines.length > 0) blocks.push(lines.join('<br>'));
        lines = [];
    };
    const flushItems = () => {
        if (items.length > 0) blocks.push(`<ul class="${LIST}">${items.map((item) => `<li>${item}</li>`).join('')}</ul>`);
        items = [];
    };
    for (const line of escapeHtml(text).split('\n')) {
        if (line.startsWith('• ')) {
            flushLines();
            items.push(line.slice(2));
        } else {
            flushItems();
            lines.push(line);
        }
    }
    flushLines();
    flushItems();
    return blocks.join('');
}
