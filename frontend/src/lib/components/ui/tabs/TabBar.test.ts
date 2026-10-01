// @vitest-environment jsdom
/**
 * TabBar — label visibility and accessible names (Vitest + jsdom).
 *
 * K step 13, item 7. The asset detail page hands PageToolbar two tabs with no `icon`, and
 * PageToolbar passes `showLabels={false}` below its `labelHideTabs` threshold (370 px of bar).
 * TabBar then hides every label unconditionally, so on a phone the two tabs render as empty
 * buttons: nothing to see. The approved fix has three parts. The icons belong to the page and
 * are asserted by the E2E (`e2e/assets/asset-mobile-layout.spec.ts`); the other two live in
 * TabBar and are pinned here, with a guard:
 *
 *   1. TabBar never hides the label of a tab that has no icon — whichever switch asked for it,
 *      `showLabels={false}` or `hideLabelOnMobile`;
 *   2. when it does hide a label, the button carries `aria-label={tab.label}`;
 *   3. (guard) while labels are shown, the visible text names the tab and no `aria-label` is added.
 *
 * Every button already carries `title={tab.label}`, which browsers fall back on for a name when
 * the content has none: the name is implicit today, not missing. The contract asked for is the
 * explicit `aria-label`.
 *
 * Why the assertions read a class and an attribute. jsdom loads no Tailwind, so `hidden` and
 * `sm:inline` compute to nothing and `toBeVisible()` would be true for every label: the class
 * token IS the rendering contract that can be observed here. For the same reason the computed
 * accessible name is useless in jsdom — the "hidden" label still contributes its text — so
 * the `aria-label` attribute is asserted directly. The real name, in a real layout, is
 * asserted by the E2E.
 *
 * Every label is a value this file passes in as a prop, never a translated string.
 */
import {describe, expect, it} from 'vitest';
import {render, screen, within} from '$test/component';
import {ChartLine, Shield} from 'lucide-svelte';
import TabBar, {type TabItem} from './TabBar.svelte';

const PLAIN_LABEL = 'Plain label';
const ICON_LABEL = 'Icon label';
const SECOND_ICON_LABEL = 'Second icon label';

/** A mixed bar: one tab without an icon, two with. Mixed on purpose — the rule is per tab. */
const TABS: TabItem[] = [
    {id: 'plain', label: PLAIN_LABEL, testId: 'tab-plain'},
    {id: 'iconic', label: ICON_LABEL, icon: Shield, testId: 'tab-iconic'},
    {id: 'iconic-2', label: SECOND_ICON_LABEL, icon: ChartLine, testId: 'tab-iconic-2'},
];

function setup(props: {showLabels?: boolean; hideLabelOnMobile?: boolean} = {}) {
    render(TabBar, {tabs: TABS, activeTab: 'plain', ...props});
    const tab = (testId: string) => screen.getByTestId(testId);
    /** The label span of a tab, found by the text this file gave it — never by a class. */
    const label = (testId: string, text: string) => within(tab(testId)).getByText(text);
    return {tab, label};
}

describe('TabBar — label visibility and accessible names', () => {
    describe('showLabels={false} (PageToolbar below labelHideTabs)', () => {
        it('keeps the label of a tab without an icon: an icon-less tab is never left empty', () => {
            const {tab, label} = setup({showLabels: false});

            // Precondition: this tab really has nothing else to show.
            expect(tab('tab-plain').querySelector('svg'), 'precondition: the plain tab renders no icon').toBeNull();
            expect(label('tab-plain', PLAIN_LABEL), 'a tab without an icon must keep its label visible — hiding it leaves an empty button').not.toHaveClass('hidden');
        });

        it('hides the label of a tab with an icon and names the button with aria-label', () => {
            const {tab, label} = setup({showLabels: false});

            for (const [testId, text] of [
                ['tab-iconic', ICON_LABEL],
                ['tab-iconic-2', SECOND_ICON_LABEL],
            ] as const) {
                // Presence barrier: the icon is what stays on screen once the label goes.
                expect(tab(testId).querySelector('svg'), `precondition: ${testId} renders its icon`).not.toBeNull();
                expect(label(testId, text), `${testId}: the icon carries the tab, so the label may go`).toHaveClass('hidden');
                expect(tab(testId), `${testId}: a hidden label must be replaced by aria-label={tab.label}`).toHaveAttribute('aria-label', text);
            }
        });
    });

    describe('labels shown', () => {
        it.each([
            ['showLabels={true}', {showLabels: true}],
            ['showLabels undefined (default)', {}],
        ] as const)('%s: every label is visible and the visible text names the tab — no aria-label', (_mode, props) => {
            const {tab, label} = setup(props);

            for (const [testId, text] of [
                ['tab-plain', PLAIN_LABEL],
                ['tab-iconic', ICON_LABEL],
                ['tab-iconic-2', SECOND_ICON_LABEL],
            ] as const) {
                expect(label(testId, text), `${testId}: label shown`).not.toHaveClass('hidden');
                expect(tab(testId), `${testId}: the visible label already names the tab`).not.toHaveAttribute('aria-label');
            }
        });
    });

    describe('hideLabelOnMobile (viewport-driven, no showLabels)', () => {
        it('keeps `hidden sm:inline` on the label of a tab with an icon', () => {
            const {label} = setup({hideLabelOnMobile: true});

            const iconLabel = label('tab-iconic', ICON_LABEL);
            expect(iconLabel).toHaveClass('hidden');
            expect(iconLabel).toHaveClass('sm:inline');
        });

        it('does not hide the label of a tab without an icon (the rule is "never", not "only for showLabels")', () => {
            const {label} = setup({hideLabelOnMobile: true});

            expect(label('tab-plain', PLAIN_LABEL), 'below sm an icon-less tab would be an empty button').not.toHaveClass('hidden');
        });
    });
});
