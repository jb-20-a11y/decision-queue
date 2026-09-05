from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_item_expected_impact"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="date_created",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]