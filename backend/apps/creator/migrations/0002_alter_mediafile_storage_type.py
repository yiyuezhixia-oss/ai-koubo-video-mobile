from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("creator", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mediafile",
            name="storage_type",
            field=models.CharField(
                choices=[
                    ("local", "本地"),
                    ("server_public", "服务器公网"),
                    ("oss", "阿里云 OSS"),
                    ("cos", "腾讯云 COS"),
                    ("object", "S3 兼容对象存储"),
                    ("remote", "第三方远程 URL"),
                ],
                default="local",
                max_length=32,
                verbose_name="存储类型",
            ),
        ),
    ]
