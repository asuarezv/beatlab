from django.db import migrations, models


def grant_existing_operators_all_types(apps, schema_editor):
    Operator = apps.get_model("hub", "Operator")
    Operator.objects.update(receive_all_beat_types=True)


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0009_operator_invite_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="operator",
            name="receive_all_beat_types",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="operator",
            name="assigned_beat_types",
            field=models.ManyToManyField(
                blank=True,
                related_name="operators",
                to="hub.beattype",
            ),
        ),
        migrations.AddField(
            model_name="operatorinvitechallenge",
            name="receive_all_beat_types",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="operatorinvitechallenge",
            name="assigned_beat_types",
            field=models.ManyToManyField(
                blank=True,
                related_name="operator_invites",
                to="hub.beattype",
            ),
        ),
        migrations.RunPython(
            grant_existing_operators_all_types,
            migrations.RunPython.noop,
        ),
    ]
