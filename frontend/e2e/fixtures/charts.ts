/**
 * Chart content assertions.
 *
 * The failure mode this exists for: a test that asserts a chart *container* is
 * visible stays green while ECharts never draws inside it — the semi-donut
 * regression of report 16 (Asse 1) survived exactly that way. Asserting the
 * container is necessary but not sufficient; the canvas and its dimensions are
 * the content.
 *
 * Generalized from `expectOwnershipChartCanvas()` in brokers/broker-sharing.spec.ts
 * (the reference implementation that would have caught that bug).
 */

import {expect, type Page} from '@playwright/test';

/**
 * Assert that the container `testId` holds a rendered chart: the container and
 * its `<canvas>` are visible, and the canvas has non-zero CSS box *and* bitmap
 * size (an `$effect` that mounts the canvas but never draws leaves the bitmap
 * at 0×0 — that is the exact bug shape this catches).
 *
 * Both size checks run under `expect.poll`: ECharts attaches and sizes the
 * canvas asynchronously after mount, so a single read would be a race.
 */
export async function expectChartCanvas(page: Page, testId: string, timeout = 5_000): Promise<void> {
    const container = page.getByTestId(testId);
    await expect(container).toBeVisible({timeout});

    const canvas = container.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout});
    await expect
        .poll(
            async () => {
                const box = await canvas.boundingBox();
                if (!box || box.width <= 0 || box.height <= 0) return 'zero-css-size';

                return canvas.evaluate((node) => {
                    const htmlCanvas = node as HTMLCanvasElement;
                    return htmlCanvas.width > 0 && htmlCanvas.height > 0 ? 'non-zero' : 'zero-bitmap-size';
                });
            },
            {timeout},
        )
        .toBe('non-zero');
}
