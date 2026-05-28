const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const app = express();
const PORT = 3000;
const multipart = multer();

// ==========================================
// Body parser
// ==========================================
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ==========================================
// 1. 靜態資源路由設定
// ==========================================
app.use('/frontPages', express.static(path.join(__dirname, 'frontPages')));
app.use('/resources', express.static(path.join(__dirname, 'resources')));


// ==========================================
// 2. AJAX API Stubs（動態路由、需在靜態 /generic 之前）
// ==========================================

// 防偽判定（checkTruth.do 頁面呼叫、帶 checksum）
app.post('/callQkit.do', (req, res) => {
    const branch = req.query.branch;
    if (branch === 'true') {
        return res.json({ isSystemMatch: 'true' });
    }
    if (branch === 'error') {
        return res.json({ data: null });
    }
    // 預設回傳 N=1 文字（與 renderCheckTruth 初始渲染一致，不會覆蓋清空）
    res.json({
        isSystemMatch: 'false',
        data: { fakeResult: buildFakeResult(1), fakeJudgeImg: '' },
        isQuest: '0'
    });
});

// 防偽判定 fallback（checksum 不存在時走這條）
app.post('/nonQkit.do', (req, res) => {
    res.json({ success: true });
});

// 動態活動看板區塊（blockId=7 是 checkTruth 頁用的）
app.post('/loadBlockCont.do', (req, res) => {
    res.json({ cont: '' });
});

// 地理位置上傳（用戶同意授權後）
app.post('/updateGeoLocation.do', (req, res) => {
    res.json({ success: true });
});

// 頁面事件記錄
app.post('/pageEventLog.do', (req, res) => {
    res.json({ success: true });
});

// 語系切換
app.post('/generic/frontLangChange.do', (req, res) => {
    res.json({ success: true });
});

// 系統訊息查詢（alertMsgFront 用，依 syscde 回對應文字）
const msgMap = {
    'GEO_LOCATION_PERMISSION': '稍後將進行地理位置授權。',
    'QKIT_ERR_MSG_001': '系統發生異常，請稍後再試。',
    'BIG_FILE_SIZE': '檔案大小不可超過 {0} KB。',
    'RESTRICT_IMG': '請上傳圖片格式的檔案。',
    'FILE_SIZE_LIMIT': '10000',
    'FORBIDDEN_FILE': '不允許此類型的檔案。',
};
app.post('/generic/getSysMsgFront.do', (req, res) => {
    const syscde = req.body.syscde || '';
    const msg = msgMap[syscde] || syscde;
    res.json({ returnMsg: 'success', msg });
});

// 圖片上傳（補件表單用，base64 multipart）
app.post('/generic/uploadImg.do', (req, res) => {
    res.json({ status: true, fileNo: 99999 });
});

// 圖片上傳（contact.do 用，欄位名 fileBase64）
app.post('/generic/uploadTemp.do', (req, res) => {
    res.json({ status: true, fileNo: 99998 });
});

// 聯絡我們 AJAX 送出
app.post('/ctactAdd.do', (req, res) => {
    res.json({ msg: 'success', returnMsg: '感謝您的聯絡，我們將盡快與您聯繫。' });
});

// 補件表單送出
app.post('/saveFormFields.do', (req, res) => {
    res.json({ status: true });
});

// 問卷題目動態載入（Questionnaire.do 頁面呼叫）
app.get('/getAllQuestion.do', (req, res) => {
    res.json({
        questionList: [
            {
                prodRltAdvQuesId: 2167,
                detemItem: '3',
                isCal: 'N',
                ansQuzIsMust: 1,
                rightAns: 'null',
                isOthOpt: 'N',
                imgList: ["<img src='/generic/getImg.do?fileNo=73186' style='width:auto;max-width:100%;height:auto;'>"],
                quesOptionList: null,
                remarkOptionList: null,
                advQuesVO: { ansMold: '11', quesDesc: '<p><span style="font-size:16px;">請您拍照上傳包裝盒上的中文標籤 </span></p>' }
            },
            {
                prodRltAdvQuesId: 2168,
                detemItem: '1',
                isCal: 'N',
                ansQuzIsMust: 1,
                rightAns: '',
                isOthOpt: 'N',
                imgList: ["<img src='/generic/getImg.do?fileNo=67567' style='width:auto;max-width:100%;height:auto;'>"],
                quesOptionList: null,
                remarkOptionList: null,
                advQuesVO: { ansMold: '11', quesDesc: '<p><span style="font-size:16px;">請您拍照上傳機器上的雷射防偽標籤（鳳凰電波）</span></p>' }
            },
            {
                prodRltAdvQuesId: 1985,
                detemItem: '1',
                isCal: 'N',
                ansQuzIsMust: 1,
                rightAns: '',
                isOthOpt: 'N',
                imgList: null,
                remarkOptionList: null,
                quesOptionList: [
                    '北部地區-臺北市','北部地區-新北市','北部地區-基隆市','北部地區-桃園市',
                    '北部地區-新竹市','北部地區-新竹縣','北部地區-宜蘭縣',
                    '中部地區-臺中市','中部地區-苗栗縣','中部地區-彰化縣','中部地區-南投縣','中部地區-雲林縣',
                    '南部地區-高雄市','南部地區-臺南市','南部地區-嘉義市','南部地區-嘉義縣','南部地區-屏東縣',
                    '東部地區-花蓮縣','東部地區-臺東縣 ',
                    '離島地區-澎湖縣 ','離島地區-金門縣 ','離島地區-連江縣',
                    '其他地區'
                ].map(v => ({ quesOptDesc: v })),
                advQuesVO: { ansMold: '6', quesDesc: '<p><span style="font-size:16px;">請選擇您施打療程的城市</span></p>' }
            },
            {
                prodRltAdvQuesId: 1983,
                detemItem: '1',
                isCal: 'N',
                ansQuzIsMust: 1,
                rightAns: '醫療院所名稱',
                isOthOpt: 'N',
                imgList: null,
                quesOptionList: null,
                remarkOptionList: null,
                advQuesVO: { ansMold: '1', quesDesc: '<p><span style="font-size:16px;">請填寫施打療程的醫療院所名稱，如有分店也請同步填寫</span></p>' }
            }
        ]
    });
});

// 問卷送出（finish:true → 前端 redirect /mainEntry.do）
app.post('/saveAnswerRecord.do', (req, res) => {
    res.json({ finish: true });
});

// 會員登入送出（stub：功能維護中）
app.post('/memLogin.do', (req, res) => {
    res.redirect('/memLogin.do?msg=maintenance');
});

// 登入驗證（stub：功能維護中）
app.post('/loginCheck.do', multipart.none(), (req, res) => {
    res.send(maintenanceHtml('功能維護中，暫不開放。'));
});

// 會員註冊條款頁（stub：功能維護中）
app.get('/takeMembershipTerms.do', (req, res) => {
    res.send(maintenanceHtml('功能維護中，暫不開放。'));
});

// 忘記密碼（stub：功能維護中）
app.post('/memForgot.do', (req, res) => {
    res.json({ data: null });
});

// 補件表單送出（multipart，stub 直接導回同頁）
app.post('/genDetemItemForm.do', (req, res) => {
    res.redirect('/genDetemItemForm.do');
});

// 聯絡我們送出（multipart，stub 直接導回同頁）
app.post('/contact.do', (req, res) => {
    res.redirect('/contact.do');
});

// 問卷頁
app.get('/Questionnaire.do', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'Questionnaire.html'));
});

// 進階比對 → 實機導向 Questionnaire.do（依規格書 09 修正）
app.get('/AdvancedMatch.do', (req, res) => {
    res.redirect('/Questionnaire.do');
});

// 登出
app.get('/logoutCheck.do', (req, res) => {
    res.redirect('/mainEntry.do');
});

// genValidCode.do：動態路由，依 code seed 回傳 SVG 驗證碼圖，必須在 /generic static 之前
app.get('/generic/genValidCode.do', (req, res) => {
    const seed = parseInt(req.query.code) || 0;
    const chars = '23456789';
    let code = '';
    let s = seed;
    const states = [];
    for (let i = 0; i < 4; i++) {
        code += chars[(s * 7 + i * 13 + 17) % chars.length];
        s = (s * 31 + 7) % 97;
        states.push(s);
    }
    const xPositions = [22, 44, 66, 88];
    let digitSvgs = '';
    for (let i = 0; i < 4; i++) {
        const x = xPositions[i];
        digitSvgs += `<text x="${x}" y="27" text-anchor="middle" `
            + `font-family="Arial, sans-serif" font-size="20" font-weight="bold" `
            + `fill="#6699cc">${code[i]}</text>`;
    }
    let dots = '';
    let ns = seed;
    for (let i = 0; i < 30; i++) {
        ns = (ns * 31 + 7) % 9973; const dx = (ns % 116) + 2;
        ns = (ns * 31 + 7) % 9973; const dy = (ns % 36) + 2;
        dots += `<circle cx="${dx}" cy="${dy}" r="1" fill="#aaaaaa" opacity="0.6"/>`;
    }
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 40" width="120" height="40">`
        + `<rect x="0" y="0" width="120" height="40" fill="white"/>`
        + `<rect x="0.5" y="0.5" width="119" height="39" fill="none" stroke="#cccccc" stroke-width="1"/>`
        + dots + digitSvgs + `</svg>`;
    res.set('Content-Type', 'image/svg+xml');
    res.send(svg);
});

// getImg.do：動態路由（依 fileNo 回傳本地圖片或佔位圖），必須在 /generic static 之前
app.get('/generic/getImg.do', (req, res) => {
    const fileNo = req.query.fileNo || '0';
    const localPath = path.join(__dirname, 'generic', `getImg${fileNo}.jpg`);
    if (fs.existsSync(localPath)) {
        return res.sendFile(localPath);
    }
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <rect width="300" height="200" fill="#ccc"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#666">fileNo: ${fileNo}</text>
</svg>`;
    res.set('Content-Type', 'image/svg+xml');
    res.send(svg);
});

// /generic 靜態檔（captcha 圖等）放在 AJAX stub 之後
app.use('/generic', express.static(path.join(__dirname, 'generic')));


// ==========================================
// 3. 頁面路由
// ==========================================
function maintenanceHtml(msg) {
    return `<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body><script>alert("${msg}"); history.back();<\/script></body></html>`;
}

function computeCaptcha(seed) {
    const chars = '23456789';
    let code = '';
    let s = seed;
    for (let i = 0; i < 4; i++) {
        code += chars[(s * 7 + i * 13 + 17) % chars.length];
        s = (s * 31 + 7) % 97;
    }
    return code;
}

function buildFakeResult(n) {
    if (n >= 2) {
        return `<p>本產品被拆封驗證第<span style="color:#FF0000;">${n}</span>次，<br>`
            + `<span style="color:#FF0000;">如次數顯示大於1，即為有疑慮的探頭，為避免使用到假貨</span>，`
            + `請儘速與原廠聯絡<a href="tel:0800004088">0800-004-088</a></p>`
            + `<p>為保障您的權益，請按"下一步" 進行驗證。</p>`;
    }
    return `<p>本產品被拆封驗證第<span style="color:#FF0000;">${n}</span>次</p>`
        + `<p>感謝您的使用，本產品為原廠正貨。</p>`;
}

function renderCheckTruth(res, isQkit, checksum, fakeResult) {
    let html = fs.readFileSync(path.join(__dirname, 'pages', 'checkTruth.html'), 'utf8');
    // {% if is_qkit %}...{% else %}...{% endif %}
    if (isQkit) {
        html = html.replace(/\{%\s*if is_qkit\s*%\}([\s\S]*?)\{%\s*else\s*%\}[\s\S]*?\{%\s*endif\s*%\}/g, '$1');
    } else {
        html = html.replace(/\{%\s*if is_qkit\s*%\}[\s\S]*?\{%\s*else\s*%\}([\s\S]*?)\{%\s*endif\s*%\}/g, '$1');
    }
    html = html.replace('{{ fake_result|safe }}', fakeResult || '');
    html = html.replace('"{{ is_qkit|lower }}"', `"${isQkit ? 'true' : 'false'}"`);
    html = html.replace('"{{ checksum|escapejs }}"', `"${checksum}"`);
    res.type('html').send(html);
}

app.post('/checkTruth.do', multipart.none(), (req, res) => {
    const validCode = (req.body.validCode || '').trim();
    const captchaSeed = parseInt(req.body.captchaSeed) || 0;
    if (validCode !== computeCaptcha(captchaSeed)) {
        return res.send(maintenanceHtml('驗證碼輸入錯誤'));
    }
    const authCodeCde = (req.body.authCodeCde || '').trim();
    // stub：TEST 開頭的碼視為有效碼測試 Scenario A，其餘一律 Scenario B
    const isQkit = authCodeCde.toUpperCase().startsWith('TEST');
    renderCheckTruth(res, isQkit, authCodeCde, isQkit ? buildFakeResult(1) : '');
});

app.get('/checkTruth.do', (req, res) => {
    renderCheckTruth(res, false, '', '');
});

app.get('/memLogin.do', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'memLogin.html'));
});

app.get('/genDetemItemForm.do', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'genDetemItemForm.html'));
});

app.get('/contact.do', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'contact.html'));
});

app.get('/mainEntry.do', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'mainEntry.html'));
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pages', 'index.html'));
});


// ==========================================
// 4. 404
// ==========================================
app.use((req, res) => {
    res.status(404).send('<h1>404 Not Found - 找不到此頁面</h1>');
});

app.listen(PORT, () => {
    console.log(`防偽復刻驗證伺服器已啟動：http://localhost:${PORT}`);
    console.log(`測試分支：`);
    console.log(`  無法比對（預設）: POST /callQkit.do`);
    console.log(`  真品分支:         POST /callQkit.do?branch=true`);
    console.log(`  系統錯誤分支:     POST /callQkit.do?branch=error`);
});