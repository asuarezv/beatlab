from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hub", "0010_operator_beat_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="beattype",
            name="severity",
            field=models.CharField(
                choices=[
                    ("info", "Info"),
                    ("aviso", "Aviso"),
                    ("alerta", "Alerta"),
                    ("critica", "Crítica"),
                ],
                default="aviso",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="beattype",
            name="icon",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
