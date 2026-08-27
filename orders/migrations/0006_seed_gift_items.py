from django.db import migrations


def create_default_gifts(apps, schema_editor):
    GiftItem = apps.get_model("orders", "GiftItem")
    GiftItem.objects.bulk_create([
        GiftItem(
            name="Tea cup",
            description="A cheerful cup for your next chai break.",
            minimum_order_value=0,
            stock_quantity=10,
            is_active=True,
        ),
        GiftItem(
            name="Kitchen knife",
            description="A handy kitchen essential for everyday prep.",
            minimum_order_value=100,
            stock_quantity=10,
            is_active=True,
        ),
        GiftItem(
            name="Dinner plate",
            description="A fresh plate to brighten your table.",
            minimum_order_value=200,
            stock_quantity=10,
            is_active=True,
        ),
    ])


def remove_default_gifts(apps, schema_editor):
    GiftItem = apps.get_model("orders", "GiftItem")
    GiftItem.objects.filter(name__in=["Tea cup", "Kitchen knife", "Dinner plate"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_giftitem_order_gift_item_order_gift_spun_at"),
    ]

    operations = [
        migrations.RunPython(create_default_gifts, remove_default_gifts),
    ]
