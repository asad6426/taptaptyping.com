"""Practice content from the database, reviewed through the admin."""
from .models import ContentItem


def content_for(language_code):
    """Words and paragraphs a language may show. Rejected items are left out."""
    items = ContentItem.objects.filter(language=language_code).exclude(review_status=ContentItem.REJECTED)
    words = []
    paragraphs = []
    versions = []
    for item in items:
        versions.append(f'{item.pk}.{item.version}')
        if item.content_type == ContentItem.WORD_LIST:
            words += item.text.split()
        else:
            paragraphs.append([line for line in item.text.splitlines() if line.strip()])
    return {
        'words': words,
        'paragraph': paragraphs[0] if paragraphs else [],
        'version': '-'.join(versions)[:30],
    }


def is_language_reviewed(language_code):
    """A language opens to search only when it has content and all of it is approved."""
    statuses = list(
        ContentItem.objects.filter(language=language_code)
        .exclude(review_status=ContentItem.REJECTED)
        .values_list('content_type', 'review_status')
    )
    types = {content_type for content_type, _ in statuses}
    return types == {ContentItem.WORD_LIST, ContentItem.PARAGRAPH} and all(
        status == ContentItem.APPROVED for _, status in statuses
    )


def reviewed_languages():
    from .languages import LANGUAGES
    return [language for language in LANGUAGES if is_language_reviewed(language.code)]
