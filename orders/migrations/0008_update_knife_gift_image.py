from django.db import migrations


def use_single_knife_image(apps, schema_editor):
    GiftItem = apps.get_model("orders", "GiftItem")
    GiftItem.objects.filter(name="Kitchen knife").update(image="gifts/knife-single.jpg")


def restore_collage_image(apps, schema_editor):
    GiftItem = apps.get_model("orders", "GiftItem")
    GiftItem.objects.filter(name="Kitchen knife").update(image="gifts/knife.webp")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_giftitem_image"),
    ]

    operations = [
        migrations.RunPython(use_single_knife_image, restore_collage_image),
    ]