"""
Rewrite the golden HTML the parity test compares against.

Run it once before a phase begins, to record what the site serves today. After
that, run it only when a content change is meant to reach visitors — the diff
it produces is what the pull request reviews.
"""

from django.core.management.base import BaseCommand
from django.test import Client

from apps.website import parity


class Command(BaseCommand):
    help = "Record the rendered HTML of every published page as the parity baseline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check", action="store_true",
            help="Compare without writing, and exit non-zero on any difference.",
        )

    def handle(self, *args, **options):
        parity.allow_testserver()
        parity.GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

        client = Client()
        checking = options["check"]
        written = unchanged = differing = 0
        problems = []

        for name, url in parity.targets():
            html = parity.render(client, url)
            path = parity.golden_path(name)
            before = path.read_text(encoding="utf-8") if path.exists() else None

            if before == html:
                unchanged += 1
                continue

            if checking:
                differing += 1
                problems.append(f"  {name} ({url}){' — no golden file yet' if before is None else ''}")
                continue

            path.write_text(html, encoding="utf-8", newline="\n")
            written += 1

        if checking:
            self.stdout.write(f"{unchanged} page(s) match the golden HTML, {differing} differ")
            if problems:
                self.stdout.write(self.style.ERROR("\nThese pages no longer match:"))
                for line in problems:
                    self.stdout.write(self.style.ERROR(line))
                raise SystemExit(1)
            self.stdout.write(self.style.SUCCESS("every page matches"))
            return

        # Any golden file with no page behind it any more is stale.
        expected = {parity.golden_path(name) for name, _ in parity.targets()}
        for stale in sorted(set(parity.GOLDEN_DIR.glob("*.html")) - expected):
            stale.unlink()
            self.stdout.write(self.style.WARNING(f"removed stale golden file {stale.name}"))

        self.stdout.write(
            self.style.SUCCESS(f"{written} page(s) written, {unchanged} unchanged")
        )
