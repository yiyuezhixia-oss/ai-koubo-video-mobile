from django.conf import settings
from django.db import models


class MediaFile(models.Model):
    FILE_TYPE_CHOICES = [
        ("source_audio", "克隆源音频"),
        ("tts_audio", "配音音频"),
        ("source_video", "源视频"),
        ("output_video", "成片视频"),
    ]
    STORAGE_CHOICES = [
        ("local", "本地"),
        ("server_public", "服务器公网"),
        ("oss", "阿里云 OSS"),
        ("cos", "腾讯云 COS"),
        ("object", "S3 兼容对象存储"),
        ("remote", "第三方远程 URL"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_files")
    task = models.ForeignKey("Task", on_delete=models.SET_NULL, blank=True, null=True, related_name="media_files")
    file_type = models.CharField("文件类型", max_length=32, choices=FILE_TYPE_CHOICES)
    storage_type = models.CharField("存储类型", max_length=32, choices=STORAGE_CHOICES, default="local")
    file_path = models.CharField("文件路径", max_length=500, blank=True)
    file_url = models.URLField("文件 URL", max_length=800, blank=True)
    file_size = models.PositiveIntegerField("文件大小", default=0)
    duration = models.FloatField("时长秒", default=0)
    mime_type = models.CharField("MIME", max_length=100, blank=True)
    checksum = models.CharField("校验值", max_length=128, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "媒体文件"
        verbose_name_plural = "媒体文件"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_type} #{self.id}"


class Voice(models.Model):
    STATUS_CHOICES = [
        ("cloning", "克隆中"),
        ("pending_confirm", "待确认"),
        ("available", "可用"),
        ("failed", "失败"),
        ("expired", "已过期"),
        ("discarded", "已丢弃"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voices")
    name = models.CharField("音色名称", max_length=80)
    provider = models.CharField("供应商", max_length=64, default="minimax")
    provider_voice_id = models.CharField("供应商 voice_id", max_length=128, blank=True)
    source_audio_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="source_voice_set")
    sample_audio_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="sample_voice_set")
    sample_audio_url = models.URLField("试听音频 URL", max_length=800, blank=True)
    clone_test_text = models.CharField("试听文案", max_length=220, blank=True)
    status = models.CharField("状态", max_length=32, choices=STATUS_CHOICES, default="pending_confirm")
    confirmed_at = models.DateTimeField("确认入库时间", blank=True, null=True)
    first_used_at = models.DateTimeField("首次使用时间", blank=True, null=True)
    must_use_before = models.DateTimeField("必须使用截止", blank=True, null=True)
    discarded_at = models.DateTimeField("丢弃时间", blank=True, null=True)
    error_message = models.TextField("错误信息", blank=True)
    idempotency_key = models.CharField("克隆幂等 Key", max_length=160, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "音色"
        verbose_name_plural = "音色"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uniq_voice_clone_key",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class VoiceAuthorization(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_authorizations")
    voice = models.OneToOneField(Voice, on_delete=models.SET_NULL, blank=True, null=True, related_name="authorization")
    source_audio_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="voice_authorizations")
    ownership_confirmed = models.BooleanField("确认本人声音或已获授权", default=False)
    separate_consent_confirmed = models.BooleanField("确认已取得被编辑者单独同意", default=False)
    statement_version = models.CharField("授权声明版本", max_length=32, default="voice-auth-v1")
    ip_address = models.GenericIPAddressField("IP 地址", blank=True, null=True)
    user_agent = models.CharField("客户端", max_length=300, blank=True)
    accepted_at = models.DateTimeField("同意时间", auto_now_add=True)

    class Meta:
        verbose_name = "声音克隆授权"
        verbose_name_plural = "声音克隆授权"
        ordering = ["-accepted_at"]

    def __str__(self):
        return f"{self.user}:voice-auth:{self.accepted_at:%Y-%m-%d %H:%M}"


class Task(models.Model):
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("rewriting", "改写中"),
        ("rewrite_done", "改写完成"),
        ("tts_done", "配音完成"),
        ("video_uploaded", "视频已上传"),
        ("generating", "生成中"),
        ("completed", "已完成"),
        ("failed", "失败"),
    ]
    STEP_CHOICES = [
        ("script", "文案"),
        ("rewrite", "改写"),
        ("tts", "配音"),
        ("video", "视频"),
        ("generating", "生成中"),
        ("preview", "预览"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField("标题", max_length=120, blank=True)
    source_type = models.CharField("来源类型", max_length=32, default="manual")
    source_url = models.URLField("来源链接", max_length=800, blank=True)
    original_text = models.TextField("原文", blank=True)
    rewritten_text = models.TextField("改写文案", blank=True)
    selected_voice = models.ForeignKey(Voice, on_delete=models.SET_NULL, blank=True, null=True, related_name="tasks")
    tts_audio_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="tts_tasks")
    source_video_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="source_video_tasks")
    output_video_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="output_video_tasks")
    status = models.CharField("状态", max_length=32, choices=STATUS_CHOICES, default="draft")
    current_step = models.CharField("当前步骤", max_length=32, choices=STEP_CHOICES, default="script")
    point_cost_total = models.IntegerField("累计消耗积分", default=0)
    refund_status = models.CharField("退款状态", max_length=32, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "创作任务"
        verbose_name_plural = "创作任务"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"任务 #{self.id}"


class ExternalJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "待提交"),
        ("submitted", "已提交"),
        ("processing", "处理中"),
        ("succeeded", "成功"),
        ("failed", "失败"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="external_jobs")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, blank=True, null=True, related_name="external_jobs")
    provider = models.CharField("供应商", max_length=64)
    job_type = models.CharField("任务类型", max_length=64)
    provider_task_id = models.CharField("供应商任务 ID", max_length=160, blank=True)
    status = models.CharField("状态", max_length=32, choices=STATUS_CHOICES, default="pending")
    request_payload_summary = models.JSONField("请求摘要", default=dict, blank=True)
    response_payload_summary = models.JSONField("响应摘要", default=dict, blank=True)
    result_url = models.URLField("结果 URL", max_length=800, blank=True)
    result_media_file = models.ForeignKey(MediaFile, on_delete=models.SET_NULL, blank=True, null=True, related_name="external_result_jobs")
    cost_points = models.IntegerField("积分成本", default=0)
    error_code = models.CharField("错误码", max_length=80, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    idempotency_key = models.CharField("提交幂等 Key", max_length=160, blank=True)
    submitted_at = models.DateTimeField("提交时间", blank=True, null=True)
    finished_at = models.DateTimeField("完成时间", blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "外部任务"
        verbose_name_plural = "外部任务"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider", "job_type", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uniq_external_job_key",
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.job_type}:{self.status}"


class ApiCallLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="api_call_logs")
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, blank=True, null=True, related_name="api_call_logs")
    external_job = models.ForeignKey(ExternalJob, on_delete=models.SET_NULL, blank=True, null=True, related_name="api_call_logs")
    provider = models.CharField("供应商", max_length=64)
    api_type = models.CharField("接口类型", max_length=64)
    endpoint = models.CharField("接口地址", max_length=300, blank=True)
    http_status = models.IntegerField("HTTP 状态", default=0)
    request_status = models.CharField("请求状态", max_length=32, default="success")
    request_id = models.CharField("请求 ID", max_length=160, blank=True)
    duration_ms = models.IntegerField("耗时 ms", default=0)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "接口调用日志"
        verbose_name_plural = "接口调用日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.api_type}:{self.request_status}"
