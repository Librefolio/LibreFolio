// @vitest-environment jsdom
/**
 * EmphasisText and `emphasisLines` (lot E4 of project 71): a catalogue text keeps its line breaks and its marked words,
 * rendered as text nodes — never as HTML.
 */
import {afterEach, describe, expect, it} from 'vitest';
import {cleanup, render} from '$test/component';
import EmphasisText from './EmphasisText.svelte';
import {emphasisLines} from './emphasisText';

afterEach(cleanup);

describe('emphasisLines', () => {
    it('EMPH-01: one line per \\n, marked words strong', () => {
        expect(emphasisLines('This link **no longer works**.\n**Nothing has changed.**')).toEqual([
            [
                {text: 'This link ', strong: false},
                {text: 'no longer works', strong: true},
                {text: '.', strong: false},
            ],
            [{text: 'Nothing has changed.', strong: true}],
        ]);
    });

    it('EMPH-02: a plain text is one line, one piece', () => {
        expect(emphasisLines('Checking the link…')).toEqual([[{text: 'Checking the link…', strong: false}]]);
    });

    it('EMPH-03: a ** without its pair stays as written', () => {
        expect(emphasisLines('a **b** c ** d')).toEqual([
            [
                {text: 'a ', strong: false},
                {text: 'b', strong: true},
                {text: ' c ** d', strong: false},
            ],
        ]);
    });
});

describe('EmphasisText', () => {
    it('EMPH-04: renders blocks and <strong>, and markup in the text stays text', () => {
        const {container} = render(EmphasisText, {text: 'One **<b>two</b>**\nthree <img src=x>'});

        const lines = container.querySelectorAll('[data-line]');
        expect(lines).toHaveLength(2);
        expect(lines[0].querySelector('strong')?.textContent).toBe('<b>two</b>');
        expect(container.querySelector('b'), 'no element made from the text').toBeNull();
        expect(container.querySelector('img')).toBeNull();
        expect(lines[1].textContent).toBe('three <img src=x>');
    });
});
