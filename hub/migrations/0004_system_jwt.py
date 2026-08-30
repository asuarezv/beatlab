from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0003_signup_challenge"),
    ]

    operations = [
        migrations.AddField(
            model_name="system",
            name="jwt_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="system",
            name="jwt_issued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
