from django.db import migrations
import uuid


def convert_ids_to_uuid(apps, schema_editor):
    OrganizationMember = apps.get_model("organizations", "OrganizationMember")

    pass


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0003_remove_organizationinvite_id_and_more"),
    ]

    operations = [
        migrations.RunPython(
            convert_ids_to_uuid, reverse_code=migrations.RunPython.noop
        ),
    ]
