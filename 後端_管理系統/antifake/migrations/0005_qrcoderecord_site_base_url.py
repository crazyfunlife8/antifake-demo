from django.db import migrations, models
import django.db.models.deletion


def add_site_base_url(apps, schema_editor):
    SystemConfig = apps.get_model('antifake', 'SystemConfig')
    SystemConfig.objects.get_or_create(
        key='SITE_BASE_URL',
        defaults={
            'value': 'https://antifake-demo-production.up.railway.app',
            'description': 'QR Code 掃描的網站根網址（結尾不加斜線）',
        },
    )


def remove_site_base_url(apps, schema_editor):
    SystemConfig = apps.get_model('antifake', 'SystemConfig')
    SystemConfig.objects.filter(key='SITE_BASE_URL').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('antifake', '0004_systemconfig_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='QrCodeRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_url', models.URLField(max_length=500, verbose_name='完整 URL')),
                ('image_b64', models.TextField(verbose_name='QR Code 圖片（base64）')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('code', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='qrcodes',
                    to='antifake.antifakecode',
                    verbose_name='防偽碼',
                )),
            ],
            options={
                'verbose_name': 'QR Code 記錄',
                'verbose_name_plural': 'QR Code 記錄',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(add_site_base_url, remove_site_base_url),
    ]
