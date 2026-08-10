from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0002_alter_wallettransaction_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="referralsettings",
            name="bonus_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("50.00"),
                help_text="Fixed rupee amount credited once when a referred customer's first order is delivered.",
                max_digits=8,
            ),
        ),
        migrations.RemoveField(
            model_name="referralsettings",
            name="bonus_percent",
        ),
    ]