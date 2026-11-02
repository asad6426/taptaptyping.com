"""
Server-side scoring. Text units here are the authority for ranked results, so
they do not depend on the browser's ICU version. See docs/typing-test/SCORING.md.
"""
import unicodedata

VIRAMA_SCRIPTS = ('DEVANAGARI', 'BENGALI')
# Marks that join the previous unit although their category is not M*
EXTENDERS = {'‌', '‍', 'ำ', 'ຳ'}


def is_extender(char):
    if char in EXTENDERS or unicodedata.category(char).startswith('M'):
        return True
    return 'ᅠ' <= char <= 'ᇿ'  # Hangul vowel and final jamo


def is_indic_consonant(char):
    if unicodedata.category(char) != 'Lo':
        return False
    return unicodedata.name(char, '').startswith(tuple(f'{script} LETTER' for script in VIRAMA_SCRIPTS))


def is_virama(char):
    return unicodedata.combining(char) == 9 and unicodedata.name(char, '').startswith(VIRAMA_SCRIPTS)


def split_units(text):
    """One unit is what a reader sees as one character: a base with its marks,
    and Indic consonants joined by a virama."""
    units = []
    for char in unicodedata.normalize('NFC', text or ''):
        if units:
            previous = units[-1]
            if is_extender(char) or (is_indic_consonant(char) and is_virama(previous[-1])):
                units[-1] = previous + char
                continue
        units.append(char)
    return units


def can_become(partial, unit):
    return unicodedata.normalize('NFD', unit).startswith(unicodedata.normalize('NFD', partial))


def score_typed_text(target, typed):
    """Compares typed text with the target position by position. A last unit that
    can still become the target unit is unfinished and does not count."""
    target_units = split_units(target)
    typed_units = split_units(typed)
    correct = incorrect = 0
    for index, unit in enumerate(typed_units):
        expected = target_units[index] if index < len(target_units) else None
        if unit == expected:
            correct += 1
        elif index == len(typed_units) - 1 and expected is not None and can_become(unit, expected):
            continue
        else:
            incorrect += 1
    return {
        'correct': correct,
        'incorrect': incorrect,
        'typed': len(typed_units),
        'target': len(target_units),
    }
