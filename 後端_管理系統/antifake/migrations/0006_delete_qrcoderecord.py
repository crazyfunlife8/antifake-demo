from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('antifake', '0005_qrcoderecord_site_base_url'),
    ]

    operations = [
        migrations.DeleteModel(
            name='QrCodeRecord',
        ),
    ]
