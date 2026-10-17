// @vitest-environment jsdom
import {beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import SupportActions from './SupportActions.svelte';
import {BUY_ME_A_COFFEE_URL, SOCIAL_SHARE_CONFIG, SOCIAL_SHARE_ORDER, type SocialPlatform} from './supportLinks';

type CoffeeHandler = () => void;
type ShareHandler = (platform: SocialPlatform) => void;

/** A self-hosted instance's answer to `GET /system/instance`: the only answer that shows the coffee (F05, lot A9). */
const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};

function mount(
    props: Partial<{
        onCoffeeClick: CoffeeHandler;
        coffeeTestId: string;
        onShare: ShareHandler;
        class: string;
    }> = {},
) {
    const onCoffeeClick: Mock<CoffeeHandler> = vi.fn();
    const onShare: Mock<ShareHandler> = vi.fn();
    return {
        onCoffeeClick,
        onShare,
        ...render(SupportActions, {onCoffeeClick, onShare, ...props}),
    };
}

beforeAll(async () => {
    await setupI18n();
});

// F05 (lot A9): the coffee is drawn only once the server has answered self-hosted. These cases pin the component as a
// self-hosted instance draws it — before the answer and on a managed instance it is SupportActions.managed.test.ts —,
// so each starts from that answer: the real store, answered through its own `load`, with no request and no module mock.
beforeEach(async () => {
    await instanceConfig.load({force: true, fetchConfig: () => Promise.resolve(SELFHOSTED)});
    expect(instanceConfig.loaded, 'precondition: the instance configuration has loaded').toBe(true);
    expect(instanceConfig.config.profile, 'precondition: a self-hosted instance').toBe('selfhosted');
});

describe('SupportActions — support links', () => {
    it('keeps the coffee action on the public donation page and preserves the default test hook', () => {
        mount();
        const coffee = screen.getByTestId('support-coffee');

        expect(coffee).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        expect(coffee).toHaveAttribute('target', '_blank');
        expect(coffee).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('lets the coffee hook be overridden without changing the destination', () => {
        mount({coffeeTestId: 'donation-popup-donate'});

        expect(screen.queryByTestId('support-coffee')).toBeNull();
        expect(screen.getByTestId('donation-popup-donate')).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
    });

    it('renders icon-only share buttons in config order without tooltip popovers and keeps them mobile-wrap friendly', () => {
        mount();
        const buttons = SOCIAL_SHARE_ORDER.map((platform) => screen.getByTestId(`support-share-${platform}`));
        const shareRow = buttons[0].parentElement;

        expect(buttons.map((button) => button.getAttribute('data-testid'))).toEqual(SOCIAL_SHARE_ORDER.map((platform) => `support-share-${platform}`));
        expect(shareRow?.className).toContain('flex-wrap');

        for (const platform of SOCIAL_SHARE_ORDER) {
            const button = screen.getByTestId(`support-share-${platform}`);

            expect(button.tagName).toBe('BUTTON');
            expect(button).toHaveAttribute('type', 'button');
            expect(button.textContent?.trim()).toBe('');
            expect(button).not.toHaveAttribute('title');
            expect(button.getAttribute('aria-label')).toContain(SOCIAL_SHARE_CONFIG[platform].label);
            expect(button.className).toContain(SOCIAL_SHARE_CONFIG[platform].brandClass);
            expect(button.querySelector(`[data-social-icon="${platform}"]`)).not.toBeNull();
        }
    });
});

describe('SupportActions — callbacks', () => {
    it('calls only the coffee callback for the coffee action', async () => {
        const {onCoffeeClick, onShare} = mount();

        await fireEvent.click(screen.getByTestId('support-coffee'));

        expect(onCoffeeClick).toHaveBeenCalledTimes(1);
        expect(onShare).not.toHaveBeenCalled();
    });

    it('reports each share platform only through the unified onShare callback', async () => {
        const {onShare, onCoffeeClick} = mount();

        for (const platform of SOCIAL_SHARE_ORDER) {
            await fireEvent.click(screen.getByTestId(`support-share-${platform}`));
        }

        expect(onShare.mock.calls).toEqual(SOCIAL_SHARE_ORDER.map((platform) => [platform]));
        expect(onCoffeeClick).not.toHaveBeenCalled();
    });
});
