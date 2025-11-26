from django.core.management.base import BaseCommand
from polls.models import PollCategory


class Command(BaseCommand):
    help = 'Initialize default poll categories'

    def handle(self, *args, **options):
        default_categories = [
            'Technology',
            'Entertainment',
            'Sports',
            'Politics',
            'Health',
            'Education',
            'Business',
            'Science',
            'Travel',
            'Food & Dining',
            'Fashion',
            'Music',
            'Movies & TV',
            'Gaming',
            'Social Issues',
            'Environment',
            'Finance',
            'Lifestyle',
            'Arts & Culture',
            'Other'
        ]

        created_count = 0
        existing_count = 0

        for category_name in default_categories:
            _, created = PollCategory.objects.get_or_create(
                name=category_name,
                defaults={'created_by': None}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category_name}')
                )
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} created, {existing_count} already existed'
            )
        )
