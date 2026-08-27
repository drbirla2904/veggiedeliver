from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_seed_gift_items"),
    ]

    operations = [
        migrations.AddField(
            model_name="giftitem",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="gifts/"),
        ),
    ]