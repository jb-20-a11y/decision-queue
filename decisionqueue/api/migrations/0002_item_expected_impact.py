from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="expected_impact",
            field=models.IntegerField(
                choices=[
                    (1, "Lowest"),
                    (2, "Low"),
                    (3, "Medium"),
                    (4, "High"),
                    (5, "Highest"),
                ]
            ),
        ),
    ]