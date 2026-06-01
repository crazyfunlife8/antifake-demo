from django.db import migrations


INITIAL_CONFIGS = [
    ('VERIFY_WARN_THRESHOLD', '2',           '驗證次數達此值時顯示警示訊息'),
    ('SERVICE_PHONE',         '0800-004-088','警示訊息內顯示的服務電話'),
    ('BLOCK_CONTENT_7',       '',            'checkTruth 頁頂部活動看板 HTML（空白表示不顯示）'),
]


def add_initial_configs(apps, schema_editor):
    SystemConfig = apps.get_model('antifake', 'SystemConfig')
    for key, value, description in INITIAL_CONFIGS:
        SystemConfig.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description},
        )


def remove_initial_configs(apps, schema_editor):
    SystemConfig = apps.get_model('antifake', 'SystemConfig')
    SystemConfig.objects.filter(key__in=[k for k, _, _ in INITIAL_CONFIGS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('antifake', '0003_antifakecode_deleted_at_alter_systemconfig_value'),
    ]

    operations = [
        migrations.RunPython(add_initial_configs, remove_initial_configs),
    ]
