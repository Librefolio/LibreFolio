// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi, type Mock} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import SupportActions from './SupportActions.svelte';
import {BUY_ME_A_COFFEE_URL, SOCIAL_SHARE_CONFIG, SOCIAL_SHARE_ORDER, type SocialPlatform} from './supportLinks';

type CoffeeHandler = () => void;
type ShareHandler = (platform: SocialPlatform) => void;

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
