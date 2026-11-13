// @vitest-environment jsdom
/**
 * AiExportMenu — one Escape closes one layer (C-12, Vitest + jsdom).
 *
 * The menu closes itself from a capturing `keydown` listener on the document. Without stopping the key, the same
 * Escape went on to the layer under the menu (a modal, a panel) and closed it too. The contract: the Escape the menu
 * consumes stops there; with the menu closed, the next Escape reaches whoever is under it.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import AiExportMenu from '../AiExportMenu.svelte';
import {buildAiExportMenuLabels} from '../ui';
import {compatibilityFixture} from './runtimeFixtures';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

describe('AiExportMenu — Escape', () => {
    it('closes the menu and does not reach the layer under it; the next Escape does', async () => {
        const compatibility = compatibilityFixture();
        render(AiExportMenu, {
            domain: 'portfolio',
            compatibility,
            memoryKey: 'portfolio',
            defaultSelectionId: 'portfolio.pac_planning',
            labels: buildAiExportMenuLabels((key: string) => key, compatibility, 'AI Export'),
            onprepare: vi.fn(),
            oncopied: vi.fn(),
            onerror: vi.fn(),
        });
        const underneath = vi.fn();
        document.body.addEventListener('keydown', underneath);

        const trigger = screen.getByTestId('ai-export-button');
        await fireEvent.click(trigger);
        await waitFor(() => expect(screen.getByTestId('ai-export-menu-panel')).toBeInTheDocument());

        await fireEvent.keyDown(screen.getByTestId('ai-export-menu-panel'), {key: 'Escape'});
        await waitFor(() => expect(screen.queryByTestId('ai-export-menu-panel')).toBeNull());
        expect(underneath, 'the Escape the menu consumed must not reach the layer under it').not.toHaveBeenCalled();

        await fireEvent.keyDown(document.body, {key: 'Escape'});
        expect(underneath, 'with the menu gone, the next Escape is the layer under its own').toHaveBeenCalledTimes(1);
        document.body.removeEventListener('keydown', underneath);
    });
});
