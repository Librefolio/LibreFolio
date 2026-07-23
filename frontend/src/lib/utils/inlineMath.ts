import katex from 'katex';
import 'katex/dist/katex.min.css';

export function escapeHtml(value: string): string {
    return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function renderInlineMath(content: string): string {
    return content.replace(/\$([^$]+)\$/g, (_, formula: string) => {
        try {
            return katex.renderToString(formula, {throwOnError: false, displayMode: false});
        } catch {
            return formula;
        }
    });
}

export function renderInlineMathText(text: string): string {
    return renderInlineMath(escapeHtml(text));
}
