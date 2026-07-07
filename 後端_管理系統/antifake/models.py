"""
antifake/models.py
所有資料表定義。
"""
from django.db import models


class AntiFakeCode(models.Model):
    """
    防偽碼主資料表。
    一支電波拉皮探頭 = 一個防偽碼。
    """
    code = models.CharField(
        "防偽碼", max_length=50, primary_key=True,
        help_text="探頭上印的防偽碼字串，例如 YK6Z0VXAG8G8"
    )
    verify_count = models.PositiveIntegerField(
        "驗證次數", default=0,
        help_text="消費者掃描查驗的累計次數。第一次驗證為 1、N≥2 顯示有疑慮警語"
    )
    is_active = models.BooleanField(
        "啟用中", default=True,
        help_text="關閉後查詢仍會顯示計數、但不再增加"
    )
    first_verify_at = models.DateTimeField("首次驗證時間", null=True, blank=True)
    last_verify_at = models.DateTimeField("最近驗證時間", null=True, blank=True)
    notes = models.TextField(
        "備註", blank=True, default="",
        help_text="批次號 / 產品 SKU / 出貨對象等業主自由備註"
    )
    deleted_at = models.DateTimeField("刪除時間", null=True, blank=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("最後修改時間", auto_now=True)

    class Meta:
        verbose_name = "防偽碼"
        verbose_name_plural = "防偽碼清單"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["verify_count"], name="idx_verify_count"),
            models.Index(fields=["last_verify_at"], name="idx_last_verify_at"),
            models.Index(fields=["is_active"], name="idx_is_active"),
        ]

    def __str__(self):
        return f"{self.code} (N={self.verify_count})"


class VerificationLog(models.Model):
    """
    每次消費者查驗都寫一筆，用於歷史追蹤與異常偵測。
    """
    code = models.ForeignKey(
        AntiFakeCode, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="防偽碼", related_name="logs",
        help_text="查驗的碼（若已被刪除則為 null）"
    )
    verify_at = models.DateTimeField("驗證時間", auto_now_add=True)
    verify_count_snapshot = models.PositiveIntegerField(
        "當次驗證次數", default=0,
        help_text="該次驗證時的累計 N 值"
    )
    client_ip = models.CharField("消費者 IP", max_length=45, blank=True, default="")
    user_agent = models.TextField("瀏覽器 UA", blank=True, default="")
    geo_lat = models.DecimalField(
        "緯度", max_digits=10, decimal_places=7, null=True, blank=True
    )
    geo_lng = models.DecimalField(
        "經度", max_digits=10, decimal_places=7, null=True, blank=True
    )
    geo_accuracy = models.DecimalField(
        "定位精度", max_digits=8, decimal_places=2, null=True, blank=True
    )
    geo_city = models.CharField("地點", max_length=100, blank=True, default="")
    auth_token = models.CharField("auth token", max_length=100, blank=True, default="")
    request_info_id = models.CharField("requestInfoId", max_length=100, blank=True, default="")

    class Meta:
        verbose_name = "驗證記錄"
        verbose_name_plural = "驗證歷史"
        ordering = ["-verify_at"]
        indexes = [
            models.Index(fields=["code", "verify_at"], name="idx_code_verify_at"),
            models.Index(fields=["verify_at"], name="idx_verify_at"),
        ]

    def __str__(self):
        code_str = self.code.code if self.code else "(已刪除)"
        return f"{code_str} @ {self.verify_at:%Y-%m-%d %H:%M}"


class UploadedFile(models.Model):
    """
    上傳圖片索引表。
    file_no 對應前端 /generic/getImg.do?fileNo=X。
    """
    file_no = models.BigAutoField("fileNo", primary_key=True)
    filename = models.CharField("原始檔名", max_length=255, blank=True, default="")
    content_type = models.CharField("MIME 類型", max_length=100, blank=True, default="")
    file_size = models.BigIntegerField("檔案大小 (bytes)", default=0)
    storage_path = models.CharField(
        "儲存路徑", max_length=500,
        help_text="本機路徑或 S3 key"
    )
    uploaded_at = models.DateTimeField("上傳時間", auto_now_add=True)
    uploaded_by_session = models.CharField(
        "上傳者 session", max_length=100, blank=True, default=""
    )

    class Meta:
        verbose_name = "上傳檔案"
        verbose_name_plural = "上傳檔案清單"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"#{self.file_no} {self.filename}"


class ContactTicket(models.Model):
    """
    聯絡我們表單提交記錄（/contact.do POST）。
    """
    PROB_TYPE_CHOICES = [
        ('1', '假冒產品'),
        ('2', '產品問題'),
        ('3', '其他'),
    ]
    is_member = models.BooleanField("是否為會員", default=False)
    legal_name = models.CharField("姓名", max_length=40, blank=True, default="")
    email = models.EmailField("電子信箱", blank=True, default="")
    country_code = models.CharField("國際區號", max_length=5, blank=True, default="")
    phone = models.CharField("手機", max_length=20, blank=True, default="")
    sex = models.CharField("性別", max_length=1, blank=True, default="")
    prod_seq = models.CharField("商品防偽碼", max_length=50, blank=True, default="")
    prob_type = models.CharField(
        "問題類型", max_length=5, blank=True, default="",
        choices=PROB_TYPE_CHOICES
    )
    pur_country = models.CharField("購買國家", max_length=20, blank=True, default="")
    pur_city = models.CharField("購買縣市", max_length=50, blank=True, default="")
    store_type = models.CharField("商店分類", max_length=5, blank=True, default="")
    pur_store = models.CharField("購買商店", max_length=50, blank=True, default="")
    pur_date = models.DateField("購買日期", null=True, blank=True)
    pur_price = models.DecimalField(
        "購買金額", max_digits=12, decimal_places=2, null=True, blank=True
    )
    pur_price_currency = models.CharField("幣別", max_length=5, blank=True, default="")
    prob_desc = models.TextField("問題描述", blank=True, default="")
    uploaded_file = models.ForeignKey(
        UploadedFile, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="附件"
    )
    agree_to_terms = models.BooleanField("同意條款", default=False)
    created_at = models.DateTimeField("提交時間", auto_now_add=True)

    class Meta:
        verbose_name = "聯絡我們"
        verbose_name_plural = "聯絡我們清單"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.legal_name} <{self.email}> @ {self.created_at:%Y-%m-%d}"


class SupplementReport(models.Model):
    """
    補件回報表單（/saveFormFields.do，formId=135）。
    """
    contact_info = models.CharField(
        "聯絡資訊", max_length=100, blank=True, default="",
        help_text="格式：王小明/09XXXXXXXX"
    )
    uploaded_file = models.ForeignKey(
        UploadedFile, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="上傳照片"
    )
    created_at = models.DateTimeField("提交時間", auto_now_add=True)

    class Meta:
        verbose_name = "補件回報"
        verbose_name_plural = "補件回報清單"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contact_info} @ {self.created_at:%Y-%m-%d}"


class QuestionnaireResponse(models.Model):
    """
    問卷回應（/saveAnswerRecord.do）。
    answers 存整份 JSON，保持彈性。
    """
    code = models.ForeignKey(
        AntiFakeCode, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="對應防偽碼", related_name="questionnaire_responses"
    )
    answers_json = models.TextField(
        "回答內容 (JSON)", blank=True, default="",
        help_text="前端送來的 questObjectList 原始 JSON"
    )
    created_at = models.DateTimeField("提交時間", auto_now_add=True)

    class Meta:
        verbose_name = "問卷回應"
        verbose_name_plural = "問卷回應清單"
        ordering = ["-created_at"]

    def __str__(self):
        code_str = self.code.code if self.code else "(無碼)"
        return f"{code_str} @ {self.created_at:%Y-%m-%d}"


class SystemConfig(models.Model):
    key = models.CharField("設定鍵", max_length=100, unique=True)
    value = models.TextField("設定值", blank=True, default="")
    description = models.CharField("說明", max_length=255, blank=True, default="")
    updated_at = models.DateTimeField("最後修改時間", auto_now=True)

    class Meta:
        verbose_name = "系統設定"
        verbose_name_plural = "系統設定"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get(cls, key, default=""):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
