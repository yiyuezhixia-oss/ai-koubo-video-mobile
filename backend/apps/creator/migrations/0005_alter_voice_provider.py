from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("creator", "0004_voiceauthorization")]

    operations = [
        migrations.AlterField(
            model_name="voice",
            name="provider",
            field=models.CharField(default="minimax", max_length=64, verbose_name="供应商"),
        ),
    ]
