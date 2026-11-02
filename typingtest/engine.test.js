// Run with: node --test typingtest/engine.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
    TypingSession, segment, filterByDifficulty, buildPracticeText, truncateUnits,
    buildNumbersText, prepareCustomText, validateCustomText, validateCustomFile,
} = require('../static/typingtest/engine.js');

const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures_scoring.json'), 'utf8')).languages;

function typeUnits(session, units, startMs = 0, stepMs = 100) {
    let value = '';
    units.forEach((unit, index) => {
        value += unit;
        session.input(value, startMs + index * stepMs);
    });
    return value;
}

for (const [language, { locale, units }] of Object.entries(fixtures)) {
    test(`${language}: text splits into the expected units`, () => {
        assert.deepEqual(segment(units.join(''), locale), units);
    });

    test(`${language}: perfect run scores every unit`, () => {
        const session = new TypingSession({ target: units.join(''), locale });
        typeUnits(session, units);
        const result = session.results(1e9);
        assert.equal(session.finished, true);
        assert.equal(result.correctUnits, units.length);
        assert.equal(result.incorrectUnits, 0);
        assert.equal(result.corrections, 0);
        assert.equal(result.accuracy, 100);
        const seconds = (units.length - 1) / 10;
        assert.equal(result.elapsedSec, Math.round(seconds * 100) / 100);
    });

    test(`${language}: a corrected mistake lowers accuracy but not correct units`, () => {
        const session = new TypingSession({ target: units.join('') + ' extra', locale });
        session.input(units[0], 0);
        session.input(units[0] + '#', 100);
        assert.equal(session.state(1), 'incorrect');
        session.input(units[0], 200);
        session.input(units[0] + units[1], 300);
        const result = session.results(300);
        assert.equal(result.correctUnits, 2);
        assert.equal(result.incorrectUnits, 0);
        assert.equal(result.corrections, 1);
        assert.equal(result.attempts, 3);
        assert.equal(result.accuracy, 66.67);
    });
}

test('the five-unit calculation matches the documented example', () => {
    const target = 'a'.repeat(300);
    const session = new TypingSession({ target, locale: 'en', durationSec: 60 });
    session.input('a'.repeat(1), 0);
    session.input('a'.repeat(250), 30000);
    assert.equal(session.expire(60000), true);
    const result = session.results(60000);
    assert.equal(result.elapsedSec, 60);
    assert.equal(result.correctUnits, 250);
    assert.equal(result.cpm, 250);
    assert.equal(result.wpm, 50);
});

test('the timer does not start until text is committed', () => {
    const session = new TypingSession({ target: 'hello', locale: 'en', durationSec: 60 });
    assert.equal(session.remaining(99999), 60);
    session.input('', 1000);
    assert.equal(session.startedAt, null);
    session.compose('こ');
    assert.equal(session.startedAt, null);
    session.input('h', 5000);
    assert.equal(session.startedAt, 5000);
});

test('unfinished IME text is not scored and does not count as an error', () => {
    const session = new TypingSession({ target: 'ことば', locale: 'ja' });
    session.compose('k');
    session.compose('こ');
    assert.equal(session.state(0), 'untyped');
    assert.equal(session.results(100).attempts, 0);
    session.input('こ', 200);
    assert.equal(session.state(0), 'correct');
    assert.equal(session.pending, '');
});

test('Korean syllables committed one at a time score as one unit each', () => {
    const session = new TypingSession({ target: '언어', locale: 'ko' });
    session.compose('ㅇ');
    session.compose('어');
    session.compose('언');
    session.input('언', 100);
    session.compose('ㅇ');
    session.compose('어');
    session.input('언어', 200);
    assert.equal(session.finished, true);
    assert.equal(session.results(200).correctUnits, 2);
    assert.equal(session.results(200).accuracy, 100);
});

test('Text still being composed when time runs out is discarded', () => {
    const session = new TypingSession({ target: 'ことば', locale: 'ja', durationSec: 15 });
    session.input('こ', 0);
    session.compose('と');
    assert.equal(session.expire(15000), true);
    assert.equal(session.pending, '');
    assert.equal(session.results(15000).correctUnits, 1);
});

test('Input after the time is up is ignored', () => {
    const session = new TypingSession({ target: 'abcdef', locale: 'en', durationSec: 15 });
    session.input('a', 0);
    session.input('ab', 20000);
    assert.equal(session.finished, true);
    const result = session.results(20000);
    assert.equal(result.correctUnits, 1);
    assert.equal(result.elapsedSec, 15);
});

test('A long gap such as a tab switch does not extend the timer', () => {
    const session = new TypingSession({ target: 'abcdef', locale: 'en', durationSec: 60 });
    session.input('a', 0);
    assert.equal(session.remaining(45000), 15);
    assert.equal(session.expire(90000), true);
    assert.equal(session.results(90000).elapsedSec, 60);
});

test('A Hindi cluster being built is partial, not an error', () => {
    const session = new TypingSession({ target: 'क्ष', locale: 'hi' });
    session.input('क', 0);
    assert.equal(session.state(0), 'partial');
    assert.equal(session.results(0).attempts, 0);
    session.input('क्', 100);
    assert.equal(session.state(0), 'partial');
    assert.equal(session.corrections, 0);
    session.input('क्ष', 200);
    assert.equal(session.state(0), 'correct');
    assert.equal(session.finished, true);
    assert.equal(session.results(200).accuracy, 100);
});

test('Decomposed and composed accents compare equal', () => {
    const session = new TypingSession({ target: 'école', locale: 'fr' });
    session.input('é', 0);
    assert.equal(session.state(0), 'correct');
});

test('Accents and vowel marks are not ignored', () => {
    const session = new TypingSession({ target: 'école', locale: 'fr' });
    session.input('ex', 0);
    assert.equal(session.state(0), 'incorrect');
    const bengali = new TypingSession({ target: 'মি', locale: 'bn' });
    bengali.input('মা', 0);
    assert.equal(bengali.state(0), 'incorrect');
});

test('Arabic with Latin digits and punctuation keeps logical order', () => {
    const units = segment('لغة 12, ab.', 'ar');
    assert.deepEqual(units.slice(0, 7), ['ل', 'غ', 'ة', ' ', '1', '2', ',']);
    const session = new TypingSession({ target: 'لغة 12', locale: 'ar' });
    typeUnits(session, segment('لغة 12', 'ar'));
    assert.equal(session.results(1e9).correctUnits, 6);
});

test('Practice text is repeatable for a seed and long enough', () => {
    const words = ['one', 'two', 'three'];
    const first = buildPracticeText(words, ' ', 200, 42, 'en');
    assert.equal(first, buildPracticeText(words, ' ', 200, 42, 'en'));
    assert.notEqual(first, buildPracticeText(words, ' ', 200, 43, 'en'));
    assert.ok(segment(first, 'en').length >= 200);
});

test('Text with no spaces between words stays joined', () => {
    const text = buildPracticeText(['ひと', 'みず'], '', 20, 7, 'ja');
    assert.equal(text.includes(' '), false);
});

test('A finished test ignores further input', () => {
    const session = new TypingSession({ target: 'ab', locale: 'en' });
    session.input('a', 0);
    session.input('ab', 100);
    session.input('abc', 200);
    assert.equal(session.units.length, 2);
    assert.equal(session.results(500).elapsedSec, 0.1);
});

test('Without corrections, scored units cannot be deleted', () => {
    const session = new TypingSession({ target: 'abcdef', locale: 'en', allowCorrections: false });
    session.input('ab', 0);
    assert.equal(session.input('a', 100), false);
    assert.equal(session.text(), 'ab');
    assert.equal(session.corrections, 0);
    assert.equal(session.input('abc', 200), true);
});

test('Stop on Error blocks moving on until the unit is fixed', () => {
    const session = new TypingSession({ target: 'abc', locale: 'en', stopOnError: true, allowCorrections: false });
    session.input('x', 0);
    assert.equal(session.state(0), 'incorrect');
    assert.equal(session.input('xb', 100), false);
    assert.equal(session.text(), 'x');
    assert.equal(session.input('', 200), true);
    assert.equal(session.input('a', 300), true);
    assert.equal(session.input('ab', 400), true);
    assert.equal(session.results(400).corrections, 1);
});

test('Strict Accuracy ends the test at the first wrong unit', () => {
    const session = new TypingSession({ target: 'abcdef', locale: 'en', durationSec: 60, strictAccuracy: true });
    session.input('ab', 0);
    assert.equal(session.finished, false);
    session.input('abx', 1000);
    assert.equal(session.finished, true);
    assert.equal(session.results(9000).elapsedSec, 1);
});

test('A timed test can end when its text is complete', () => {
    const session = new TypingSession({ target: 'ab', locale: 'en', durationSec: 60, endOnComplete: true });
    session.input('a', 0);
    session.input('ab', 2000);
    assert.equal(session.finished, true);
    assert.equal(session.results(2000).elapsedSec, 2);
});

test('A timed test keeps running past its text unless told to end', () => {
    const session = new TypingSession({ target: 'ab', locale: 'en', durationSec: 60 });
    session.input('ab', 0);
    assert.equal(session.finished, false);
    session.extend(' cd');
    session.input('ab c', 100);
    assert.equal(session.state(3), 'correct');
});

test('Difficulty picks shorter or longer words', () => {
    const words = ['a', 'bbb', 'cc', 'dddd'];
    assert.deepEqual(filterByDifficulty(words, 'beginner', 'en'), ['a', 'cc']);
    assert.deepEqual(filterByDifficulty(words, 'advanced', 'en'), ['bbb', 'dddd']);
    assert.deepEqual(filterByDifficulty(words, 'intermediate', 'en'), words);
});

test('Word count produces exactly that many words', () => {
    const text = buildPracticeText(['one', 'two', 'three'], ' ', 0, 5, 'en', { maxWords: 25 });
    assert.equal(text.split(' ').length, 25);
});

test('Unit-based length truncates on a text unit, not inside one', () => {
    assert.equal(truncateUnits('น้ำดี', 1, 'th'), 'น้ำ');
    assert.equal(truncateUnits('क्षेत्र', 1, 'hi'), segment('क्षेत्र', 'hi')[0]);
});

test('Content options add capitals, punctuation and numbers', () => {
    const text = buildPracticeText(['one', 'two', 'three'], ' ', 200, 9, 'en', { capitalize: true, numbers: true, comma: ',', end: '.' });
    assert.match(text, /^[A-Z]/);
    assert.match(text, /,/);
    assert.match(text, /\./);
    assert.match(text, /\d/);
});

test('Capitalizing follows the language rules', () => {
    const text = buildPracticeText(['ismim'], ' ', 1, 9, 'tr', { capitalize: true });
    assert.equal(text.startsWith('İ'), true);
});

test('Number kinds have the documented shapes', () => {
    assert.match(buildNumbersText('whole', 10, 1), /^\d+( \d+){9}$/);
    assert.match(buildNumbersText('decimal', 10, 1), /^\d+\.\d\d( \d+\.\d\d){9}$/);
    assert.match(buildNumbersText('mixed', 10, 1), /[-+=%$#*/]/);
    assert.equal(buildNumbersText('mixed', 10, 1), buildNumbersText('mixed', 10, 1));
});

test('Custom text options keep what the user asked to keep', () => {
    const raw = 'Hello,   World!\r\n\r\n  Next  line';
    assert.equal(prepareCustomText(raw, {}, 'en'), 'Hello, World!\nNext line');
    assert.equal(prepareCustomText(raw, { preserveCapitalization: false }, 'en'), 'hello, world!\nnext line');
    assert.equal(prepareCustomText(raw, { preservePunctuation: false }, 'en'), 'Hello World\nNext line');
    assert.equal(prepareCustomText('a  b', { normalizeSpaces: false }, 'en'), 'a  b');
});

test('Removing punctuation keeps accents and vowel signs', () => {
    assert.equal(prepareCustomText('আমি, বাংলা।', { preservePunctuation: false }, 'bn'), 'আমি বাংলা');
    assert.equal(prepareCustomText('tiếng, école.', { preservePunctuation: false }, 'vi'), 'tiếng école');
});

test('Custom text and files are validated', () => {
    assert.match(validateCustomText('short'), /at least/);
    assert.match(validateCustomText('x'.repeat(10001)), /no more than/);
    assert.match(validateCustomText('a\u0000'.repeat(20)), /plain text/);
    assert.equal(validateCustomText('x'.repeat(20)), null);
    assert.equal(validateCustomFile({ name: 'a.txt', type: 'text/plain', size: 10 }), null);
    assert.match(validateCustomFile({ name: 'a.html', type: 'text/html', size: 10 }), /plain text/);
    assert.match(validateCustomFile({ name: 'a.txt', type: 'text/html', size: 10 }), /plain text/);
    assert.match(validateCustomFile({ name: 'a.txt', type: 'text/plain', size: 200000 }), /100 KB/);
});

test('Numbers can use a language\'s own digits', () => {
    const text = buildNumbersText('decimal', 5, 3, '০১২৩৪৫৬৭৮৯');
    assert.match(text, /^[০-৯]+\.[০-৯]{2}( [০-৯]+\.[০-৯]{2}){4}$/);
    assert.equal(/[0-9]/.test(text), false);
    const session = new TypingSession({ target: '১২', locale: 'bn' });
    session.input('১', 0);
    session.input('১২', 100);
    assert.equal(session.results(100).correctUnits, 2);
});

test('Vietnamese Telex can rewrite a letter without counting as a mistake', () => {
    const session = new TypingSession({ target: 'tiếng', locale: 'vi' });
    session.input('ti', 0);
    session.input('tie', 100);
    assert.equal(session.state(2), 'partial');
    session.input('tiê', 200);
    assert.equal(session.state(2), 'partial');
    session.input('tiế', 300);
    assert.equal(session.state(2), 'correct');
    const result = session.results(300);
    assert.equal(result.corrections, 0);
    assert.equal(result.accuracy, 100);
});

test('A base letter left without its accent is still a mistake', () => {
    const session = new TypingSession({ target: 'école', locale: 'fr' });
    session.input('e', 0);
    assert.equal(session.state(0), 'partial');
    session.input('ec', 100);
    assert.equal(session.state(0), 'incorrect');
    assert.equal(session.results(100).correctUnits, 1);
    assert.equal(session.results(100).accuracy, 50);
});
