from django.db import migrations, models


def populate_operator_profiles(apps, schema_editor):
    Operator = apps.get_model("hub", "Operator")
    used = set()
    for operator in Operator.objects.select_related("user").all():
        user = operator.user
        first = (getattr(user, "first_name", None) or "").strip()
        last = (getattr(user, "last_name", None) or "").strip()
        operator.first_name = first or "Operator"
        operator.last_name = last or (user.username if user else str(operator.pk))
        email = (getattr(user, "email", None) or "").strip().lower()
        if not email or email in used:
            email = f"op-{operator.pk}@pending.invalid"
        used.add(email)
        operator.email = email
        operator.save(update_fields=["first_name", "last_name", "email"])


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0004_system_jwt"),
    ]

    operations = [
        migrations.AddField(
            model_name="operator",
            name="first_name",
            field=models.CharField(default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="operator",
            name="last_name",
            field=models.CharField(default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="operator",
            name="email",
            field=models.EmailField(max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="operator",
            name="last_login_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(populate_operator_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="operator",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterModelOptions(
            name="operator",
            options={"ordering": ["last_name", "first_name", "email"]},
        ),
        migrations.CreateModel(
            name="OperatorOtpChallenge",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("code_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
