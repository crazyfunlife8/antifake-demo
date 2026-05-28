"""
translations.py — 多語系字串查詢表

使用方式：
  - 頁面 view 呼叫 _render_page(request, ...)，會自動把對應語系 dict 以 `t` 傳入 template
  - template 裡用 {{ t.key }} 取得翻譯字串
  - getSysMsgFront.do 使用每個語系下的 sys dict

新增語系步驟：
  1. 在 TRANS 加入 'XXX': { ... } dict，複製 CHT 的 key 並翻譯 value
  2. 在每個頁面的語言選單加入 <li class="langChange" title="XXX">...
  3. 若需要語系專屬頁面版型，建立 index_xxx.html 等檔案，程式會自動 fallback
"""

TRANS = {
    'CHT': {
        # ── 導覽列 ─────────────────────────────────────────────────────────
        'nav_result':      '查詢結果',
        'nav_contact':     '聯絡我們',
        'nav_login':       '會員登入',
        'nav_lang_select': '選取語言',
        'nav_lang_close':  '關閉語言',
        'lang_cht':        '繁體中文',
        'scroll_top':      '頁面往上',

        # ── 頁尾 ───────────────────────────────────────────────────────────
        'footer_main': 'T-Security Inc. © 2016-2026',
        'footer_copy': '版權所有 COPYRIGHT 2016-2026&nbsp;T-SECURITY INC. ALL RIGHTS RESERVED.｜POWERED BY AMAZON WEB SERVICES.',

        # ── JS 常數（注入至各頁底部 <script>）──────────────────────────────
        'js_select_file': '選擇檔案',
        'js_not_empty':   '不可空白',

        # ── index.html ─────────────────────────────────────────────────────
        'title_check':   '真偽查詢',
        'label_code':    '商品防偽碼',
        'label_captcha': '驗證碼',
        'btn_query':     '查詢',

        # ── checkTruth.html / mainEntry.html ───────────────────────────────
        'msg_nomatch':       '您查詢的防偽碼無法比對！',
        'msg_provide_photo': '請提供防偽標籤照片確認。',
        'btn_next':          '下一步',
        'msg_geo_agree':     '同意',
        'msg_geo_decline':   '不同意',
        'fake_result_ok': (
            '<p>本產品被拆封驗證第<span style="color:#FF0000;">{n}</span>次</p>'
            '<p>感謝您的使用，本產品為原廠正貨。</p>'
        ),
        'fake_result_warn': (
            '<p>本產品被拆封驗證第<span style="color:#FF0000;">{n}</span>次，<br>'
            '<span style="color:#FF0000;">如次數顯示大於1，即為有疑慮的探頭，'
            '為避免使用到假貨</span>，請儘速與原廠聯絡'
            '<a href="tel:{phone_no}">{phone}</a></p>'
            '<p>為保障您的權益，請按&quot;下一步&quot; 進行驗證。</p>'
        ),

        # ── memLogin.html ──────────────────────────────────────────────────
        'title_login':         '會員登入',
        'label_account':       '帳號(電子信箱)',
        'label_password':      '密碼',
        'link_forgot':         '忘記密碼',
        'label_remember':      '記住我的登入資訊',
        'btn_login':           '登入',
        'btn_register':        '會員註冊',
        'title_reset_pwd':     '重設密碼',
        'label_enter_account': '請輸入您的帳號(電子信箱)',
        'btn_confirm':         '確認',

        # ── genDetemItemForm.html ──────────────────────────────────────────
        'msg_requery':        '請重新查詢正確的防偽碼，或<a href="/contact.do">與我們聯繫</a>。',
        'label_upload_photo': '請您拍照上傳產品包裝圖檔（含防偽標籤），提供我們更多資訊。',
        'label_contact_info': '請留下您的姓名及電話(範例：王小明/09XXXXXXXX)',
        'btn_submit':         '送出',

        # ── contact.html ───────────────────────────────────────────────────
        'title_contact':             '聯絡我們',
        'label_name':                '姓名*',
        'placeholder_name':          '請輸入姓名',
        'msg_required':              '*必填',
        'label_country_code':        '國際電話區號',
        'placeholder_country_code':  '請選擇國際電話區號',
        'label_phone':               '手機號碼',
        'placeholder_phone':         '請輸入手機號碼',
        'label_email':               '電子信箱*',
        'placeholder_email':         '請輸入電子信箱',
        'msg_email_error':           '電子信箱格式錯誤。',
        'label_gender':              '性別',
        'placeholder_gender':        '請選擇性別',
        'opt_female':                '女',
        'opt_male':                  '男',
        'label_product_code':        '商品防偽碼',
        'placeholder_product_code':  '請輸入商品防偽碼',
        'label_issue_type':          '問題類型',
        'placeholder_issue_type':    '請選擇問題類型',
        'opt_issue_auth':            '產品真偽問題',
        'opt_issue_quality':         '產品品質問題',
        'opt_issue_usage':           '產品使用問題',
        'opt_issue_other':           '其他問題',
        'label_store_type':          '商店分類',
        'placeholder_store_type':    '請選擇商店類型',
        'opt_store_physical':        '實體商店',
        'opt_store_online':          '網路商店',
        'label_store_name':          '購買商店',
        'placeholder_store_name':    '請輸入購買商店名',
        'label_purchase_date':       '購買日期',
        'placeholder_purchase_date': '請輸入購買日期',
        'label_purchase_amount':     '購買金額',
        'placeholder_purchase_amount': '請輸入購買金額',
        'label_currency':            '幣別',
        'placeholder_currency':      '請選擇幣別',
        'optgroup_recommended':      '建議幣別',
        'optgroup_common':           '常用幣別',
        'optgroup_other':            '其他幣別',
        'label_description':         '問題描述*',
        'placeholder_description':   '請寫下產品系列名稱、規格或型號、有效日期及您遇到的問題。',
        'label_privacy_agree':       '我已同意並詳細閱讀',
        'label_privacy_link':        '個資說明',
        'opt_yes':                   '是',
        'label_captcha_contact':     '驗證碼 *',
        'placeholder_captcha':       '請輸入驗證碼',
        'js_required_fields':        '仍有必填欄位未填，請檢查填寫內容。',
        'js_email_format_error':     '電子信箱格式錯誤，請檢查後再送出。',

        # ── Questionnaire.html ─────────────────────────────────────────────
        'label_file_upload':   '檔案上傳',
        'placeholder_no_file': '未選擇任何檔案',
        'msg_no_answer':       '尚未回答或選擇答案',

        # ── 系統訊息（getSysMsgFront.do API，key 須與前端 alertMsgFront 呼叫一致）
        'sys': {
            'GEO_LOCATION_PERMISSION': '稍後將進行地理位置授權。',
            'QKIT_ERR_MSG_001':        '系統發生異常，請稍後再試。',
            'BIG_FILE_SIZE':           '檔案大小不可超過 {0} KB。',
            'RESTRICT_IMG':            '請上傳圖片格式的檔案。',
            'FILE_SIZE_LIMIT':         '10000',
            'FORBIDDEN_FILE':          '不允許此類型的檔案。',
            'CTACT_ADD_ERR_MSG_001':   '聯絡表單送出失敗，請稍後再試。',
        },
    },

    'ENG': {
        # ── 導覽列 ─────────────────────────────────────────────────────────
        'nav_result':      'Check Result',
        'nav_contact':     'Contact Us',
        'nav_login':       'Member Login',
        'nav_lang_select': 'Select Language',
        'nav_lang_close':  'Close',
        'lang_cht':        'Traditional Chinese',
        'scroll_top':      'Back to Top',

        # ── 頁尾 ───────────────────────────────────────────────────────────
        'footer_main': 'T-Security Inc. © 2016-2026',
        'footer_copy': 'Copyright 2016-2026&nbsp;T-SECURITY INC. ALL RIGHTS RESERVED. | POWERED BY AMAZON WEB SERVICES.',

        # ── JS 常數 ────────────────────────────────────────────────────────
        'js_select_file': 'Choose File',
        'js_not_empty':   'cannot be blank',

        # ── index.html ─────────────────────────────────────────────────────
        'title_check':   'Authenticity Check',
        'label_code':    'Anti-fake Code',
        'label_captcha': 'Verification Code',
        'btn_query':     'Search',

        # ── checkTruth.html / mainEntry.html ───────────────────────────────
        'msg_nomatch':       'Anti-fake code not found.',
        'msg_provide_photo': 'Please provide a photo of the anti-fake label for confirmation.',
        'btn_next':          'Next',
        'msg_geo_agree':     'Allow',
        'msg_geo_decline':   'Deny',
        'fake_result_ok': (
            '<p>This product has been verified '
            '<span style="color:#FF0000;">{n}</span> time(s).</p>'
            '<p>Thank you. This product is genuine.</p>'
        ),
        'fake_result_warn': (
            '<p>This product has been verified '
            '<span style="color:#FF0000;">{n}</span> time(s).<br>'
            '<span style="color:#FF0000;">If the count is greater than 1, there is a concern '
            'about counterfeiting. To avoid using counterfeit products</span>, please contact '
            'the manufacturer immediately at <a href="tel:{phone_no}">{phone}</a></p>'
            '<p>To protect your rights, please click &quot;Next&quot; to proceed with verification.</p>'
        ),

        # ── memLogin.html ──────────────────────────────────────────────────
        'title_login':         'Member Login',
        'label_account':       'Account (Email)',
        'label_password':      'Password',
        'link_forgot':         'Forgot Password',
        'label_remember':      'Remember my login',
        'btn_login':           'Login',
        'btn_register':        'Register',
        'title_reset_pwd':     'Reset Password',
        'label_enter_account': 'Please enter your account (email)',
        'btn_confirm':         'Confirm',

        # ── genDetemItemForm.html ──────────────────────────────────────────
        'msg_requery':        'Please re-enter the correct anti-fake code, or <a href="/contact.do">contact us</a>.',
        'label_upload_photo': 'Please upload a photo of the product packaging (including anti-fake label) to provide more information.',
        'label_contact_info': 'Please leave your name and phone number (e.g. John/09XXXXXXXX)',
        'btn_submit':         'Submit',

        # ── contact.html ───────────────────────────────────────────────────
        'title_contact':             'Contact Us',
        'label_name':                'Name*',
        'placeholder_name':          'Enter your name',
        'msg_required':              '*Required',
        'label_country_code':        'Country Code',
        'placeholder_country_code':  'Select country code',
        'label_phone':               'Mobile Number',
        'placeholder_phone':         'Enter mobile number',
        'label_email':               'Email*',
        'placeholder_email':         'Enter email address',
        'msg_email_error':           'Invalid email format.',
        'label_gender':              'Gender',
        'placeholder_gender':        'Select gender',
        'opt_female':                'Female',
        'opt_male':                  'Male',
        'label_product_code':        'Anti-fake Code',
        'placeholder_product_code':  'Enter anti-fake code',
        'label_issue_type':          'Issue Type',
        'placeholder_issue_type':    'Select issue type',
        'opt_issue_auth':            'Product Authenticity',
        'opt_issue_quality':         'Product Quality',
        'opt_issue_usage':           'Product Usage',
        'opt_issue_other':           'Other Issues',
        'label_store_type':          'Store Type',
        'placeholder_store_type':    'Select store type',
        'opt_store_physical':        'Physical Store',
        'opt_store_online':          'Online Store',
        'label_store_name':          'Purchase Store',
        'placeholder_store_name':    'Enter store name',
        'label_purchase_date':       'Purchase Date',
        'placeholder_purchase_date': 'Enter purchase date',
        'label_purchase_amount':     'Purchase Amount',
        'placeholder_purchase_amount': 'Enter purchase amount',
        'label_currency':            'Currency',
        'placeholder_currency':      'Select currency',
        'optgroup_recommended':      'Recommended',
        'optgroup_common':           'Common',
        'optgroup_other':            'Other',
        'label_description':         'Issue Description*',
        'placeholder_description':   'Please describe the product series, specification, model, expiry date, and the issue you encountered.',
        'label_privacy_agree':       'I have read and agreed to the',
        'label_privacy_link':        'Privacy Policy',
        'opt_yes':                   'Yes',
        'label_captcha_contact':     'Verification Code *',
        'placeholder_captcha':       'Enter verification code',
        'js_required_fields':        'There are required fields not filled in. Please check your input.',
        'js_email_format_error':     'Invalid email format. Please check and resubmit.',

        # ── Questionnaire.html ─────────────────────────────────────────────
        'label_file_upload':   'File Upload',
        'placeholder_no_file': 'No file selected',
        'msg_no_answer':       'Please answer all required questions before submitting',

        # ── 系統訊息 ───────────────────────────────────────────────────────
        'sys': {
            'GEO_LOCATION_PERMISSION': 'Location permission will be requested shortly.',
            'QKIT_ERR_MSG_001':        'System error, please try again later.',
            'BIG_FILE_SIZE':           'File size must not exceed {0} KB.',
            'RESTRICT_IMG':            'Please upload an image file.',
            'FILE_SIZE_LIMIT':         '10000',
            'FORBIDDEN_FILE':          'This file type is not allowed.',
            'CTACT_ADD_ERR_MSG_001':   'Failed to submit contact form, please try again.',
        },
    },
}
