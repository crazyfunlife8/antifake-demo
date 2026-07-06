from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('antifake', '0006_delete_qrcoderecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='antifakecode',
            name='url_exported',
            field=models.BooleanField(
                default=False,
                help_text='是否已將完整掃描 URL 匯出給廠商製作 QR Code',
                verbose_name='已匯出 URL',
            ),
        ),
    ]
