/* Connects the typing engine to the language test page. */
(function () {
    const config = JSON.parse(document.getElementById('typingConfig').textContent);
    const Engine = window.TypingEngine;
    const { TypingSession, segment } = Engine;

    const WINDOW_UNITS = 240;
    const UNITS_PER_SECOND = 22; // Enough text for the fastest speed the site accepts
    const NUMBER_TOKENS = 40;
    const MODE_LABELS = { time: 'Time', words: 'Words', paragraph: 'Paragraph', custom: 'Custom Text', numbers: 'Numbers' };
    const PREFS_KEY = 'typingTestPrefs';
    const DEFAULT_PREFS = {
        difficulty: 'intermediate',
        punctuation: false,
        numbers: false,
        capitalization: false,
        allowCorrections: true,
        stopOnError: false,
        strictAccuracy: false,
        theme: 'system',
        fontSize: 'medium',
        lineSpacing: 'normal',
        caret: 'box',
        reducedMotion: false,
        digitStyle: 'western',
    };

    const $ = (id) => document.getElementById(id);
    const page = $('ttPage');
    const display = $('practiceText');
    const input = $('typingInput');
    const timer = $('timerValue');
    const statusLine = $('typingStatus');
    const results = $('typingResults');
    const optionError = $('optionError');

    let prefs = loadPrefs();
    const pageQuery = new URLSearchParams(window.location.search);
    if (['beginner', 'intermediate', 'advanced'].includes(pageQuery.get('difficulty'))) {
        prefs.difficulty = pageQuery.get('difficulty');
    }
    let session = null;
    let composing = false;
    let tick = null;
    let durationSec = config.mode === 'time' ? config.durationSec : null;
    const requestedDuration = Number(pageQuery.get('duration'));
    if (config.mode === 'time' && Number.isInteger(requestedDuration)
        && requestedDuration >= config.customMin && requestedDuration <= config.customMax) {
        durationSec = requestedDuration;
    }
    let seed = 0;
    let lastResult = null;
    let customBase = '';
    let rankedToken = null;
    let rankedStart = null;
    let generation = 0;
    let pasteAttempted = false;
    let usedComposition = false;
    let completed = false;

    function loadPrefs() {
        let saved = {};
        try {
            saved = JSON.parse(localStorage.getItem(PREFS_KEY) || '{}');
        } catch (error) {
            // Fall back to the defaults
        }
        return { ...DEFAULT_PREFS, ...saved, ...config.serverPreferences };
    }

    function savePrefs() {
        try {
            localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
        } catch (error) {
            // The settings still apply to this page
        }
        if (config.signedIn) {
            postJson('/typing-test/api/preferences', prefs).catch(() => {});
        }
    }

    function csrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify(body),
        });
    }

    /** Analytics carries only these settings, never typed text. */
    function track(event, extra = {}) {
        if (navigator.globalPrivacyControl || typeof window.gtag !== 'function') return;
        window.gtag('event', event, {
            language: config.language,
            mode: config.mode,
            duration: durationSec,
            difficulty: prefs.difficulty,
            deviceCategory: isMobileInput() ? 'mobile' : 'desktop',
            inputCategory: inputCategory(),
            scoringVersion: config.scoringVersion,
            ...extra,
        });
    }

    function isMobileInput() {
        return navigator.maxTouchPoints > 0 && window.matchMedia('(pointer: coarse)').matches;
    }

    function inputCategory() {
        if (isMobileInput()) return 'mobile';
        return usedComposition ? 'ime' : 'desktop';
    }

    /** Ranked tests need a server session, standard settings and a fixed length. */
    function canRank() {
        if (!config.signedIn || !['time', 'words', 'paragraph', 'numbers'].includes(config.mode)) return false;
        const standard = prefs.allowCorrections && !prefs.stopOnError && !prefs.strictAccuracy
            && !prefs.punctuation && !prefs.numbers && !prefs.capitalization;
        if (!standard) return false;
        if (config.mode === 'time') return config.rankedDurations.includes(durationSec);
        if (config.mode === 'words') return checked('wordCount') !== 'custom';
        return true;
    }

    function textSize() {
        if (config.mode === 'words') {
            const count = checked('wordCount');
            return count === 'custom' ? 'custom-' + $('customWordCount').value : count;
        }
        if (config.mode === 'paragraph') return { 1: 'short', 2: 'medium', 4: 'long' }[checked('paragraphSize')];
        if (config.mode === 'numbers') return checked('numberKind') + '-' + (checked('digitStyle') || 'western');
        return '';
    }

    /** Saves the result for signed-in users. A failure never loses the result on screen. */
    async function saveResult(result) {
        const note = $('resultSaveNote');
        $('resultBest').textContent = '-';
        if (!config.signedIn) {
            note.textContent = 'This result stays in your browser. Sign in to save your history and personal bests.';
            return;
        }
        if (result.elapsedSec <= 0) {
            note.textContent = 'This result was too short to save.';
            return;
        }
        note.textContent = 'Saving your result...';
        try {
            if (rankedStart) await rankedStart;
            const response = await postJson('/typing-test/api/results', {
                language: config.language,
                mode: config.mode,
                durationSec: session.durationSec === null ? null : session.durationSec,
                textSize: textSize(),
                difficulty: config.mode === 'time' || config.mode === 'words' ? prefs.difficulty : '',
                contentVersion: config.contentVersion,
                inputCategory: inputCategory(),
                pasteAttempted,
                ...result,
                ...(rankedToken ? { sessionToken: rankedToken, typedText: session.text() } : {}),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                note.textContent = data.error || 'This result could not be saved.';
                return;
            }
            $('resultBest').textContent = data.personalBest + ' WPM';
            if (rankedToken) {
                // The server's calculation is the official result
                $('resultSpeed').textContent = data.wpm;
                $('resultCpm').textContent = data.cpm;
            }
            $('resultEligibility').textContent = data.underReview ? 'Under review' : (data.ranked ? 'Ranked' : 'Not ranked');
            const saved = data.isNewBest ? 'New personal best! Saved to your progress.' : 'Saved to your progress.';
            note.textContent = data.ranked ? saved : saved + ' ' + data.reason;
        } catch (error) {
            note.textContent = 'You seem to be offline, so this result was not saved.';
        }
    }

    function now() {
        return performance.now();
    }

    function formatTime(seconds) {
        const whole = Math.ceil(seconds);
        return Math.floor(whole / 60) + ':' + String(whole % 60).padStart(2, '0');
    }

    function checked(name) {
        const element = document.querySelector('input[name="' + name + '"]:checked');
        return element ? element.value : null;
    }

    function contentOptions() {
        return {
            capitalize: prefs.capitalization && config.cased,
            numbers: prefs.numbers,
            comma: prefs.punctuation ? config.comma : '',
            end: prefs.punctuation ? config.end : '',
        };
    }

    /** The practice text for the current mode, or null with an error shown. */
    function buildText() {
        optionError.textContent = '';
        const words = Engine.filterByDifficulty(config.words, prefs.difficulty, config.locale);
        const options = contentOptions();

        if (config.mode === 'time') {
            return Engine.buildPracticeText(words, config.joiner, durationSec * UNITS_PER_SECOND, seed, config.locale, options);
        }
        if (config.mode === 'words') {
            let count = checked('wordCount');
            if (count === 'custom') {
                count = Number($('customWordCount').value);
                if (!Number.isInteger(count) || count < 5 || count > 500) {
                    optionError.textContent = 'Enter a whole number from 5 to 500.';
                    return null;
                }
            } else {
                count = Number(count);
            }
            if (config.wordBoundary === 'spaces') {
                return Engine.buildPracticeText(words, config.joiner, 0, seed, config.locale, { ...options, maxWords: count });
            }
            return Engine.truncateUnits(Engine.buildPracticeText(words, config.joiner, count, seed, config.locale, options), count, config.locale);
        }
        if (config.mode === 'paragraph') {
            return config.paragraphs.slice(0, Number(checked('paragraphSize'))).join(config.wordBoundary === 'spaces' ? ' ' : '');
        }
        if (config.mode === 'numbers') {
            return Engine.buildNumbersText(checked('numberKind'), NUMBER_TOKENS, seed, checked('digitStyle') === 'native' ? config.digits : '');
        }
        return null;
    }

    function startSession(text, options = {}) {
        pasteAttempted = false;
        usedComposition = false;
        completed = false;
        rankedStart = null;
        clearInterval(tick);
        tick = null;
        composing = false;
        session = new TypingSession({
            target: text,
            locale: config.locale,
            durationSec,
            allowCorrections: prefs.allowCorrections,
            stopOnError: prefs.stopOnError,
            strictAccuracy: prefs.strictAccuracy,
            ...options,
        });
        input.value = '';
        input.disabled = false;
        results.hidden = true;
        lockScoringSettings(false);
        statusLine.textContent = 'Start typing to begin. The timer starts with your first character.';
        render();
        updateStats();
        input.focus({ preventScroll: true });
    }

    /** Starts a test. Keeps the same text if keepText is set, otherwise makes new text. */
    function newTest(keepText = false) {
        if (!keepText) seed = (Math.random() * 0xffffffff) >>> 0;
        if (config.mode === 'custom') {
            startCustom();
            return;
        }
        const text = buildText();
        if (text === null) return;
        const current = ++generation;
        rankedToken = null;
        if (!canRank()) {
            startSession(text);
            track('test_restarted');
            return;
        }
        input.disabled = true;
        statusLine.textContent = 'Preparing your test...';
        postJson('/typing-test/api/sessions', {
            language: config.language,
            mode: config.mode,
            durationSec: config.mode === 'time' ? durationSec : null,
            textSize: textSize(),
            difficulty: prefs.difficulty,
        }).then((response) => (response.ok ? response.json() : Promise.reject(new Error('session')))).then((data) => {
            if (current !== generation) return;
            rankedToken = data.token;
            startSession(data.target);
        }).catch(() => {
            if (current !== generation) return;
            // The test still works when the server cannot be reached, but it cannot be ranked
            startSession(text);
            statusLine.textContent = 'Could not reach the server, so this test will not be ranked. Start typing to begin.';
        });
    }

    function render() {
        const position = session.units.length;
        const start = Math.max(0, Math.floor(position / WINDOW_UNITS) * WINDOW_UNITS - 20);
        const end = Math.min(session.target.length, start + WINDOW_UNITS + 60);
        const fragment = document.createDocumentFragment();
        for (let i = start; i < end; i++) {
            const span = document.createElement('span');
            span.className = 'unit ' + session.state(i);
            if (i === position) span.classList.add('current');
            span.textContent = session.target[i];
            fragment.appendChild(span);
        }
        display.replaceChildren(fragment);
        const current = display.querySelector('.current');
        if (current) current.scrollIntoView({ block: 'nearest' });
    }

    function updateStats() {
        const time = now();
        if (session.durationSec !== null) {
            $('timerLabel').textContent = 'Time left';
            timer.textContent = formatTime(session.remaining(time));
        } else {
            $('timerLabel').textContent = 'Progress';
            const done = session.target.length > 0 ? Math.min(100, Math.round((session.units.length / session.target.length) * 100)) : 0;
            timer.textContent = done + '%';
        }
        const live = session.results(time);
        $('liveSpeed').textContent = String(Math.round(live.wpm));
        $('liveAccuracy').textContent = live.attempts > 0 ? Math.round(live.accuracy) + '%' : '-';
    }

    function lockScoringSettings(locked) {
        document.querySelectorAll('[data-scoring]').forEach((group) => { group.disabled = locked; });
        $('settingsLocked').hidden = !locked;
        document.querySelectorAll('#testOptions input, #testOptions button, #testOptions textarea').forEach((element) => {
            element.disabled = locked;
        });
    }

    function startTicking() {
        if (tick !== null || session.durationSec === null) return;
        tick = setInterval(() => {
            if (session.expire(now())) showResults();
            else updateStats();
        }, 200);
    }

    function commit() {
        // An IME may leave the Enter that confirmed it behind
        if (input.value.endsWith('\n') && session.target[segment(input.value, config.locale).length - 1] !== '\n') {
            input.value = input.value.slice(0, -1);
        }
        const accepted = session.input(input.value, now());
        if (!accepted && !session.finished) {
            input.value = session.text();
            statusLine.textContent = prefs.allowCorrections || prefs.stopOnError
                ? 'Fix the marked mistake to continue.'
                : 'Corrections are turned off in this test.';
            return;
        }
        if (session.startedAt !== null) {
            if (!rankedStart && rankedToken) {
                rankedStart = postJson('/typing-test/api/sessions/' + rankedToken + '/start', {}).catch(() => {});
                track('test_started');
            } else if (!rankedStart && !rankedToken) {
                rankedStart = Promise.resolve();
                track('test_started');
            }
            lockScoringSettings(true);
            startTicking();
            if (accepted) statusLine.textContent = '';
        }
        if (session.finished) {
            showResults();
            return;
        }
        // Repeat Text Until Timer Ends, and a safety margin for timed tests
        if (!rankedToken && session.durationSec !== null && !session.endOnComplete && session.target.length - session.units.length < 50) {
            session.extend((config.mode === 'custom' ? '\n' + customBase : config.joiner + buildText()));
        }
        render();
        updateStats();
    }

    function showResults() {
        clearInterval(tick);
        tick = null;
        input.disabled = true;
        lockScoringSettings(false);
        const result = session.results(now());
        lastResult = result;
        const set = (id, value) => { $(id).textContent = value; };
        set('resultSpeed', result.wpm);
        set('resultCpm', result.cpm);
        set('resultAccuracy', result.accuracy + '%');
        set('resultElapsed', result.elapsedSec + ' s');
        set('resultCorrect', result.correctUnits);
        set('resultIncorrect', result.incorrectUnits);
        set('resultCorrections', result.corrections);
        set('resultMode', MODE_LABELS[config.mode]);
        set('resultDuration', session.durationSec === null ? 'Until finished' : formatTime(session.durationSec));
        set('resultDifficulty', config.mode === 'time' || config.mode === 'words'
            ? prefs.difficulty.charAt(0).toUpperCase() + prefs.difficulty.slice(1)
            : 'Not applicable');
        render();
        updateStats();
        results.hidden = false;
        statusLine.textContent = 'Test finished. Speed ' + result.wpm + ' WPM, accuracy ' + result.accuracy + ' percent.';
        $('tryAgain').focus({ preventScroll: true });
        completed = true;
        track('test_completed');
        saveResult(result);
    }

    // ---- Custom text ----

    function customOptions() {
        return {
            preserveCapitalization: $('customCaps').checked,
            preservePunctuation: $('customPunct').checked,
            normalizeSpaces: $('customSpaces').checked,
        };
    }

    function updateCustomCount() {
        $('customCount').textContent = Array.from($('customSource').value).length + ' characters';
    }

    function startCustom() {
        optionError.textContent = '';
        const text = Engine.prepareCustomText($('customSource').value, customOptions(), config.locale);
        const error = Engine.validateCustomText(text);
        if (error) {
            optionError.textContent = error;
            $('customSource').focus();
            return;
        }
        const timed = checked('customFinish') === 'timed';
        durationSec = null;
        if (timed) {
            const seconds = Number($('customTimedSeconds').value);
            if (!Number.isInteger(seconds) || seconds < config.customMin || seconds > config.customMax) {
                optionError.textContent = 'Enter a whole number from ' + config.customMin + ' to ' + config.customMax + ' seconds.';
                $('customTimedSeconds').focus();
                return;
            }
            durationSec = seconds;
        }
        customBase = text;
        const repeat = timed && $('customRepeat').checked;
        startSession(text, { endOnComplete: !repeat });
    }

    function setUpCustomMode() {
        const source = $('customSource');
        source.addEventListener('input', updateCustomCount);
        $('startCustom').addEventListener('click', startCustom);
        $('clearText').addEventListener('click', () => {
            source.value = '';
            updateCustomCount();
            optionError.textContent = '';
            source.focus();
        });
        $('pasteText').addEventListener('click', async () => {
            try {
                source.value = await navigator.clipboard.readText();
                updateCustomCount();
            } catch (error) {
                optionError.textContent = 'Your browser blocked reading the clipboard. Click in the box and press Ctrl+V.';
                source.focus();
            }
        });
        $('uploadText').addEventListener('change', async (event) => {
            const file = event.target.files[0];
            event.target.value = '';
            if (!file) return;
            const error = Engine.validateCustomFile(file);
            if (error) {
                optionError.textContent = error;
                return;
            }
            source.value = await file.text();
            updateCustomCount();
            optionError.textContent = Engine.validateCustomText(source.value) || '';
        });
    }

    // ---- Settings ----

    function applyAppearance() {
        page.dataset.theme = prefs.theme;
        page.dataset.fontSize = prefs.fontSize;
        page.dataset.lineSpacing = prefs.lineSpacing;
        page.dataset.caret = prefs.caret;
        page.dataset.reducedMotion = prefs.reducedMotion ? 'true' : 'false';
    }

    function setUpSettings() {
        const bind = (id, key, property = 'checked') => {
            const element = $(id);
            if (!element.disabled) element[property] = prefs[key];
            return element;
        };
        const difficulty = document.querySelector('input[name="difficulty"][value="' + prefs.difficulty + '"]');
        if (difficulty) difficulty.checked = true;

        const restartOnChange = (element, key, property = 'checked') => {
            element.addEventListener('change', () => {
                prefs[key] = element[property];
                savePrefs();
                newTest();
            });
        };
        restartOnChange(bind('optPunctuation', 'punctuation'), 'punctuation');
        restartOnChange(bind('optNumbers', 'numbers'), 'numbers');
        restartOnChange(bind('optCapitalization', 'capitalization'), 'capitalization');
        restartOnChange(bind('optCorrections', 'allowCorrections'), 'allowCorrections');
        restartOnChange(bind('optStopOnError', 'stopOnError'), 'stopOnError');
        restartOnChange(bind('optStrict', 'strictAccuracy'), 'strictAccuracy');
        document.querySelectorAll('input[name="difficulty"]').forEach((radio) => {
            radio.addEventListener('change', () => {
                prefs.difficulty = radio.value;
                savePrefs();
                newTest();
            });
        });

        const appearance = (id, key, property = 'value') => {
            const element = bind(id, key, property);
            element.addEventListener('change', () => {
                prefs[key] = element[property];
                savePrefs();
                applyAppearance();
            });
        };
        appearance('optTheme', 'theme');
        appearance('optFontSize', 'fontSize');
        appearance('optLineSpacing', 'lineSpacing');
        appearance('optCaret', 'caret');
        appearance('optReducedMotion', 'reducedMotion', 'checked');
        applyAppearance();
    }

    // ---- Events ----

    input.addEventListener('compositionstart', () => {
        composing = true;
        usedComposition = true;
    });
    input.addEventListener('compositionupdate', (event) => { session.compose(event.data); });
    input.addEventListener('compositionend', () => {
        composing = false;
        commit();
    });
    input.addEventListener('input', (event) => {
        if (composing || event.isComposing) return;
        commit();
    });
    // Enter is only text when the practice text has a line break here. It must
    // still reach an IME, which uses it to confirm a composition.
    input.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' || composing || event.isComposing) return;
        if (session.target[session.units.length] !== '\n') event.preventDefault();
    });
    input.addEventListener('paste', (event) => {
        event.preventDefault();
        pasteAttempted = true;
        statusLine.textContent = 'Pasting is turned off in this test.';
    });

    display.addEventListener('click', () => input.focus());
    display.addEventListener('keydown', (event) => {
        // Arrow keys scroll this region; anything else goes to the typing box
        if (event.key.length === 1) input.focus();
    });
    $('restartTest').addEventListener('click', () => newTest(true));
    $('tryAgain').addEventListener('click', () => newTest(true));
    $('newText').addEventListener('click', () => newTest(false));
    $('shareResult').addEventListener('click', async () => {
        const text = 'I typed ' + lastResult.wpm + ' WPM (5-unit) with ' + lastResult.accuracy + '% accuracy on the TapTapTyping '
            + MODE_LABELS[config.mode] + ' test.';
        try {
            if (navigator.share) await navigator.share({ text, url: location.href });
            else await navigator.clipboard.writeText(text + ' ' + location.href);
            statusLine.textContent = navigator.share ? 'Result shared.' : 'Result copied.';
            track('result_shared');
        } catch (error) {
            statusLine.textContent = 'The result could not be shared.';
        }
    });

    document.querySelectorAll('#testOptions input[type="radio"]:not([name^="custom"])').forEach((radio) => {
        radio.addEventListener('change', () => { if (radio.value !== 'custom') newTest(); });
    });
    const customWordCount = $('customWordCount');
    if (customWordCount) {
        customWordCount.addEventListener('change', () => {
            document.querySelector('input[name="wordCount"][value="custom"]').checked = true;
            newTest();
        });
    }

    // The time left comes from the clock, so it stays correct after a tab switch.
    document.addEventListener('visibilitychange', () => {
        if (document.hidden || !session || session.finished) return;
        if (session.expire(now())) showResults();
        else updateStats();
    });

    const durationForm = $('customDurationForm');
    if (durationForm) {
        durationForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const field = $('customDuration');
            const seconds = Number(field.value);
            if (!Number.isInteger(seconds) || seconds < config.customMin || seconds > config.customMax) {
                $('customDurationError').textContent = 'Enter a whole number from ' + config.customMin + ' to ' + config.customMax + ' seconds.';
                field.setAttribute('aria-invalid', 'true');
                field.focus();
                return;
            }
            $('customDurationError').textContent = '';
            field.removeAttribute('aria-invalid');
            durationSec = seconds;
            newTest();
        });
    }

    window.addEventListener('pagehide', () => {
        if (session && session.startedAt !== null && !completed) track('test_abandoned');
    });
    window.addEventListener('offline', () => {
        if (session && !session.finished) statusLine.textContent = 'You are offline. You can keep typing, but this result may not be saved.';
    });

    const reportForm = $('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const statusNote = $('reportStatus');
            try {
                const response = await postJson('/typing-test/api/report', {
                    language: config.language,
                    mode: config.mode,
                    message: $('reportMessage').value,
                    excerpt: session.target.slice(0, 60).join(''),
                });
                const data = await response.json();
                statusNote.textContent = data.success ? 'Thank you. Your report was sent.' : data.error;
                if (data.success) $('reportMessage').value = '';
            } catch (error) {
                statusNote.textContent = 'The report could not be sent. Try again later.';
            }
        });
    }

    setUpSettings();

    const digitChoice = document.querySelector('input[name="digitStyle"][value="' + prefs.digitStyle + '"]');
    if (digitChoice) digitChoice.checked = true;
    document.querySelectorAll('input[name="digitStyle"]').forEach((radio) => {
        radio.addEventListener('change', () => {
            prefs.digitStyle = radio.value;
            savePrefs();
        });
    });

    if (config.words.length === 0 || segment(config.words[0], config.locale).length === 0) {
        statusLine.textContent = 'Practice text could not be loaded.';
        input.disabled = true;
        return;
    }

    track('mode_selected');
    if (config.mode === 'custom') {
        setUpCustomMode();
        session = new TypingSession({ target: '', locale: config.locale });
        input.disabled = true;
        statusLine.textContent = 'Add your text above, then choose Start Practice.';
        render();
        updateStats();
    } else {
        newTest();
    }
})();
