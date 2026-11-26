// @vitest-environment jsdom
/**
 * AiExportMenu — a copy the browser refused (testlist of 25/11, Vitest + jsdom).
 *
 * The text is ready and a press of the user's copies it: the refusal leaves «Copy the ready text», whatever the size's
 * severity, and nothing is computed again. It used to leave the box without a button (`pendingContext` was cleared), and
 * «Copy anyway» did nothing at all. The steps the menu shows are the client's real ones.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

import AiExportMenu from '../AiExportMenu.svelte';
import {prepareAiExport, type AiExportStep, type PreparedAiExport} from '../aiExportClipboard';
import {estimateAiExportTokenSeverity} from '../aiExportOptions';
import {AiExportClipboardUnavailableError} from '../aiExportClipboard';
import {buildAiExportMenuLabels} from '../ui';
import {compatibilityFixture, selectionFixture, snapshotFixture} from './runtimeFixtures';

beforeAll(async () => {
    await setupI18n();
});

let writeText: ReturnType<typeof vi.fn>;
beforeEach(() => {
    writeText = vi.fn();
    Object.defineProperty(navigator, 'clipboard', {value: {writeText}, configurable: true});
    Object.defineProperty(window, 'isSecureContext', {value: true, configurable: true});
    // The shared writer's fallback has no transport either in jsdom
    Object.defineProperty(document, 'execCommand', {value: () => false, configurable: true});
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

const denied = (): Error => Object.assign(new Error('Document is not focused'), {name: 'NotAllowedError'});

function openMenu(prompt?: string) {
    const compatibility = compatibilityFixture();
    const selection = selectionFixture('dataset', 'portfolio.overview_and_history');
    const onerror = vi.fn();
    const oncopied = vi.fn();
    const onprepare = vi.fn(async (options: Parameters<typeof prepareAiExport>[0]['options'], onstep: (step: AiExportStep) => void): Promise<PreparedAiExport> => {
        const prepared = await prepareAiExport({context: {domain: 'portfolio', snapshotAsOf: '2026-03-31', targetCurrency: 'EUR'}, options, compatibility}, {transport: async (request) => snapshotFixture(selection, request.detail_level, request.period), onstep});
        return prompt === undefined ? prepared : {...prepared, prompt, stats: {...prepared.stats, finalPrompt: {...prepared.stats.finalPrompt, estimatedTokens: 500_000}}};
    });
    render(AiExportMenu, {domain: 'portfolio', compatibility, memoryKey: 'portfolio', defaultSelectionId: 'portfolio.overview_and_history', labels: buildAiExportMenuLabels((key: string) => key, compatibility, 'AI Export'), onprepare, oncopied, onerror});
    return {onprepare, oncopied, onerror};
}

async function prepareOnce(): Promise<void> {
    await fireEvent.click(screen.getByTestId('ai-export-button'));
    await waitFor(() => expect(screen.getByTestId('ai-export-copy-button')).toBeEnabled());
    await fireEvent.click(screen.getByTestId('ai-export-copy-button'));
}

describe('a copy the browser refused', () => {
    it('keeps the text ready behind a button of its own, and copies it without a new request', async () => {
        writeText.mockRejectedValueOnce(denied());
        const {onprepare, oncopied, onerror} = openMenu();
        await prepareOnce();
        const ready = await screen.findByTestId('ai-export-copy-ready');
        expect(ready).toBeEnabled();
        expect(onerror).toHaveBeenCalledTimes(1);
        const error: unknown = onerror.mock.calls[0][0];
        expect(error).toBeInstanceOf(AiExportClipboardUnavailableError);
        expect(oncopied).not.toHaveBeenCalled();

        writeText.mockResolvedValueOnce(undefined);
        await fireEvent.click(ready);
        await waitFor(() => expect(oncopied).toHaveBeenCalledTimes(1));
        expect(onprepare, 'the prompt was computed again').toHaveBeenCalledTimes(1);
        expect(writeText.mock.calls[1][0], 'the same text').toBe(writeText.mock.calls[0][0]);
        await waitFor(() => expect(screen.queryByTestId('ai-export-menu-panel')).toBeNull());
    });

    it('a second refusal leaves the button where it was, and says so again', async () => {
        writeText.mockRejectedValue(denied());
        const {onprepare, onerror} = openMenu();
        await prepareOnce();
        await fireEvent.click(await screen.findByTestId('ai-export-copy-ready'));
        await waitFor(() => expect(onerror).toHaveBeenCalledTimes(2));
        expect(screen.getByTestId('ai-export-copy-ready')).toBeEnabled();
        expect(onprepare).toHaveBeenCalledTimes(1);
    });

    it('a large text asks first; its refusal, then, is copied by the same button, not lost', async () => {
        writeText.mockRejectedValueOnce(denied());
        const {onprepare, oncopied, onerror} = openMenu('a large prompt');
        await prepareOnce();
        expect(estimateAiExportTokenSeverity(500_000)).not.toBe('normal');
        // «Copy anyway» is the first press, and the browser refuses it
        await fireEvent.click(await screen.findByTestId('ai-export-copy-anyway'));
        await waitFor(() => expect(onerror).toHaveBeenCalledTimes(1));
        writeText.mockResolvedValueOnce(undefined);
        await fireEvent.click(await screen.findByTestId('ai-export-copy-ready'));
        await waitFor(() => expect(oncopied).toHaveBeenCalledTimes(1));
        expect(onprepare).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenLastCalledWith('a large prompt');
    });

    it('a change of the options drops the ready text and its button', async () => {
        writeText.mockRejectedValueOnce(denied());
        openMenu();
        await prepareOnce();
        await screen.findByTestId('ai-export-copy-ready');
        await fireEvent.click(screen.getByTestId('ai-export-category-analysis'));
        await waitFor(() => expect(screen.queryByTestId('ai-export-copy-ready')).toBeNull());
    });
});

describe('the steps the menu shows', () => {
    it('shows the request, then the rendering, then the copy, and none of them when it is done', async () => {
        const seen: (string | null)[] = [];
        let letCopy: () => void = () => {};
        writeText.mockImplementation(() => new Promise<void>((resolve) => (letCopy = resolve)));
        openMenu();
        const observer = new MutationObserver(() => {
            const node = document.querySelector('[data-testid="ai-export-progress"]');
            const step = node?.getAttribute('data-step') ?? null;
            if (step !== null && seen.at(-1) !== step) seen.push(step);
        });
        observer.observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ['data-step']});
        await prepareOnce();
        await waitFor(() => expect(seen).toContain('copy'));
        expect(seen).toEqual(['request', 'render', 'copy']);
        letCopy();
        await waitFor(() => expect(screen.queryByTestId('ai-export-progress')).toBeNull());
        observer.disconnect();
    });
});
