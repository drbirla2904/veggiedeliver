from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_alter_order_delivery_speed"),
    ]

    operations = [
        migrations.CreateModel(
            name="GiftItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("minimum_order_value", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("stock_quantity", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="order",
            name="gift_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="won_orders",
                to="orders.giftitem",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="gift_spun_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]