"""
The one list of supported languages. Routes, selectors, metadata and the
language links are all generated from LANGUAGES, so adding a language here is
enough to add its pages.

word_boundary is 'spaces' when words are normally separated by spaces and
'none' when they are not. Practice text and later the Words mode follow it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    name: str
    locale: str
    script: str
    direction: str = 'ltr'
    word_boundary: str = 'spaces'
    comma: str = ','
    end: str = '.'
    digits: str = ''

    @property
    def cased(self):
        return self.script in ('latin', 'cyrillic')

    @property
    def code(self):
        return self.name.lower()

    @property
    def slug(self):
        return f'{self.code}-typing-test'

    @property
    def path(self):
        return f'/{self.slug}'

    @property
    def joiner(self):
        return ' ' if self.word_boundary == 'spaces' else ''


LANGUAGES = (
    Language('English', 'en', 'latin'),
    Language('Bengali', 'bn', 'bengali', end='।', digits='০১২৩৪৫৬৭৮৯'),
    Language('Hindi', 'hi', 'devanagari', end='।', digits='०१२३४५६७८९'),
    Language('Indonesian', 'id', 'latin'),
    Language('Spanish', 'es', 'latin'),
    Language('Portuguese', 'pt', 'latin'),
    Language('Vietnamese', 'vi', 'latin'),
    Language('Turkish', 'tr', 'latin'),
    Language('German', 'de', 'latin'),
    Language('French', 'fr', 'latin'),
    Language('Arabic', 'ar', 'arabic', direction='rtl', comma='،', digits='٠١٢٣٤٥٦٧٨٩'),
    Language('Russian', 'ru', 'cyrillic'),
    Language('Thai', 'th', 'thai', word_boundary='none', comma='', end='', digits='๐๑๒๓๔๕๖๗๘๙'),
    Language('Urdu', 'ur', 'urdu', direction='rtl', comma='،', end='۔', digits='۰۱۲۳۴۵۶۷۸۹'),
    Language('Italian', 'it', 'latin'),
    Language('Polish', 'pl', 'latin'),
    Language('Dutch', 'nl', 'latin'),
    Language('Filipino', 'fil', 'latin'),
    Language('Japanese', 'ja', 'japanese', word_boundary='none', comma='、', end='。'),
    Language('Korean', 'ko', 'korean'),
)

LANGUAGES_BY_CODE = {language.code: language for language in LANGUAGES}

# route segment, seconds, minutes shown in the H1
DURATIONS = (
    ('1-minute', 60, 1),
    ('2-minutes', 120, 2),
    ('3-minutes', 180, 3),
    ('5-minutes', 300, 5),
    ('10-minutes', 600, 10),
)

CUSTOM_DURATION_MIN = 15
CUSTOM_DURATION_MAX = 1800

# internal key, route segment (empty for the main page), label
MODES = (
    ('time', '', 'Time'),
    ('words', 'words', 'Words'),
    ('paragraph', 'paragraph', 'Paragraph'),
    ('custom', 'custom-text', 'Custom Text'),
    ('numbers', 'numbers', 'Numbers'),
)

# For languages that separate words with spaces
WORD_COUNTS = (10, 25, 50, 100, 200)
# For languages that do not, length is counted in text units instead
UNIT_COUNTS = (25, 50, 100, 200, 400)
