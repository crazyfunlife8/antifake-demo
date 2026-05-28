$(function () {
  $.extend($.fn, {
    asyncFile: function (a) {
      var b = $(this);
      "file" == b.prop("type") &&
        0 != a.length &&
        b.change(function () {
          this.value
            ? getFileBytes(b, function (b) {
                a.val(b);
              })
            : a.val("");
        });
    },
    valid: function () {
      var a = $(this),
        b = !0;
      $.each($(".required:not(span)", a), function (a, d) {
        if (validIsEmpty($(d))) return (b = !1);
      });
      return b;
    },
    isBlank: function () {
      return $(this).val() ? !1 : !0;
    },
  });
});
function validIsEmpty(a) {
  return a.isBlank()
    ? ("front" == platform && "function" === typeof $.featherlight
        ? $.featherlight(
            "<div class='lightbox'>" +
              getTitle(a) +
              " " +
              alertMsgNotEmptyId +
              "!</div>",
            { variant: "fixwidth" },
          )
        : alert(getTitle(a) + " " + alertMsgNotEmptyId + "!"),
      a.focus(),
      !0)
    : !1;
}
function getParam2Obj(a) {
  return JSON.parse(
    '{"' +
      decodeURIComponent(a.replace(/&/g, '","').replace(/=/g, '":"')) +
      '"}',
  );
}
function getTitle(a) {
  var b = a.attr("title");
  b || (b = $("label[for='" + a.prop("id") + "']").text());
  return b;
}
function setFormTag(a, b, c, d) {
  0 == $("#" + b, a).length &&
    (d || (d = ""),
    a.prepend(
      "<input type='hidden' id='" + b + "'  name='" + b + "' " + d + " />",
    ));
  a = $("#" + b, a);
  a.val(c);
  return a;
}
function getForm(a) {
  if (a.prop("form")) return a.prop("form");
  for (; "HTML" != a.prop("tagName") && "FORM" != a.prop("tagName"); )
    a = a.parent();
  return a;
}
function setDataForm(a, b) {
  for (index in a) $("#" + index, b).val(a[index]);
}
function getFormData(a) {
  return getTagData(a[0]);
}
function getDivData(a) {
  return getTagData($("input,textarea,select", a));
}
function getTagData(a) {
  var b = {};
  $.each(a, function (a, d) {
    var c = $(d),
      f = c.prop("name");
    f &&
      ("checkbox" == c.prop("type") || "radio" == c.prop("type")
        ? this.checked && (b[f] = c.val())
        : "textarea" == c.prop("type") &&
            -1 != c.prop("class").indexOf("htmlEdit")
          ? (c = window.ckeditors[c.prop("id")]) && (b[f] = c.getData())
          : (b[f] = c.val()));
  });
  return b;
}
function setSelectData(a, b, c) {
  setSelectById(a, b, "key", "value", c);
}
function setSelectById(a, b, c, d, e) {
  b.empty();
  e && b.append($("<option>").val("").text(e));
  for (index in a) b.append($("<option>").val(a[index][c]).text(a[index][d]));
  b.hasClass("chosen-select-deselect") && b.trigger("chosen:updated");
}
function getTagValues(a) {
  var b = [];
  $.each(a, function (a, d) {
    b.push($(d).val());
  });
  return b;
}
function getSelectValues(a) {
  var b = [];
  $.each(a.find("option"), function (a, d) {
    d.value && b.push(d.value);
  });
  return b;
}
function getIntVal(a, b) {
  try {
    ((a = parseInt(a.replace(/[^\d]/g, ""))), isNaN(a) && (a = b));
  } catch (c) {
    a = b;
  }
  return a;
}
function getFileBytes(a, b) {
  if (0 != a.length && a[0].files && 0 != a[0].files.length) {
    var c = a[0].files[0].size,
      d = alertMsgFront("FILE_SIZE_LIMIT", "", "", "", !0);
    c > 1024 * d
      ? (alert(alertMsgFront("BIG_FILE_SIZE", d, "", "", !0)),
        (a[0].value = ""))
      : $.each(a[0].files, function (a, c) {
          var d = new FileReader();
          d.readAsDataURL(c);
          d.onloadend = function (a) {
            a = d.result;
            b(a.substr(a.indexOf("base64") + 7));
          };
        });
  }
}
function uploadTempFile(a, b) {
  var c = a[0].files[0].type,
    d = /image/i;
  1e7 < a[0].files[0].size
    ? (alertMsgFront("BIG_FILE_SIZE", 1e4, "", ""), (a[0].value = ""))
    : d.test(c)
      ? $.each(a[0].files, function (c, d) {
          var e = new FileReader();
          e.readAsDataURL(d);
          console.log(d);
          e.onloadend = function (c) {
            c = new FormData();
            var d = e.result;
            d = JSON.stringify(d.substr(d.indexOf("base64") + 7));
            c.append("fileBase64", d);
            $.ajaxSettings.traditional = !0;
            $.ajaxSettings.cache = !1;
            $.ajax({
              url: "generic/uploadTemp.do",
              data: c,
              type: "post",
              dataType: "json",
              async: !0,
              contentType: !1,
              processData: !1,
              beforeSend: function () {
                $("#loading").append(
                  '<div id="bar" class="container" style="top: 80%;position: relative;"><div class="progress" style="height: 15px;">  <div class="progress-bar progress-bar-success progress-bar-striped active" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="0" style="width: 0%;">0%</div></div></div>',
                );
                $("#loading").css({ opacity: "0.75", display: "block" });
              },
              success: function (a, c) {
                b(a, a.fileNo);
              },
              xhr: function () {
                var a = $.ajaxSettings.xhr();
                a.upload &&
                  a.upload.addEventListener(
                    "progress",
                    function (a) {
                      a.lengthComputable &&
                        ($(".progress-bar-success").attr({
                          "aria-valuenow": a.loaded,
                          "aria-valuemax": a.total,
                        }),
                        $(".progress-bar-success").css(
                          "width",
                          ((a.loaded / a.total) * 100).toFixed(0) + "%",
                        ),
                        $(".progress-bar-success").text(
                          ((a.loaded / a.total) * 100).toFixed(0) + "%",
                        ));
                    },
                    !1,
                  );
                return a;
              },
              error: function (b, c, d) {
                a[0].value = "";
                $("input[type=text]")[0].value = "";
                alertMsgFront("FORBIDDEN_FILE");
              },
              complete: function () {
                $("#loading").fadeOut(800);
                $("#bar").remove();
              },
            });
          };
        })
      : ((a[0].value = ""), alertMsgFront("RESTRICT_IMG"));
}
function redirect(a) {
  a && (location.href = getRootUrl(a));
}
var submited = !1;
function formSubmit(a, b, c) {
  (c && submited) ||
    (a || ((a = $("<form>")), $("body").append(a)),
    $("select:disabled", a).removeAttr("disabled"),
    a.attr({
      enctype: "multipart/form-data",
      action: getRootUrl(b),
      method: "post",
    }),
    0 == $("button[type=submit]", a).length &&
      a.prepend("<button type='submit' style='display: none;'></button>"),
    c || (submited = !0),
    $("button[type=submit]", a).trigger("click"));
}
function doAjax(a, b, c, d) {
  $.ajaxSettings.async = !1;
  d && ($.ajaxSettings.async = d);
  $.ajaxSettings.traditional = !0;
  $.ajaxSettings.cache = !1;
  $.ajax({
    url: getRootUrl(a),
    data: b,
    type: "post",
    dataType: "json",
    success: function (a, b) {
      c(a, b);
    },
    error: function (a, b, c) {
      console.log(a);
      console.log(b);
      console.log(c);
    },
  });
}
function doAjaxAndHandleError(a, b, c, d, e) {
  $.ajaxSettings.async = !1;
  e && ($.ajaxSettings.async = e);
  $.ajaxSettings.traditional = !0;
  $.ajaxSettings.cache = !1;
  $.ajax({
    url: getRootUrl(a),
    data: b,
    type: "post",
    dataType: "json",
    success: function (a, b) {
      c(a, b);
    },
    error: function (a, b, c) {
      console.log(a);
      console.log(b);
      console.log(c);
      d(a.status);
    },
  });
}
function getRootUrl(a) {
  a.substr(0, 5) != contextPath &&
    (a = "/" == a.substr(0, 1) ? contextPath + a : contextPath + "/" + a);
  return a;
}
function getNowDate() {
  var a = new Date(),
    b = a.getDate(),
    c = a.getMonth() + 1;
  a = a.getFullYear();
  10 > b && (b = "0" + b);
  10 > c && (c = "0" + c);
  return a + "/" + c + "/" + b;
}
function isValidEmail(a) {
  return /^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$/.test(a);
}
function setHiddenTag(a, b, c, d, e) {
  0 == $("#" + b, a).length &&
    (e || (e = ""),
    a.prepend(
      "<input type='hidden' id='" + b + "'  name='" + c + "' " + e + " />",
    ));
  a = $("#" + b, a);
  a.val(d);
  return a;
}
function getUrlParameters(a, b, c) {
  b = (b.length ? b : window.location.search).split("?")[1].split("&");
  for (var d = !0, e = 0; e < b.length; e++) {
    parr = b[e].split("=");
    if (parr[0] == a) return c ? decodeURIComponent(parr[1]) : parr[1];
    d = !1;
  }
  if (!d) return !1;
}
function secToTime(a) {
  var b = new Date(0, 0, 0, 0, 0, a);
  a = b.getHours();
  var c = b.getMinutes();
  b = b.getSeconds();
  10 > parseInt(a) && (a = "0" + a);
  10 > parseInt(c) && (c = "0" + c);
  10 > parseInt(b) && (b = "0" + b);
  return a + ":" + c + ":" + b;
}
function alertMsg(a, b, c, d, e) {
  var f = "";
  doAjax(
    "generic/getSysMsg.do",
    {
      syscde: a,
      a: null == b ? "" : b,
      b: null == c ? "" : c,
      c: null == d ? "" : d,
    },
    function (a, b) {
      "success" == a.returnMsg && ((f = a.msg), e || alert(f));
    },
  );
  return f;
}
function alertMsgFront(a, b, c, d, e) {
  var f = "";
  doAjax(
    "generic/getSysMsgFront.do",
    {
      syscde: a,
      a: null == b ? "" : b,
      b: null == c ? "" : c,
      c: null == d ? "" : d,
    },
    function (a, b) {
      "success" == a.returnMsg &&
        ((f = a.msg),
        e ||
          $.featherlight("<div class='lightbox'>" + f + "</div>", {
            variant: "fixwidth",
          }));
    },
  );
  return f;
}
