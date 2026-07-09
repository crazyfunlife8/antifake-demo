import base64
import csv
import io
import json
import random
from datetime import timedelta

import openpyxl
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.forms import CheckboxSelectMultiple
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.utils.html import format_html, mark_safe
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils import timezone
from .models import (
    AntiFakeCode, VerificationLog, UploadedFile,
    ContactTicket, SupplementReport, QuestionnaireResponse, SystemConfig,
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
    headers = ["防偽碼", "驗證時間", "當次次數", "IP", "地點", "緯度", "經度", "定位精度", "UA"]
    rows = [[o.code_id, o.verify_at, o.verify_count_snapshot,
             o.client_ip, o.geo_city, o.geo_lat, o.geo_lng, o.geo_accuracy, o.user_agent] for o in qs]
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
    fields = ["verify_at", "verify_count_snapshot", "client_ip", "geo_city", "user_agent"]
    readonly_fields = ["verify_at", "verify_count_snapshot", "client_ip", "geo_city", "user_agent"]
    extra = 0
    can_delete = False
    ordering = ["-verify_at"]
    verbose_name = "驗證記錄"
    verbose_name_plural = "驗證歷史（時間倒序）"


@admin.register(AntiFakeCode)
class AntiFakeCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "verify_count", "is_active", "last_verify_at", "notes", "created_at"]
    list_filter = [DeletedFilter, "is_active", VerifyCountFilter, "created_at"]
    search_fields = ["code", "notes"]
    readonly_fields = ["verify_count", "first_verify_at", "last_verify_at", "created_at", "updated_at", "deleted_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    inlines = [VerificationLogInline]
    actions = ["export_csv", "export_excel", "restore", "soft_delete", "hard_delete"] # 刪除鍵放末尾(軟刪放刪除鍵前)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get("deleted") == "deleted":
            qs = qs.filter(deleted_at__isnull=False)
        else:
            qs = qs.filter(deleted_at__isnull=True)
        return qs

    def has_add_permission(self, request):
        return False  # 停用單筆新增，改用批量新增

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
                scan_log = obj.logs.filter(verify_at__lte=q.created_at).order_by("-verify_at").first()
            questionnaires.append({
                "obj": q,
                "city": city,
                "clinic": clinic,
                "scan_time": scan_log.verify_at if scan_log else None,
            })

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

            if action == "generate":
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

                base_url = SystemConfig.get('SITE_BASE_URL', '').rstrip('/')
                if not base_url:
                    messages.error(request, "請先在系統設定中設定 SITE_BASE_URL。")
                    return redirect("../")
                headers = ["防偽碼", "掃描網址"]
                rows = [[obj.code, f"{base_url}/?code={obj.code}"] for obj in to_create]
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.append(headers)
                for row in rows:
                    ws.append(row)
                buf = io.BytesIO()
                wb.save(buf)
                excel_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                changelist_url = reverse('admin:antifake_antifakecode_changelist')
                return render(request, "admin/antifake/antifakecode/batch_create_download.html", {
                    **self.admin_site.each_context(request),
                    "excel_b64": excel_b64,
                    "count": len(to_create),
                    "changelist_url": changelist_url,
                })

            return redirect("../")

        return render(request, "admin/antifake/antifakecode/batch_create.html", {
            **self.admin_site.each_context(request),
            "title": "批量新增防偽碼",
        })


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ["code", "verify_at", "verify_count_snapshot", "client_ip", "geo_city"]
    list_filter = ["verify_at"]
    search_fields = ["code__code", "client_ip"]
    readonly_fields = ["verify_at"]
    fieldsets = [
        (None, {"fields": [
            "code", "verify_at", "verify_count_snapshot",
            "client_ip", "user_agent",
            "geo_city",
            "auth_token", "request_info_id",
        ]}),
    ]
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
    list_display = ["file_no", "filename", "content_type", "file_size", "uploaded_at", "download_link"]
    readonly_fields = ["file_no", "uploaded_at"]
    ordering = ["-file_size"]

    def get_urls(self):
        return [
            path("<int:file_no>/download/", self.admin_site.admin_view(self.download_view),
                 name="antifake_uploadedfile_download"),
        ] + super().get_urls()

    @admin.display(description="下載")
    def download_link(self, obj):
        url = reverse("admin:antifake_uploadedfile_download", args=[obj.file_no])
        return format_html('<a href="{}">⬇ 下載</a>', url)

    def download_view(self, request, file_no):
        import os
        try:
            f = UploadedFile.objects.get(file_no=file_no)
        except UploadedFile.DoesNotExist:
            messages.error(request, "找不到此檔案記錄。")
            return redirect("../../")
        if not f.storage_path or not os.path.exists(f.storage_path):
            messages.error(request, f"實體檔案不存在：{f.storage_path}")
            return redirect("../../")
        filename = f.filename or f"file_{file_no}"
        response = FileResponse(open(f.storage_path, 'rb'), content_type=f.content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


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
    readonly_fields = ["created_at", "download_link"]
    fieldsets = [
        (None, {"fields": ["contact_info", ("uploaded_file", "download_link"), "created_at"]}),
    ]
    actions = ["export_csv", "export_excel"]

    @admin.display(description="下載圖片")
    def download_link(self, obj):
        if obj.uploaded_file:
            url = reverse("admin:antifake_uploadedfile_download", args=[obj.uploaded_file.file_no])
            return format_html('<a href="{}" class="button">⬇ 下載圖片</a>', url)
        return "（無附件）"

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
    list_display = ["code", "answers_summary", "created_at"]
    search_fields = ["code__code"]
    readonly_fields = ["created_at", "formatted_answers"]
    fieldsets = [
        (None, {"fields": ["code", "created_at", "formatted_answers"]}),
    ]
    actions = ["export_csv", "export_excel"]

    @admin.display(description="回答摘要")
    def answers_summary(self, obj):
        try:
            raw = json.loads(obj.answers_json) if obj.answers_json else {}
        except Exception:
            return "(解析失敗)"
        city, clinic = "", ""
        for i in range(10):
            qid = raw.get(f"questObjectList[{i}].prodRltAdvQuesId", "")
            ans = raw.get(f"questObjectList[{i}].answer", "")
            if qid == "1985":
                city = ans
            elif qid == "1983":
                clinic = ans
        parts = [p for p in [city, clinic] if p]
        return " / ".join(parts) or "(無)"

    @admin.display(description="回答內容")
    def formatted_answers(self, obj):
        import re
        from urllib.parse import unquote
        try:
            raw = json.loads(obj.answers_json) if obj.answers_json else {}
        except Exception:
            return format_html('<pre style="white-space:pre-wrap">{}</pre>', obj.answers_json)

        rows = []
        for i in range(10):
            if not raw.get(f"questObjectList[{i}].prodRltAdvQuesId"):
                break
            ans_mold = raw.get(f"questObjectList[{i}].ansMold", "")
            desc_raw = raw.get(f"questObjectList[{i}].quesDesc", "")
            desc_text = re.sub(r'<[^>]+>', '', unquote(desc_raw)).strip() or f"第 {i + 1} 題"
            ans = raw.get(f"questObjectList[{i}].answer", "")

            if ans_mold == "11" and ans.isdigit():
                url = reverse("admin:antifake_uploadedfile_download", args=[int(ans)])
                ans_cell = format_html('<a href="{}">⬇ 下載圖片 (fileNo={})</a>', url, ans)
            elif ans:
                ans_cell = format_html('{}', ans)
            else:
                ans_cell = mark_safe('<span style="color:#999">（未填）</span>')

            rows.append(format_html(
                '<tr style="border-bottom:1px solid #eee">'
                '<td style="padding:8px 16px 8px 0;font-weight:bold;vertical-align:top;width:45%">{}</td>'
                '<td style="padding:8px 0">{}</td>'
                '</tr>',
                desc_text,
                ans_cell,
            ))

        if not rows:
            return mark_safe('<span style="color:#999">(無資料)</span>')

        return format_html(
            '<table style="width:100%;border-collapse:collapse;margin-top:4px">{}</table>',
            mark_safe(''.join(rows)),
        )

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
