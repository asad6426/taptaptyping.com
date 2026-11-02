from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import Resolver404, resolve

from blog.models import BlogPost


def is_servable(post):
    try:
        return resolve(f'/{post.slug}/', urlconf='TapTapTyping.urls').url_name == 'blog_detail'
    except Resolver404:
        return False


class Command(BaseCommand):
    help = "Give posts a slug the public route can serve. Dry run unless --apply is given."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save the changes')

    @transaction.atomic
    def handle(self, *args, **options):
        broken = [post for post in BlogPost.objects.all() if not is_servable(post)]
        for post in broken:
            old = post.slug
            post.slug = post.build_slug(old)
            self.stdout.write(f"post {post.id} (published={post.published}): {old!r} -> {post.slug!r}")
            if options['apply']:
                post.save(update_fields=['slug'])
        self.stdout.write(f"{len(broken)} posts {'updated' if options['apply'] else 'would be updated (dry run)'}")
