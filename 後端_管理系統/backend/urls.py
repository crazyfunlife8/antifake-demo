from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings
import os

from antifake import views

PROJECT_DIR = os.path.join(settings.BASE_DIR, 'project')

urlpatterns = [
    # ── 管理後台 ────────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── 頁面路由 ────────────────────────────────────────────────────────────
    path('', views.index),
    path('verifyResult.do', views.verify_result),
    path('mainEntry.do', views.main_entry),
    path('memLogin.do', views.mem_login),
    path('loginCheck.do', views.login_check),
    path('takeMembershipTerms.do', views.take_membership_terms),
    path('memForgot.do', views.mem_forgot),
    path('checkTruth.do', views.check_truth),
    path('genDetemItemForm.do', views.gen_detem_item_form),
    path('contact.do', views.contact),
    path('Questionnaire.do', views.questionnaire),
    path('AdvancedMatch.do', views.advanced_match),
    path('logoutCheck.do', views.logout_check),

    # ── AJAX API ────────────────────────────────────────────────────────────
    path('callQkit.do', views.call_qkit),
    path('nonQkit.do', views.non_qkit),
    path('updateGeoLocation.do', views.update_geo_location),
    path('pageEventLog.do', views.page_event_log),
    path('loadBlockCont.do', views.load_block_cont),
    path('saveFormFields.do', views.save_form_fields),
    path('ctactAdd.do', views.ctact_add),
    path('saveAnswerRecord.do', views.save_answer_record),
    path('getAllQuestion.do', views.get_all_question),

    # ── generic API ─────────────────────────────────────────────────────────
    path('generic/frontLangChange.do', views.front_lang_change),
    path('generic/getSysMsgFront.do', views.get_sys_msg_front),
    path('generic/genValidCode.do', views.gen_valid_code),
    path('generic/getImg.do', views.get_img),
    path('generic/uploadImg.do', views.upload_img),
    path('generic/uploadTemp.do', views.upload_temp),

    # ── 靜態資源（CSS / JS / 圖片）─────────────────────────────────────────
    re_path(r'^frontPages/(?P<path>.*)$', serve,
            {'document_root': os.path.join(PROJECT_DIR, 'frontPages')}),
    re_path(r'^resources/(?P<path>.*)$', serve,
            {'document_root': os.path.join(PROJECT_DIR, 'resources')}),
    re_path(r'^generic/(?P<path>.*)$', serve,
            {'document_root': os.path.join(PROJECT_DIR, 'generic')}),
]
