from django.db import migrations

from typingtest.content import SOURCE, STARTER_PARAGRAPHS, STARTER_WORDS


def seed(apps, schema_editor):
    ContentItem = apps.get_model('typingtest', 'ContentItem')
    for language, words in STARTER_WORDS.items():
        ContentItem.objects.create(language=language, content_type='word_list', text=' '.join(words), source_or_license=SOURCE)
        ContentItem.objects.create(
            language=language,
            content_type='paragraph',
            text='\n'.join(STARTER_PARAGRAPHS[language]),
            source_or_license=SOURCE,
        )


def unseed(apps, schema_editor):
    apps.get_model('typingtest', 'ContentItem').objects.filter(source_or_license=SOURCE).delete()


class Migration(migrations.Migration):
    dependencies = [('typingtest', '0002_stage678')]
    operations = [migrations.RunPython(seed, unseed)]
