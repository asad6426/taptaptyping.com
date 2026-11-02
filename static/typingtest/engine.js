/*
 * TapTapTyping typing engine. No DOM access, so the same code runs in the
 * browser and under `node --test`. Rules are documented in docs/typing-test/SCORING.md.
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.TypingEngine = factory();
    }
})(typeof self !== 'undefined' ? self : this, function () {
    const SCORING_VERSION = '1';

    function segment(text, locale) {
        const normalized = (text || '').normalize('NFC');
        const segmenter = new Intl.Segmenter(locale, { granularity: 'grapheme' });
        return Array.from(segmenter.segment(normalized), (part) => part.segment);
    }

    /** True if `partial` can still become `unit`, such as e becoming ế or क becoming क्ष. */
    function canBecome(partial, unit) {
        return unit.normalize('NFD').startsWith(partial.normalize('NFD'));
    }

    function round(value) {
        return Math.round(value * 100) / 100;
    }

    class TypingSession {
        /**
         * @param {string} options.target Practice text
         * @param {string} options.locale BCP 47 tag used to split the text into units
         * @param {number} [options.durationSec] Set for a timed test
         * @param {boolean} [options.endOnComplete] End when the text is finished. Defaults to untimed tests only.
         * @param {boolean} [options.allowCorrections] Allow deleting units that are already scored
         * @param {boolean} [options.stopOnError] Do not move past a wrong unit until it is fixed
         * @param {boolean} [options.strictAccuracy] The first wrong unit ends the test
         */
        constructor({
            target,
            locale,
            durationSec = null,
            endOnComplete = durationSec === null,
            allowCorrections = true,
            stopOnError = false,
            strictAccuracy = false,
        }) {
            this.locale = locale;
            this.target = segment(target, locale);
            this.durationSec = durationSec;
            this.endOnComplete = endOnComplete;
            // Stop on Error needs a way to fix the wrong unit
            this.allowCorrections = allowCorrections || stopOnError;
            this.stopOnError = stopOnError;
            this.strictAccuracy = strictAccuracy;
            this.units = [];
            this.settled = 0;
            this.attempts = 0;
            this.correctAttempts = 0;
            this.corrections = 0;
            this.pending = '';
            this.startedAt = null;
            this.endedAt = null;
            this.finished = false;
        }

        /** Add more practice text to a running timed test. */
        extend(text) {
            this.target = this.target.concat(segment(text, this.locale));
        }

        /** Text still being composed by an IME. Never scored, never starts the timer. */
        compose(text) {
            if (!this.finished) this.pending = text || '';
        }

        /** The committed text. The page restores this when input is rejected. */
        text() {
            return this.units.join('');
        }

        /**
         * Replace the committed input with `value`, the full text typed so far.
         * Returns false if a setting rejected it, leaving the session unchanged.
         */
        input(value, now) {
            if (this.finished) return false;
            if (this.expire(now)) return false;

            const units = segment(value, this.locale);
            this.pending = '';
            if (this.startedAt === null && units.length === 0) return true;

            let shared = 0;
            while (shared < units.length && shared < this.units.length && units[shared] === this.units[shared]) {
                shared++;
            }

            if (!this.allowCorrections && shared < this.settled) return false;
            if (this.stopOnError) {
                const wrong = this.units.findIndex((unit, index) => index < this.settled && unit !== this.target[index]);
                if (wrong !== -1 && units.length > wrong + 1) return false;
            }

            if (this.startedAt === null) this.startedAt = now;

            // A cluster that only grew, like क becoming क्, is still being typed.
            const onlyGrew = shared === this.units.length - 1
                && shared < units.length
                && canBecome(this.units[shared], units[shared]);
            if (!onlyGrew) {
                this.corrections += Math.max(0, this.units.length - shared);
            }

            this.units = units;
            this.settled = Math.min(this.settled, shared);
            this.settle(units.length - 1);
            if (units.length > 0 && !this.isPartial(units.length - 1)) {
                this.settle(units.length);
            }

            const hasError = this.units.some((unit, index) => index < this.settled && unit !== this.target[index]);
            if ((this.strictAccuracy && hasError) || (this.endOnComplete && this.isComplete())) {
                this.finish(now);
            }
            return true;
        }

        settle(upTo) {
            for (let i = this.settled; i < upTo; i++) {
                this.attempts++;
                if (this.units[i] === this.target[i]) this.correctAttempts++;
            }
            this.settled = Math.max(this.settled, upTo);
        }

        /** The last typed unit is unfinished if it can still become the target unit. */
        isPartial(index) {
            return index === this.units.length - 1
                && index < this.target.length
                && this.units[index] !== this.target[index]
                && canBecome(this.units[index], this.target[index]);
        }

        isComplete() {
            const last = this.units.length - 1;
            return this.units.length >= this.target.length && !this.isPartial(last);
        }

        /** Ends a timed test whose time is up. Uncommitted IME text is discarded. */
        expire(now) {
            if (this.finished || this.durationSec === null || this.startedAt === null) return this.finished;
            if (now - this.startedAt >= this.durationSec * 1000) {
                this.finish(this.startedAt + this.durationSec * 1000);
            }
            return this.finished;
        }

        finish(now) {
            this.pending = '';
            this.endedAt = now;
            this.finished = true;
        }

        /** Seconds left in a timed test, or null for an untimed test. */
        remaining(now) {
            if (this.durationSec === null) return null;
            if (this.startedAt === null) return this.durationSec;
            const end = this.endedAt === null ? now : this.endedAt;
            return Math.max(0, this.durationSec - (end - this.startedAt) / 1000);
        }

        /** 'correct', 'incorrect', 'partial' or 'untyped' for one target position. */
        state(index) {
            if (index >= this.units.length) return 'untyped';
            if (this.isPartial(index)) return 'partial';
            return this.units[index] === this.target[index] ? 'correct' : 'incorrect';
        }

        results(now) {
            const end = this.endedAt === null ? now : this.endedAt;
            const elapsedMs = this.startedAt === null ? 0 : Math.max(0, end - this.startedAt);
            let correctUnits = 0;
            let incorrectUnits = 0;
            this.units.forEach((unit, index) => {
                const state = this.state(index);
                if (state === 'correct') correctUnits++;
                if (state === 'incorrect') incorrectUnits++;
            });
            const minutes = elapsedMs / 60000;
            const cpm = minutes > 0 ? correctUnits / minutes : 0;
            return {
                scoringVersion: SCORING_VERSION,
                correctUnits,
                incorrectUnits,
                corrections: this.corrections,
                attempts: this.attempts,
                accuracy: this.attempts > 0 ? round((this.correctAttempts / this.attempts) * 100) : 0,
                elapsedSec: round(elapsedMs / 1000),
                cpm: round(cpm),
                wpm: round(cpm / 5),
            };
        }
    }

    function seededRandom(seed) {
        let state = seed >>> 0 || 1;
        return (limit) => {
            state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
            return state % limit;
        };
    }

    /**
     * Beginner uses the shorter half of the list, Advanced the longer half, and
     * Intermediate all of it. Length is measured in text units.
     */
    function filterByDifficulty(words, difficulty, locale) {
        if (difficulty !== 'beginner' && difficulty !== 'advanced') return words;
        const sorted = words
            .map((word, index) => ({ word, index, length: segment(word, locale).length }))
            .sort((a, b) => a.length - b.length || a.index - b.index)
            .map((item) => item.word);
        const middle = Math.ceil(sorted.length / 2);
        return difficulty === 'beginner' ? sorted.slice(0, middle) : sorted.slice(sorted.length - middle);
    }

    /**
     * Builds repeatable practice text from a word list. The same seed always
     * gives the same text, so a result can be checked against it later.
     * Stops at options.maxWords if set, otherwise once minUnits is reached.
     */
    function buildPracticeText(words, joiner, minUnits, seed, locale, options = {}) {
        const { maxWords = null, capitalize = false, numbers = false, comma = '', end = '' } = options;
        const next = seededRandom(seed);
        const pieces = [];
        let units = 0;
        let previous = -1;
        while (maxWords === null ? units < minUnits : pieces.length < maxWords) {
            const position = pieces.length;
            let word;
            if (numbers && position % 5 === 4) {
                word = String(next(1000));
            } else {
                let index = next(words.length);
                if (index === previous) index = (index + 1) % words.length;
                previous = index;
                word = words[index];
            }
            if (capitalize && position % 8 === 0) {
                const [first, ...rest] = segment(word, locale);
                word = first.toLocaleUpperCase(locale) + rest.join('');
            }
            if (end && position % 8 === 7) word += end;
            else if (comma && position % 4 === 3) word += comma;
            pieces.push(word);
            units += segment(word, locale).length + segment(joiner, locale).length;
        }
        return pieces.join(joiner);
    }

    /** The first `count` text units of a text, for languages measured in units. */
    function truncateUnits(text, count, locale) {
        return segment(text, locale).slice(0, count).join('');
    }

    function buildNumbersText(kind, count, seed, digits = '') {
        const next = seededRandom(seed);
        const symbols = ['+', '-', '=', '%', '$', '#', '*', '/'];
        const tokens = [];
        for (let i = 0; i < count; i++) {
            const whole = String(next(10000));
            if (kind === 'decimal') {
                tokens.push(whole + '.' + String(next(100)).padStart(2, '0'));
            } else if (kind === 'mixed') {
                const symbol = symbols[next(symbols.length)];
                tokens.push(i % 2 === 0 ? whole + symbol : symbol + whole);
            } else {
                tokens.push(whole);
            }
        }
        const text = tokens.join(' ');
        if (!digits) return text;
        const native = Array.from(digits);
        return text.replace(/[0-9]/g, (digit) => native[Number(digit)]);
    }

    const CUSTOM_TEXT_MIN = 20;
    const CUSTOM_TEXT_MAX = 10000;
    const CUSTOM_FILE_MAX_BYTES = 100 * 1024;

    /** Applies the Custom Text options. Marks are only removed if the user turns punctuation off. */
    function prepareCustomText(text, options, locale) {
        const { preserveCapitalization = true, preservePunctuation = true, normalizeSpaces = true } = options;
        let result = (text || '').normalize('NFC').replace(/\r\n?/g, '\n');
        if (!preserveCapitalization) result = result.toLocaleLowerCase(locale);
        if (!preservePunctuation) result = result.replace(/[\p{P}\p{S}]/gu, '');
        if (normalizeSpaces) result = result.replace(/[^\S\n]+/g, ' ').replace(/\n{2,}/g, '\n').replace(/ ?\n ?/g, '\n').trim();
        return result;
    }

    /** Returns an error message, or null if the text can be practised. */
    function validateCustomText(text) {
        const length = Array.from(text || '').length;
        if (/\u0000/.test(text || '')) return 'This does not look like a plain text file.';
        if (length < CUSTOM_TEXT_MIN) return 'Enter at least ' + CUSTOM_TEXT_MIN + ' characters.';
        if (length > CUSTOM_TEXT_MAX) return 'Use no more than ' + CUSTOM_TEXT_MAX + ' characters.';
        return null;
    }

    /** Returns an error message, or null if the file can be read as plain text. */
    function validateCustomFile(file) {
        const isText = /\.txt$/i.test(file.name) && (file.type === '' || file.type === 'text/plain');
        if (!isText) return 'Choose a plain text file ending in .txt.';
        if (file.size > CUSTOM_FILE_MAX_BYTES) return 'Choose a file no larger than 100 KB.';
        return null;
    }

    return {
        SCORING_VERSION,
        TypingSession,
        segment,
        filterByDifficulty,
        buildPracticeText,
        truncateUnits,
        buildNumbersText,
        prepareCustomText,
        validateCustomText,
        validateCustomFile,
    };
});
