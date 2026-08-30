import secrets

from django.db import migrations, models


def fill_invite_tokens(apps, schema_editor):
    Challenge = apps.get_model("hub", "OperatorInviteChallenge")
    seen = set()
    for row in Challenge.objects.all():
        token = secrets.token_urlsafe(16)
        while token in seen:
            token = secrets.token_urlsafe(16)
        seen.add(token)
        row.token = token
        row.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0008_email_change_challenge"),
    ]

    operations = [
        migrations.AddField(
            model_name="operatorinvitechallenge",
            name="inviter_name",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="operatorinvitechallenge",
            name="token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.RunPython(fill_invite_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="operatorinvitechallenge",
            name="token",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
