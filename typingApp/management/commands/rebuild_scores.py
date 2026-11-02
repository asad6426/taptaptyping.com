from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from typingApp.models import Score, TypingTestResult
from typingApp.scoring import is_plausible_result


def plausible(result):
    return is_plausible_result(result.wpm, result.correct_entries, result.time_taken)


def decimal(value):
    return Decimal(str(round(value, 2)))


class Command(BaseCommand):
    help = (
        "Recalculate the Score of every user who has an impossible result, using only "
        "their plausible results. Results are never deleted. Dry run unless --apply is given."
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save the changes')

    @transaction.atomic
    def handle(self, *args, **options):
        affected = {result.user_id for result in TypingTestResult.objects.all() if not plausible(result)}

        for score in Score.objects.select_related('user').filter(user_id__in=affected):
            results = [r for r in TypingTestResult.objects.filter(user=score.user) if plausible(r)]
            count = len(results)
            before = (score.total_score, score.total_tests, score.average_wpm, score.best_wpm)

            score.total_tests = count
            score.total_score = decimal(sum(float(r.marks or 0) for r in results))
            score.average_wpm = decimal(sum(r.wpm for r in results) / count) if count else 0
            score.average_accuracy = decimal(sum(float(r.accuracy) for r in results) / count) if count else 0
            score.best_wpm = max((r.wpm for r in results), default=0)
            score.best_accuracy = max((r.accuracy for r in results), default=0)

            self.stdout.write(
                f"{score.user.username[:3]}*** points {before[0]} -> {score.total_score}, "
                f"tests {before[1]} -> {score.total_tests}, avg wpm {before[2]} -> {score.average_wpm}, "
                f"best wpm {before[3]} -> {score.best_wpm}"
            )
            if options['apply']:
                score.save()

        self.stdout.write(f"{len(affected)} users {'updated' if options['apply'] else 'would be updated (dry run)'}")
