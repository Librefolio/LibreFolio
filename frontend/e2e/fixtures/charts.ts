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

import {expect, type Locator, type Page} from '@playwright/test';

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

/**
 * Bring up a chart's axis tooltip and wait until `anchor` is on screen.
 *
 * ECharts paints its series into a `<canvas>`, so the tooltip is the *only*
 * place a chart's own numbers and series names reach the DOM. That makes it the
 * only honest way to assert what a chart drew: the container, the canvas and its
 * dimensions are identical whether the series are right, wrong or absent.
 *
 * This is not coordinate-hunting for one slice. `trigger: 'axis'` means every
 * point inside the plot area produces a tooltip for its column, so the move
 * lands on *a* valid bucket by construction — unlike a treemap tile or a bar,
 * which would need pixel arithmetic and is exactly what the suite refuses to do.
 *
 * The move is re-emitted under `expect.poll` because a `mousemove` delivered
 * while the chart is still animating is simply dropped: ECharts has no retry, so
 * a single move is a bet on timing, and a lost one reads as "the chart has no
 * tooltip". The loop ends on a real assertion, so a tooltip that never appears
 * fails here rather than three assertions later.
 *
 * `minimum` is what makes the loop safe across a mode switch. ECharts repaints
 * the tooltip on the *next* pointer event, so a tooltip raised in one submode can
 * still be on screen in the next one — and an anchor that only asks for "at least
 * one match" is happily satisfied by the previous submode's rows. Asking for the
 * number of rows the new content must have keeps the pointer moving until the
 * chart has actually caught up.
 *
 * The pointer is deliberately left where it is: `hideDelay` only starts once it
 * leaves the plot, so the caller can keep asserting on the tooltip it just
 * raised.
 */
export async function showChartTooltip(page: Page, chart: Locator, anchor: Locator, timeout = 10_000, minimum = 1): Promise<void> {
    const canvas = chart.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout});

    const box = await canvas.boundingBox();
    if (!box) throw new Error('the chart canvas reports no bounding box — it never laid out');

    // 55%/50% is the middle of the plot: clear of the y-axis gutter on the left
    // and of the dataZoom strip at the bottom, whichever bucket that lands on.
    // Offsets are element-relative and driven through `hover()` rather than
    // absolute `mouse.move()` coordinates, because the dashboard is taller than
    // the viewport: a box read before the page settled points at a spot the
    // pointer can never reach, and the resulting "no tooltip" reads exactly like
    // "the chart has nothing to say".
    let jitter = 0;

    await expect
        .poll(
            async () => {
                // One pixel of movement per attempt: two identical positions are
                // coalesced by the browser and the second never reaches the chart.
                jitter = jitter === 0 ? 1 : 0;
                await canvas.hover({position: {x: box.width * 0.55 + jitter, y: box.height * 0.5}});
                return anchor.count();
            },
            {timeout},
        )
        .toBeGreaterThanOrEqual(minimum);
}
