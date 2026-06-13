from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("directory", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="location",
            field=models.CharField(
                blank=True,
                choices=[("UE", "UE"), ("AH", "AH"), ("TTS", "TTS")],
                max_length=3,
            ),
        ),
    ]
