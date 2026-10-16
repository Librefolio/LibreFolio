// @vitest-environment jsdom
/**
 * FileGrid — the scope and the delete of a card (decision 36), as a component test.
 *
 * In browse mode with actions, a card offers its file the opposite scope — `file-grid-scope-<id>`, which calls
 * `onscopechange({file, scope})` — and its delete, `file-grid-delete-<id>`, which calls `ondelete({id})`. Both only to
 * whoever may manage the file: `can_delete !== false`, as the server reports it (its uploader or an admin). A file
 * whose `can_delete` is absent keeps both, as files listed before the field did. The scope button also needs a parent
 * that handles it: without `onscopechange` there is nothing to call, so there is no button. Select mode — the picker —
 * shows no card actions at all. A card action is not a click on the card: it never selects the card.
 *
 * Every absence is asserted beside a presence in the same render: the card is drawn (`file-grid-size-<id>`, which
 * every card publishes) and another card, or the same one in browse mode, has the control. So «no button here» never
 * passes on a grid that drew nothing, nor on one where the button has no test id yet.
 *
 * The real FileGrid; only the network is cut: `formatBytes` shares its module with `uploadFile`, so `$lib/api` is
 * stubbed. Text files, so no image preview is involved.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({axiosInstance: {post: vi.fn()}, zodiosApi: {}}));

import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {UploadedFile} from '$lib/types';
import FileGrid from './FileGrid.svelte';

const UPLOADED_AT = '2026-10-15T12:00:00Z';

/** A text file; `canDelete` undefined leaves the field out, as on a file listed before it existed. */
function textFile(id: string, scope: UploadedFile['scope'], canDelete: boolean | undefined): UploadedFile {
    const file: UploadedFile = {id, original_name: `grid-${id}.txt`, mime_type: 'text/plain', size_bytes: 256, uploaded_at: UPLOADED_AT, uploaded_by_user_id: 7, scope, url: `/review/grid/${id}`};
    return canDelete === undefined ? file : {...file, can_delete: canDelete};
}

/** The grid as the Files page draws it — browse mode, actions on — with every callback a spy. */
function mount(files: UploadedFile[], props: Record<string, unknown> = {}) {
    const onscopechange = vi.fn();
    const ondelete = vi.fn();
    const onselect = vi.fn();
    const onpreview = vi.fn();
    const result = render(FileGrid, {files, mode: 'browse', cardSize: 'full', showSearch: false, showActions: true, onscopechange, ondelete, onselect, onpreview, ...props});
    return {...result, onscopechange, ondelete, onselect, onpreview};
}

beforeAll(async () => {
    await setupI18n();
});

describe('FileGrid — the scope button of a card (decision 36)', () => {
    it('offers common to a personal file the user may manage, without selecting the card', async () => {
        const file = textFile('own-personal', 'personal', true);
        const {onscopechange, onselect, ondelete} = mount([file]);

        await fireEvent.click(screen.getByTestId('file-grid-scope-own-personal'));

        expect(onscopechange).toHaveBeenCalledExactlyOnceWith({file: expect.objectContaining({id: 'own-personal'}), scope: 'common'});
        expect(onselect).not.toHaveBeenCalled();
        expect(ondelete).not.toHaveBeenCalled();
    });

    it('offers personal to a common file the user may manage', async () => {
        const file = textFile('own-common', 'common', true);
        const {onscopechange, onselect} = mount([file]);

        await fireEvent.click(screen.getByTestId('file-grid-scope-own-common'));

        expect(onscopechange).toHaveBeenCalledExactlyOnceWith({file: expect.objectContaining({id: 'own-common'}), scope: 'personal'});
        expect(onselect).not.toHaveBeenCalled();
    });

    it('keeps the scope button and delete on a file whose can_delete is absent', () => {
        mount([textFile('legacy', 'common', undefined)]);

        expect(screen.getByTestId('file-grid-scope-legacy')).toBeInTheDocument();
        expect(screen.getByTestId('file-grid-delete-legacy')).toBeInTheDocument();
    });

    it('draws no scope button when the parent handles no scope change; delete stays', () => {
        mount([textFile('own-personal', 'personal', true)], {onscopechange: undefined});

        // The card's actions are drawn: delete is there.
        expect(screen.getByTestId('file-grid-delete-own-personal')).toBeInTheDocument();
        expect(screen.queryByTestId('file-grid-scope-own-personal')).toBeNull();
    });
});

describe('FileGrid — what a file the user may not manage offers (decision 36)', () => {
    it('neither the scope button nor delete, beside a manageable file that has both; preview stays', () => {
        mount([textFile('own-common', 'common', true), textFile('foreign-common', 'common', false)]);

        // Controls, same render: the user's own file has both, and the other card is drawn with its other actions.
        expect(screen.getByTestId('file-grid-scope-own-common')).toBeInTheDocument();
        expect(screen.getByTestId('file-grid-delete-own-common')).toBeInTheDocument();
        expect(screen.getByTestId('file-grid-size-foreign-common')).toBeInTheDocument();
        expect(screen.getByTestId('file-grid-preview-foreign-common')).toBeInTheDocument();

        expect(screen.queryByTestId('file-grid-scope-foreign-common')).toBeNull();
        expect(screen.queryByTestId('file-grid-delete-foreign-common')).toBeNull();
    });
});

describe('FileGrid — delete by its own test id (decision 36)', () => {
    it('hands the file id to ondelete, without selecting the card', async () => {
        const {ondelete, onselect, onscopechange} = mount([textFile('own-personal', 'personal', true)]);

        await fireEvent.click(screen.getByTestId('file-grid-delete-own-personal'));

        expect(ondelete).toHaveBeenCalledExactlyOnceWith({id: 'own-personal'});
        expect(onselect).not.toHaveBeenCalled();
        expect(onscopechange).not.toHaveBeenCalled();
    });
});

describe('FileGrid — select mode has no card actions (decision 36)', () => {
    it('the picker’s grid draws neither the scope button nor delete, which browse mode draws for the same file', () => {
        const file = textFile('own-personal', 'personal', true);

        // Control: in browse mode the same file has both.
        const browse = mount([file]);
        expect(within(browse.container).getByTestId('file-grid-scope-own-personal')).toBeInTheDocument();
        expect(within(browse.container).getByTestId('file-grid-delete-own-personal')).toBeInTheDocument();
        browse.unmount();

        // Select mode, even with showActions on: the card is drawn, without them.
        const picker = mount([file], {mode: 'select', cardSize: 'compact', showActions: true});
        expect(within(picker.container).getByTestId('file-grid-size-own-personal')).toBeInTheDocument();
        expect(within(picker.container).queryByTestId('file-grid-scope-own-personal')).toBeNull();
        expect(within(picker.container).queryByTestId('file-grid-delete-own-personal')).toBeNull();
    });
});
