from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0006_operator_invite_challenge"),
    ]

    operations = [
        migrations.AddField(
            model_name="operator",
            name="password_hash",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
