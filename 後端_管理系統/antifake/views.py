"""
antifake/views.py
所有頁面與 API 端點。
"""
import io
import os
import base64
import json as json_lib
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse  # FileResponse still used by get_img
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.shortcuts import redirect, render

from .models import AntiFakeCode, VerificationLog, UploadedFile, \
    ContactTicket, SupplementReport, QuestionnaireResponse, SystemConfig
from .translations import TRANS

# ── 工具 ────────────────────────────────────────────────────────────────────

PAGES_DIR = os.path.join(settings.BASE_DIR, 'project', 'pages')
UPLOAD_DIR = os.path.join(settings.BASE_DIR, 'project', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _alert_back(msg):
    return HttpResponse(
        f'<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>'
        f'<script>alert("{msg}"); history.back();</script></body></html>',
        content_type='text/html; charset=utf-8'
    )


def _get_lang(request):
    return request.session.get('lang', 'CHT').upper()


def _render_page(request, filename, extra_ctx=None):
    lang = _get_lang(request)
    t = TRANS.get(lang, TRANS['CHT'])
    base, ext = os.path.splitext(filename)
    variant = f'{base}_{lang.lower()}{ext}'
    tpl = variant if os.path.exists(os.path.join(PAGES_DIR, variant)) else filename
    ctx = {
        't': t,
        'lang': lang,
        'has_verify_result': 'last_verify' in request.session,
        **(extra_ctx or {}),
    }
    return render(request, tpl, ctx)


def _compute_captcha(seed):
    chars = '23456789'
    code = ''
    s = seed
    for i in range(4):
        code += chars[(s * 7 + i * 13 + 17) % len(chars)]
        s = (s * 31 + 7) % 97
    return code


def _client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ── 頁面路由 ─────────────────────────────────────────────────────────────────

def index(request):
    code_param = request.GET.get('code', '').strip()
    if code_param:
        return _process_qr_scan(request, code_param)
    return _render_page(request, 'index.html')


def _process_qr_scan(request, code):
    lang = _get_lang(request)
    block_content_7 = SystemConfig.get('BLOCK_CONTENT_7', '')
    try:
        code_obj = AntiFakeCode.objects.get(code=code, is_active=True, deleted_at__isnull=True)
        code_obj.verify_count += 1
        if code_obj.first_verify_at is None:
            code_obj.first_verify_at = timezone.now()
        code_obj.last_verify_at = timezone.now()
        code_obj.save()
        n = code_obj.verify_count
        VerificationLog.objects.create(
            code=code_obj,
            verify_count_snapshot=n,
            client_ip=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        request.session['last_verify'] = {'checksum': code, 'is_qkit': True, 'verify_count': n}
        return _render_page(request, 'checkTruth.html', {
            'checksum': code, 'is_qkit': True,
            'fake_result': _build_fake_result(n, lang),
            'block_content_7': block_content_7,
        })
    except AntiFakeCode.DoesNotExist:
        VerificationLog.objects.create(
            code=None,
            verify_count_snapshot=0,
            client_ip=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        request.session['last_verify'] = {'checksum': code, 'is_qkit': False, 'verify_count': 0}
        return _render_page(request, 'checkTruth.html', {
            'checksum': code, 'is_qkit': False,
            'fake_result': '',
            'block_content_7': block_content_7,
        })


def verify_result(request):
    last = request.session.get('last_verify')
    if not last:
        return redirect('/')
    lang = _get_lang(request)
    block_content_7 = SystemConfig.get('BLOCK_CONTENT_7', '')
    return _render_page(request, 'checkTruth.html', {
        'checksum': last['checksum'],
        'is_qkit': last['is_qkit'],
        'fake_result': _build_fake_result(last['verify_count'], lang) if last['is_qkit'] else '',
        'block_content_7': block_content_7,
    })


def main_entry(request):
    last = request.session.get('last_verify', {})
    lang = _get_lang(request)
    extra = {}
    if last.get('is_qkit'):
        t = TRANS.get(lang, TRANS['CHT'])
        extra = {
            'is_qkit': True,
            'fake_result': t['fake_result_final'],
        }
    return _render_page(request, 'mainEntry.html', extra)


def mem_login(request):
    if request.method == 'POST':
        return redirect('/memLogin.do?msg=maintenance')
    return _render_page(request, 'memLogin.html')


@csrf_exempt
def login_check(request):
    return _alert_back('功能維護中，暫不開放。')


def take_membership_terms(request):
    return _alert_back('功能維護中，暫不開放。')


@csrf_exempt
@require_POST
def mem_forgot(request):
    return JsonResponse({'data': None})


def _build_fake_result(n, lang='CHT'):
    threshold = int(SystemConfig.get('VERIFY_WARN_THRESHOLD', '2'))
    phone = SystemConfig.get('SERVICE_PHONE', '0800-004-088')
    t = TRANS.get(lang, TRANS['CHT'])
    if n >= threshold:
        return t['fake_result_warn'].format(n=n, phone=phone, phone_no=phone.replace('-', ''))
    return t['fake_result_ok'].format(n=n)


@csrf_exempt
def check_truth(request):
    lang = _get_lang(request)
    block_content_7 = SystemConfig.get('BLOCK_CONTENT_7', '')
    if request.method == 'POST':
        code = request.POST.get('authCodeCde', '').strip()
        valid_code_input = request.POST.get('validCode', '').strip()
        captcha_seed = int(request.POST.get('captchaSeed', 0) or 0)
        if valid_code_input != _compute_captcha(captcha_seed):
            return _alert_back('驗證碼輸入錯誤')
        try:
            code_obj = AntiFakeCode.objects.get(code=code, is_active=True, deleted_at__isnull=True)
            code_obj.verify_count += 1
            if code_obj.first_verify_at is None:
                code_obj.first_verify_at = timezone.now()
            code_obj.last_verify_at = timezone.now()
            code_obj.save()
            n = code_obj.verify_count
            VerificationLog.objects.create(
                code=code_obj,
                verify_count_snapshot=n,
                client_ip=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            request.session['last_verify'] = {'checksum': code, 'is_qkit': True, 'verify_count': n}
            return _render_page(request, 'checkTruth.html', {
                'checksum': code, 'is_qkit': True,
                'fake_result': _build_fake_result(n, lang),
                'block_content_7': block_content_7,
            })
        except AntiFakeCode.DoesNotExist:
            VerificationLog.objects.create(
                code=None,
                verify_count_snapshot=0,
                client_ip=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            request.session['last_verify'] = {'checksum': code, 'is_qkit': False, 'verify_count': 0}
            return _render_page(request, 'checkTruth.html', {
                'checksum': code, 'is_qkit': False,
                'fake_result': '',
                'block_content_7': block_content_7,
            })
    return _render_page(request, 'checkTruth.html', {
        'checksum': '', 'is_qkit': False,
        'fake_result': '',
        'block_content_7': block_content_7,
    })


def gen_detem_item_form(request):
    if request.method == 'POST':
        return redirect('/genDetemItemForm.do')
    return _render_page(request, 'genDetemItemForm.html')


def contact(request):
    if request.method == 'POST':
        _save_contact_ticket(request)
        return redirect('/contact.do')
    return _render_page(request, 'contact.html')


def questionnaire(request):
    return _render_page(request, 'Questionnaire.html')


def advanced_match(request):
    return redirect('/Questionnaire.do')


def logout_check(request):
    return redirect('/mainEntry.do')


# ── 核心 API ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def call_qkit(request):
    checksum = request.POST.get('checksum', '').strip()
    lang = _get_lang(request)
    threshold = int(SystemConfig.get('VERIFY_WARN_THRESHOLD', '2'))

    try:
        code_obj = AntiFakeCode.objects.get(code=checksum, is_active=True, deleted_at__isnull=True)
        n = code_obj.verify_count
        return JsonResponse({
            'isSystemMatch': 'false',
            'data': {'fakeResult': _build_fake_result(n, lang), 'fakeJudgeImg': ''},
            'isQuest': '0' if n >= threshold else '1',
        })
    except AntiFakeCode.DoesNotExist:
        return JsonResponse({
            'isSystemMatch': 'false',
            'data': {'fakeResult': '', 'fakeJudgeImg': ''},
            'isQuest': '1',
        })


@csrf_exempt
@require_POST
def non_qkit(request):
    return JsonResponse({'success': True})


def _reverse_geocode(lat, lng):
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lng}&format=json&accept-language=zh-TW"
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'AntifakeVerifySystem/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json_lib.loads(resp.read().decode())
        addr = data.get('address', {})
        city = addr.get('city') or addr.get('county') or addr.get('state', '')
        district = addr.get('city_district') or addr.get('town') or addr.get('suburb') or ''
        return (city + district).strip() or data.get('display_name', '')[:50]
    except Exception:
        return ''


@csrf_exempt
@require_POST
def update_geo_location(request):
    # 把 GPS 更新到最新一筆 VerificationLog（若有）
    lat = request.POST.get('location.latitude')
    lng = request.POST.get('location.longitude')
    acc = request.POST.get('location.accuracy')
    last_log = VerificationLog.objects.order_by('-verify_at').first()
    if last_log and lat and lng:
        last_log.geo_lat = lat
        last_log.geo_lng = lng
        last_log.geo_accuracy = acc
        last_log.geo_city = _reverse_geocode(lat, lng)
        last_log.save()
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def page_event_log(request):
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def load_block_cont(request):
    block_id = request.POST.get('blockId', '')
    cont = SystemConfig.get(f'BLOCK_CONTENT_{block_id}', '')
    return JsonResponse({'cont': cont})


@csrf_exempt
@require_POST
def front_lang_change(request):
    lang = request.POST.get('langType', 'CHT').upper()
    request.session['lang'] = lang
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def get_sys_msg_front(request):
    lang = _get_lang(request)
    syscde = request.POST.get('syscde', '')
    t = TRANS.get(lang, TRANS['CHT'])
    msg = t['sys'].get(syscde, syscde)
    return JsonResponse({'returnMsg': 'success', 'msg': msg})


# ── 圖片 / 驗證碼 API ────────────────────────────────────────────────────────

_CAPTCHA_FONT = None

def _get_captcha_font(size=22):
    global _CAPTCHA_FONT
    if _CAPTCHA_FONT is None:
        for path in [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]:
            try:
                _CAPTCHA_FONT = ImageFont.truetype(path, size)
                break
            except (IOError, OSError):
                pass
        if _CAPTCHA_FONT is None:
            _CAPTCHA_FONT = ImageFont.load_default(size=size)
    return _CAPTCHA_FONT


@require_GET
def gen_valid_code(request):
    seed = int(request.GET.get('code', 0) or 0)
    chars = '23456789'
    code = ''
    s = seed
    for i in range(4):
        code += chars[(s * 7 + i * 13 + 17) % len(chars)]
        s = (s * 31 + 7) % 97

    img = Image.new('RGB', (120, 40), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 不規則灰色雜點
    ns = seed
    for _ in range(80):
        ns = (ns * 31 + 7) % 9973
        x = ns % 120
        ns = (ns * 31 + 7) % 9973
        y = ns % 40
        ns = (ns * 31 + 7) % 9973
        g = 150 + ns % 80  # 150~229 淺灰
        draw.point((x, y), fill=(g, g, g))

    # 淺灰邊框
    draw.rectangle([0, 0, 119, 39], outline=(200, 200, 200))

    # 淺藍數字
    font = _get_captcha_font(22)
    blue = (102, 153, 204)
    cell_w = 30
    for i, digit in enumerate(code):
        cx = cell_w * i + cell_w // 2
        bbox = draw.textbbox((0, 0), digit, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, (40 - th) // 2 - 1), digit, fill=blue, font=font)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='image/jpeg')


@require_GET
def get_img(request):
    file_no = request.GET.get('fileNo', '0')

    # 先查 DB
    try:
        f = UploadedFile.objects.get(file_no=int(file_no))
        path = f.storage_path
        if os.path.exists(path):
            return FileResponse(open(path, 'rb'), content_type=f.content_type or 'image/jpeg')
    except (UploadedFile.DoesNotExist, ValueError):
        pass

    # 查本地靜態檔案（key_images 或 generic 目錄）
    for candidate in [
        os.path.join(PAGES_DIR, '..', 'frontPages', 'images', 'key_images', f'fileNo_{file_no}.jpg'),
        os.path.join(PAGES_DIR, '..', 'generic', f'getImg{file_no}.jpg'),
    ]:
        candidate = os.path.abspath(candidate)
        if os.path.exists(candidate):
            return FileResponse(open(candidate, 'rb'), content_type='image/jpeg')

    # 無對應檔案 → SVG 佔位圖
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
        f'<rect width="300" height="200" fill="#ccc"/>'
        f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
        f'font-family="sans-serif" font-size="14" fill="#666">fileNo: {file_no}</text>'
        f'</svg>'
    )
    return HttpResponse(svg, content_type='image/svg+xml')


@csrf_exempt
@require_POST
def upload_img(request):
    b64 = request.POST.get('uploadBase64Img', '')
    filename = request.POST.get('uploadFileName', 'upload.jpg')

    if not b64:
        return JsonResponse({'status': False})

    # base64 解碼存檔
    try:
        b64_clean = b64.strip('"')   # 前端有多包一層 JSON.stringify
        img_bytes = base64.b64decode(b64_clean)
    except Exception:
        return JsonResponse({'status': False})

    ext = os.path.splitext(filename)[1] or '.jpg'
    content_type = 'image/jpeg' if ext.lower() in ('.jpg', '.jpeg') else 'image/png'

    file_record = UploadedFile.objects.create(
        filename=filename,
        content_type=content_type,
        file_size=len(img_bytes),
        storage_path='',
        uploaded_by_session=request.session.session_key or '',
    )
    save_path = os.path.join(UPLOAD_DIR, f'{file_record.file_no}{ext}')
    with open(save_path, 'wb') as fp:
        fp.write(img_bytes)
    file_record.storage_path = save_path
    file_record.save()

    return JsonResponse({'status': True, 'fileNo': file_record.file_no})


@csrf_exempt
@require_POST
def upload_temp(request):
    # contact.do 用的上傳 endpoint，欄位名為 fileBase64（已 JSON.stringify 的 base64）
    b64 = request.POST.get('fileBase64', '')
    if not b64:
        return JsonResponse({'status': False}, status=400)
    try:
        b64_clean = b64.strip('"')
        img_bytes = base64.b64decode(b64_clean)
    except Exception:
        return JsonResponse({'status': False}, status=400)

    file_record = UploadedFile.objects.create(
        filename='upload.jpg',
        content_type='image/jpeg',
        file_size=len(img_bytes),
        storage_path='',
        uploaded_by_session=request.session.session_key or '',
    )
    save_path = os.path.join(UPLOAD_DIR, f'{file_record.file_no}.jpg')
    with open(save_path, 'wb') as fp:
        fp.write(img_bytes)
    file_record.storage_path = save_path
    file_record.save()

    return JsonResponse({'status': True, 'fileNo': file_record.file_no})


# ── 表單 API ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def save_form_fields(request):
    contact_info = ''
    uploaded_file_no = None
    for key, val in request.POST.items():
        if 'fieldValue' in key and val:
            if val.isdigit():
                uploaded_file_no = int(val)
            else:
                contact_info = val

    uploaded_file = None
    if uploaded_file_no:
        try:
            uploaded_file = UploadedFile.objects.get(file_no=uploaded_file_no)
        except UploadedFile.DoesNotExist:
            pass

    SupplementReport.objects.create(
        contact_info=contact_info,
        uploaded_file=uploaded_file,
    )
    return JsonResponse({'status': True})


@csrf_exempt
@require_POST
def save_answer_record(request):
    answers = {k: v for k, v in request.POST.items()}
    code = None
    checksum = request.session.get('last_verify', {}).get('checksum', '')
    if checksum:
        try:
            code = AntiFakeCode.objects.get(code=checksum)
        except AntiFakeCode.DoesNotExist:
            pass
    QuestionnaireResponse.objects.create(
        code=code,
        answers_json=json_lib.dumps(answers, ensure_ascii=False),
    )
    return JsonResponse({'finish': True})


@csrf_exempt
@require_GET
def get_all_question(request):
    return JsonResponse({
        'questionList': [
            {
                'prodRltAdvQuesId': 2167, 'detemItem': '3', 'isCal': 'N',
                'ansQuzIsMust': 1, 'rightAns': 'null', 'isOthOpt': 'N',
                'imgList': ["<img src='/generic/getImg.do?fileNo=73186' style='width:auto;max-width:100%;height:auto;'>"],
                'quesOptionList': None, 'remarkOptionList': None,
                'advQuesVO': {'ansMold': '11', 'quesDesc': '<p><span style="font-size:16px;">請您拍照上傳包裝盒上的中文標籤 </span></p>'},
            },
            {
                'prodRltAdvQuesId': 2168, 'detemItem': '1', 'isCal': 'N',
                'ansQuzIsMust': 1, 'rightAns': '', 'isOthOpt': 'N',
                'imgList': ["<img src='/generic/getImg.do?fileNo=67567' style='width:auto;max-width:100%;height:auto;'>"],
                'quesOptionList': None, 'remarkOptionList': None,
                'advQuesVO': {'ansMold': '11', 'quesDesc': '<p><span style="font-size:16px;">請您拍照上傳機器上的雷射防偽標籤（鳳凰電波）</span></p>'},
            },
            {
                'prodRltAdvQuesId': 1985, 'detemItem': '1', 'isCal': 'N',
                'ansQuzIsMust': 1, 'rightAns': '', 'isOthOpt': 'N',
                'imgList': None, 'remarkOptionList': None,
                'quesOptionList': [{'quesOptDesc': v} for v in [
                    '北部地區-臺北市', '北部地區-新北市', '北部地區-基隆市', '北部地區-桃園市',
                    '北部地區-新竹市', '北部地區-新竹縣', '北部地區-宜蘭縣',
                    '中部地區-臺中市', '中部地區-苗栗縣', '中部地區-彰化縣', '中部地區-南投縣', '中部地區-雲林縣',
                    '南部地區-高雄市', '南部地區-臺南市', '南部地區-嘉義市', '南部地區-嘉義縣', '南部地區-屏東縣',
                    '東部地區-花蓮縣', '東部地區-臺東縣 ',
                    '離島地區-澎湖縣 ', '離島地區-金門縣 ', '離島地區-連江縣', '其他地區',
                ]],
                'advQuesVO': {'ansMold': '6', 'quesDesc': '<p><span style="font-size:16px;">請選擇您施打療程的城市</span></p>'},
            },
            {
                'prodRltAdvQuesId': 1983, 'detemItem': '1', 'isCal': 'N',
                'ansQuzIsMust': 1, 'rightAns': '醫療院所名稱', 'isOthOpt': 'N',
                'imgList': None, 'quesOptionList': None, 'remarkOptionList': None,
                'advQuesVO': {'ansMold': '1', 'quesDesc': '<p><span style="font-size:16px;">請填寫施打療程的醫療院所名稱，如有分店也請同步填寫</span></p>'},
            },
        ]
    })


# ── 聯絡我們存檔 ──────────────────────────────────────────────────────────────

def _save_contact_ticket(request):
    def g(k):
        return request.POST.get(k, '')

    file_no = g('fileNo')
    uploaded_file = None
    if file_no:
        try:
            uploaded_file = UploadedFile.objects.get(file_no=int(file_no))
        except (UploadedFile.DoesNotExist, ValueError):
            pass

    pur_date = g('purDate') or None
    pur_price_raw = g('purPrice')
    pur_price = float(pur_price_raw) if pur_price_raw else None

    ContactTicket.objects.create(
        is_member=g('isMember') == 'T',
        legal_name=g('legalName'),
        email=g('email'),
        country_code=g('countryCode'),
        phone=g('phone'),
        sex=g('sex'),
        prod_seq=g('prodSeq'),
        prob_type=g('probType'),
        pur_country=g('purCountry'),
        pur_city=g('purCity'),
        store_type=g('storeType'),
        pur_store=g('purStore'),
        pur_date=pur_date,
        pur_price=pur_price,
        pur_price_currency=g('purPriceCurrency'),
        prob_desc=g('probDesc'),
        uploaded_file=uploaded_file,
        agree_to_terms=g('agreeToTerms') == 'true',
    )


@csrf_exempt
@require_POST
def ctact_add(request):
    # contact.html 表單 AJAX 送出（欄位名用原站 Spring 格式）
    def g(k):
        return request.POST.get(k, '')

    file_no = g('fileNo') or g('file')
    uploaded_file = None
    if file_no:
        try:
            uploaded_file = UploadedFile.objects.get(file_no=int(file_no))
        except (UploadedFile.DoesNotExist, ValueError):
            pass

    pur_date = g('memCont.purDate') or None
    pur_price_raw = g('purPrice')
    pur_price = float(pur_price_raw) if pur_price_raw else None

    try:
        ContactTicket.objects.create(
            is_member=g('memCont.isMem') in ('T', '1'),
            legal_name=g('idv.idvProf.legalNm'),
            email=g('idv.emailCtact.emailAddr'),
            country_code=g('idv.tlphnCtact.countryCde'),
            phone=g('idv.tlphnCtact.tlphnNbr'),
            sex=g('idv.idvProf.sex'),
            prod_seq=g('memCont.prodSeq'),
            prob_type=g('memCont.probTyp'),
            pur_country=g('memCont.purCountry'),
            pur_city=g('memCont.purCity'),
            store_type=g('memCont.storeTyp'),
            pur_store=g('memCont.purStore'),
            pur_date=pur_date,
            pur_price=pur_price,
            pur_price_currency=g('memCont.purPriceCurrency'),
            prob_desc=g('memCont.probDesc'),
            uploaded_file=uploaded_file,
            agree_to_terms=g('memCont.agreeToTerms') == '1',
        )
        return JsonResponse({'msg': 'success', 'returnMsg': '感謝您的聯絡，我們將盡快與您聯繫。'})
    except Exception:
        return JsonResponse({'msg': 'error', 'returnMsg': '系統錯誤，請稍後再試。'}, status=500)
