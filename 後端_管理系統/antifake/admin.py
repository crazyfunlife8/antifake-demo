import base64
import csv
import io
import json
import random
from datetime import timedelta

import openpyxl
import qrcode
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.forms import CheckboxSelectMultiple
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    AntiFakeCode, VerificationLog, UploadedFile,
    ContactTicket, SupplementReport, QuestionnaireResponse, SystemConfig,
    QrCodeRecord,
)


def _can_export(request):
    return request.user.is_superuser or request.user.groups.filter(name__in=["管理員", "法務"]).exists()


def _export_csv(rows, headers, filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def _export_excel(rows, headers, filename):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append([str(v) if v is not None else "" for v in row])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(buf, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return response

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 排除 0/O/1/I 避免混淆


def _generate_code(length):
    return "".join(random.choices(CODE_CHARS, k=length))


class DeletedFilter(admin.SimpleListFilter):
    title = "刪除狀態"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return [
            ("active", "使用中"),
            ("deleted", "已刪除"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset.filter(deleted_at__isnull=True)

    def choices(self, changelist):
        # 預設選取「使用中」
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }


class VerifyCountFilter(admin.SimpleListFilter):
    title = "驗證次數"
    parameter_name = "verify_count_range"

    def lookups(self, request, model_admin):
        return [
            ("0", "0 次（未驗證）"),
            ("1", "1 次"),
            ("2_4", "2–4 次"),
            ("5+", "5 次以上（異常）"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "0":
            return queryset.filter(verify_count=0)
        if self.value() == "1":
            return queryset.filter(verify_count=1)
        if self.value() == "2_4":
            return queryset.filter(verify_count__gte=2, verify_count__lte=4)
        if self.value() == "5+":
            return queryset.filter(verify_count__gte=5)
        return queryset


def _antifakecode_rows(qs):
    headers = ["防偽碼", "驗證次數", "啟用中", "首次驗證時間", "最近驗證時間", "備註", "建立時間"]
    rows = [[o.code, o.verify_count, "是" if o.is_active else "否",
             o.first_verify_at, o.last_verify_at, o.notes, o.created_at] for o in qs]
    return headers, rows


def _verificationlog_rows(qs):
    headers = ["防偽碼", "驗證時間", "當次次數", "IP", "緯度", "經度", "定位精度", "UA"]
    rows = [[o.code_id, o.verify_at, o.verify_count_snapshot,
             o.client_ip, o.geo_lat, o.geo_lng, o.geo_accuracy, o.user_agent] for o in qs]
    return headers, rows


def _contactticket_rows(qs):
    headers = ["姓名", "信箱", "電話", "防偽碼", "問題類型", "問題描述", "購買日期", "提交時間"]
    rows = [[o.legal_name, o.email, o.phone, o.prod_seq, o.get_prob_type_display(),
             o.prob_desc, o.pur_date, o.created_at] for o in qs]
    return headers, rows


def _supplementreport_rows(qs):
    headers = ["聯絡資訊", "上傳照片 fileNo", "提交時間"]
    rows = [[o.contact_info, o.uploaded_file_id, o.created_at] for o in qs]
    return headers, rows


def _questionnaireresponse_rows(qs):
    headers = ["防偽碼", "回答內容", "提交時間"]
    rows = [[o.code_id, o.answers_json, o.created_at] for o in qs]
    return headers, rows


class VerificationLogInline(admin.TabularInline):
    model = VerificationLog
    fields = ["verify_at", "verify_count_snapshot", "client_ip", "geo_lat", "geo_lng", "user_agent"]
    readonly_fields = ["verify_at", "verify_count_snapshot", "client_ip", "geo_lat", "geo_lng", "user_agent"]
    extra = 0
    can_delete = False
    ordering = ["-verify_at"]
    verbose_name = "驗證記錄"
    verbose_name_plural = "驗證歷史（時間倒序）"


@admin.register(AntiFakeCode)
class AntiFakeCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "verify_count", "is_active", "last_verify_at", "has_qrcode", "notes", "created_at"]
    list_filter = [DeletedFilter, "is_active", VerifyCountFilter, "created_at"]
    search_fields = ["code", "notes"]
    readonly_fields = ["verify_count", "first_verify_at", "last_verify_at", "created_at", "updated_at", "deleted_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    inlines = [VerificationLogInline]
    actions = ["export_csv", "export_excel", "restore", "generate_qrcode", "soft_delete", "hard_delete"] # 刪除鍵放末尾(軟刪放刪除鍵前)

    @admin.display(description="已產生 QR Code", boolean=True)
    def has_qrcode(self, obj):
        return obj.qrcode_count > 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get("deleted") == "deleted":
            qs = qs.filter(deleted_at__isnull=False)
        else:
            qs = qs.filter(deleted_at__isnull=True)
        return qs.annotate(qrcode_count=Count('qrcodes'))

    def has_delete_permission(self, request, obj=None):
        return False  # 停用硬刪除按鈕

    @admin.action(description="軟刪除選取的防偽碼")
    def soft_delete(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=now)
        self.message_user(request, f"已標記刪除 {updated} 筆防偽碼。")

    @admin.action(description="還原已刪除的防偽碼")
    def restore(self, request, queryset):
        updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(request, f"已還原 {updated} 筆防偽碼。")

    @admin.action(description="⚠️ 永久刪除（無法復原，僅限管理員）")
    def hard_delete(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "僅 superuser 可執行永久刪除。", level="error")
            return
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"已永久刪除 {count} 筆防偽碼。", level="warning")

    @admin.action(description="匯出選取項目為 CSV")
    def export_csv(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _antifakecode_rows(queryset)
        return _export_csv(rows, headers, "防偽碼")

    @admin.action(description="匯出選取項目為 Excel")
    def export_excel(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _antifakecode_rows(queryset)
        return _export_excel(rows, headers, "防偽碼")

    @admin.action(description="產生 QR Code")
    def generate_qrcode(self, request, queryset):
        base_url = SystemConfig.get('SITE_BASE_URL', '').rstrip('/')
        if not base_url:
            self.message_user(request, "請先在系統設定中設定 SITE_BASE_URL。", level="error")
            return
        created = 0
        for obj in queryset:
            url = f"{base_url}/?code={obj.code}"
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode()
            QrCodeRecord.objects.create(code=obj, full_url=url, image_b64=b64)
            created += 1
        self.message_user(request, f"已產生 {created} 筆 QR Code 記錄。")

    def get_readonly_fields(self, request, obj=None):
        if obj:  # 編輯既有記錄時，code 不可改
            return self.readonly_fields + ["code"]
        return self.readonly_fields

    def get_urls(self):
        return [
            path("batch-create/", self.admin_site.admin_view(self.batch_create_view),
                 name="antifake_antifakecode_batch_create"),
            path("<str:code>/detail/", self.admin_site.admin_view(self.code_detail_view),
                 name="antifake_antifakecode_detail"),
        ] + super().get_urls()

    def code_detail_view(self, request, code):
        try:
            obj = AntiFakeCode.objects.get(code=code)
        except AntiFakeCode.DoesNotExist:
            messages.error(request, f"防偽碼 {code} 不存在。")
            return redirect("../../../")

        logs = obj.logs.order_by("-verify_at")

        questionnaires = []
        for q in obj.questionnaire_responses.order_by("-created_at"):
            try:
                raw = json.loads(q.answers_json) if q.answers_json else {}
            except Exception:
                raw = {}
            city, clinic = "", ""
            for i in range(10):
                qid = raw.get(f"questObjectList[{i}].prodRltAdvQuesId", "")
                ans = raw.get(f"questObjectList[{i}].answer", "")
                if qid == "1985":
                    city = ans
                elif qid == "1983":
                    clinic = ans
            questionnaires.append({"obj": q, "city": city, "clinic": clinic})

        return render(request, "admin/antifake/antifakecode/code_detail.html", {
            **self.admin_site.each_context(request),
            "title": f"防偽碼詳情：{code}",
            "obj": obj,
            "logs": logs,
            "questionnaires": questionnaires,
            "opts": self.model._meta,
        })

    def batch_create_view(self, request):
        if request.method == "POST":
            action = request.POST.get("action")

            if action == "csv":
                f = request.FILES.get("csv_file")
                if not f:
                    messages.error(request, "請選擇 CSV 檔案。")
                    return redirect(".")
                text = f.read().decode("utf-8-sig")
                reader = csv.reader(io.StringIO(text))
                to_create, skipped = [], 0
                existing = set(AntiFakeCode.objects.values_list("code", flat=True))
                for row in reader:
                    if not row:
                        continue
                    code = row[0].strip()
                    notes = row[1].strip() if len(row) > 1 else ""
                    if not code or code in existing:
                        skipped += 1
                        continue
                    to_create.append(AntiFakeCode(code=code, notes=notes))
                    existing.add(code)
                AntiFakeCode.objects.bulk_create(to_create)
                messages.success(request, f"成功匯入 {len(to_create)} 筆，跳過 {skipped} 筆（重複或空白）。")

            elif action == "generate":
                count = min(int(request.POST.get("count", 10)), 10000)
                length = int(request.POST.get("length", 12))
                notes = request.POST.get("notes", "").strip()
                existing = set(AntiFakeCode.objects.values_list("code", flat=True))
                to_create = []
                attempts = 0
                while len(to_create) < count and attempts < count * 10:
                    code = _generate_code(length)
                    attempts += 1
                    if code not in existing:
                        to_create.append(AntiFakeCode(code=code, notes=notes))
                        existing.add(code)
                AntiFakeCode.objects.bulk_create(to_create)
                messages.success(request, f"成功產生並建立 {len(to_create)} 筆防偽碼。")

            return redirect("../")

        return render(request, "admin/antifake/antifakecode/batch_create.html", {
            **self.admin_site.each_context(request),
            "title": "批量新增防偽碼",
        })


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ["code", "verify_at", "verify_count_snapshot", "client_ip", "geo_lat", "geo_lng"]
    list_filter = ["verify_at"]
    search_fields = ["code__code", "client_ip"]
    readonly_fields = ["verify_at"]
    actions = ["export_csv", "export_excel"]

    @admin.action(description="匯出選取項目為 CSV")
    def export_csv(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _verificationlog_rows(queryset)
        return _export_csv(rows, headers, "驗證歷史")

    @admin.action(description="匯出選取項目為 Excel")
    def export_excel(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _verificationlog_rows(queryset)
        return _export_excel(rows, headers, "驗證歷史")

    def get_urls(self):
        return [
            path("anomaly/", self.admin_site.admin_view(self.anomaly_view),
                 name="antifake_verificationlog_anomaly"),
        ] + super().get_urls()

    def anomaly_view(self, request):
        now = timezone.now()
        since_24h = now - timedelta(hours=24)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ① 同碼 24h ≥5 次
        anomaly_codes_qs = (
            VerificationLog.objects
            .filter(verify_at__gte=since_24h)
            .values("code_id")
            .annotate(count=Count("id"))
            .filter(count__gte=5)
            .order_by("-count")
        )
        code_ids = [r["code_id"] for r in anomaly_codes_qs]
        totals = {
            c.pk: c.verify_count
            for c in AntiFakeCode.objects.filter(pk__in=code_ids)
        }
        anomaly_codes = []
        for row in anomaly_codes_qs:
            anomaly_codes.append({
                "code_id": row["code_id"],
                "count": row["count"],
                "total": totals.get(row["code_id"], "-"),
            })

        # ② 同 IP 今日 ≥10 個不同碼
        anomaly_ips = (
            VerificationLog.objects
            .filter(verify_at__gte=today_start)
            .exclude(client_ip="")
            .values("client_ip")
            .annotate(code_count=Count("code", distinct=True))
            .filter(code_count__gte=10)
            .order_by("-code_count")
        )

        # ③ 同 GPS 今日 ≥10 個不同碼
        anomaly_gps = (
            VerificationLog.objects
            .filter(verify_at__gte=today_start, geo_lat__isnull=False, geo_lng__isnull=False)
            .values("geo_lat", "geo_lng")
            .annotate(code_count=Count("code", distinct=True))
            .filter(code_count__gte=10)
            .order_by("-code_count")
        )

        return render(request, "admin/antifake/verificationlog/anomaly.html", {
            **self.admin_site.each_context(request),
            "title": "異常檢測報表",
            "now": now.strftime("%Y-%m-%d %H:%M"),
            "anomaly_codes": anomaly_codes,
            "anomaly_ips": list(anomaly_ips),
            "anomaly_gps": list(anomaly_gps),
        })


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ["file_no", "filename", "content_type", "file_size", "uploaded_at"]
    readonly_fields = ["file_no", "uploaded_at"]


@admin.register(ContactTicket)
class ContactTicketAdmin(admin.ModelAdmin):
    list_display = ["legal_name", "email", "phone", "prod_seq", "prob_type", "created_at"]
    list_filter = ["prob_type", "is_member"]
    search_fields = ["legal_name", "email", "prod_seq"]
    readonly_fields = ["created_at"]
    actions = ["export_csv", "export_excel"]

    @admin.action(description="匯出選取項目為 CSV")
    def export_csv(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _contactticket_rows(queryset)
        return _export_csv(rows, headers, "聯絡我們")

    @admin.action(description="匯出選取項目為 Excel")
    def export_excel(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _contactticket_rows(queryset)
        return _export_excel(rows, headers, "聯絡我們")


@admin.register(SupplementReport)
class SupplementReportAdmin(admin.ModelAdmin):
    list_display = ["contact_info", "uploaded_file", "created_at"]
    readonly_fields = ["created_at"]
    actions = ["export_csv", "export_excel"]

    @admin.action(description="匯出選取項目為 CSV")
    def export_csv(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _supplementreport_rows(queryset)
        return _export_csv(rows, headers, "補件回報")

    @admin.action(description="匯出選取項目為 Excel")
    def export_excel(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _supplementreport_rows(queryset)
        return _export_excel(rows, headers, "補件回報")


@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ["code", "created_at"]
    search_fields = ["code__code"]
    readonly_fields = ["created_at"]
    actions = ["export_csv", "export_excel"]

    @admin.action(description="匯出選取項目為 CSV")
    def export_csv(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _questionnaireresponse_rows(queryset)
        return _export_csv(rows, headers, "問卷回應")

    @admin.action(description="匯出選取項目為 Excel")
    def export_excel(self, request, queryset):
        if not _can_export(request):
            self.message_user(request, "您沒有匯出權限。", level="error")
            return
        headers, rows = _questionnaireresponse_rows(queryset)
        return _export_excel(rows, headers, "問卷回應")


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]
    readonly_fields = ["key", "updated_at"]
    fields = ["key", "value", "description", "updated_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QrCodeRecord)
class QrCodeRecordAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_url', 'qr_preview', 'created_at']
    readonly_fields = ['code', 'full_url', 'qr_image_large', 'created_at']
    fields = ['code', 'full_url', 'qr_image_large', 'created_at']
    ordering = ['-created_at']
    actions = ['print_qrcode', 'delete_selected'] # 刪除鍵放末尾

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        return [
            path('print/', self.admin_site.admin_view(self.print_view),
                 name='antifake_qrcoderecord_print'),
        ] + super().get_urls()

    @admin.action(description='列印選取 QR Code')
    def print_qrcode(self, request, queryset):
        request.session['print_qrcode_ids'] = list(queryset.values_list('pk', flat=True))
        return redirect('admin:antifake_qrcoderecord_print')
    
    @admin.action(description='⚠️ 刪除所選的 QR Code 紀錄')
    def delete_selected(self, request, queryset):
        from django.contrib.admin.actions import delete_selected as _delete
        return _delete(self, request, queryset)

    def print_view(self, request):
        ids = request.session.pop('print_qrcode_ids', [])
        records = QrCodeRecord.objects.filter(pk__in=ids).select_related('code').order_by('code_id')
        return render(request, 'admin/antifake/qrcoderecord/print.html', {
            'records': records,
        })

    def qr_preview(self, obj):
        return format_html(
            '<img src="data:image/png;base64,{}" width="60" height="60" style="border:1px solid #ccc;">',
            obj.image_b64
        )
    qr_preview.short_description = 'QR Code'

    def qr_image_large(self, obj):
        return format_html(
            '<img src="data:image/png;base64,{}" width="200" height="200">',
            obj.image_b64
        )
    qr_image_large.short_description = 'QR Code 圖片'


admin.site.unregister(User)

@admin.register(User)
class SimpleUserAdmin(BaseUserAdmin):
    list_display = ["username", "is_staff", "is_active", "get_groups"]
    list_filter = ["is_staff", "is_active", "groups"]
    search_fields = ["username"]

    fieldsets = (
        ("帳號", {"fields": ("username", "password")}),
        ("權限", {"fields": ("is_active", "is_staff", "groups")}),
    )
    add_fieldsets = (
        ("建立帳號", {"fields": ("username", "password1", "password2")}),
        ("權限", {"fields": ("is_active", "is_staff", "groups")}),
    )
    filter_horizontal = []

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups":
            kwargs["widget"] = CheckboxSelectMultiple()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(description="群組")
    def get_groups(self, obj):
        return "、".join(g.name for g in obj.groups.all()) or "（無）"


# ── 後台首頁 Dashboard patch ──────────────────────────────────────────────────
# 使用 each_context 而非 index，因為 each_context 在 request 時期才被動態查找，
# 不受 URL pattern 建立時機影響。

from django.core.paginator import Paginator as _Paginator

_orig_each_context = admin.AdminSite.each_context


def _dashboard_each_context(self, request):
    context = _orig_each_context(self, request)
    if request.user.is_authenticated:
        search_q = request.GET.get("q", "").strip()
        warn_filter = request.GET.get("warn") == "1"
        qs = (
            AntiFakeCode.objects
            .filter(verify_count__gte=1, deleted_at__isnull=True)
            .order_by("-last_verify_at")
        )
        if search_q:
            qs = qs.filter(code__icontains=search_q)
        if warn_filter:
            qs = qs.filter(verify_count__gte=3)
        paginator = _Paginator(qs, 20)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        context["dashboard_page"] = page_obj
        context["dashboard_search"] = search_q
        context["dashboard_warn_filter"] = warn_filter
    return context


admin.AdminSite.each_context = _dashboard_each_context
