from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('antifake', '0006_delete_qrcoderecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='verificationlog',
            name='geo_city',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='地點'),
        ),
    ]
