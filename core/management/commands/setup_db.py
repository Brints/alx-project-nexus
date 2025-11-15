import os

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up the development database with initial data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Starting Database Setup ---"))

        # Create PostgreSQL database if it doesn't exist
        self.stdout.write("Checking PostgreSQL database...")
        self.create_postgres_db()

        # Run makemigrations
        self.stdout.write("Making migrations...")
        call_command("makemigrations")

        # Apply migrations
        self.stdout.write("Applying migrations...")
        call_command("migrate")

        # Create a superuser (if it doesn't exist)
        self.stdout.write("Checking for superuser...")
        self.create_superuser()

    def create_superuser(self):
        admin_user = os.environ.get("ADMIN_USER", os.environ.get("ADMIN_USERNAME"))
        admin_email = os.environ.get("ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL"))
        admin_pass = os.environ.get("ADMIN_PASS", os.environ.get("ADMIN_PASSWORD"))

        if not User.objects.filter(username=admin_user).exists():
            self.stdout.write(f'Creating superuser "{admin_user}"...')
            User.objects.create_superuser(
                username=admin_user, email=admin_email, password=admin_pass
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{admin_user}" created.'))
        else:
            self.stdout.write(
                self.style.WARNING(f'Superuser "{admin_user}" already exists.')
            )

    def create_postgres_db(self):
        """Create PostgreSQL database if it doesn't exist."""
        import psycopg2
        from psycopg2 import sql

        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")

        # Connect to the default database to create a new one
        conn = psycopg2.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [db_name]
        )
        exists = cursor.fetchone()

        if not exists:
            self.stdout.write(f'Creating database "{db_name}"...')
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            self.stdout.write(self.style.SUCCESS(f'Database "{db_name}" created.'))
        else:
            self.stdout.write(
                self.style.WARNING(f'Database "{db_name}" already exists.')
            )

        cursor.close()
        conn.close()
