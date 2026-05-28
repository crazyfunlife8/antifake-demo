function addNewRow(group, className, key, value, lang) {
    var tmp = $($('#RowTemp').html()).addClass(className);
    var num = parseInt(className.split("--")[1]);
    if (num == 4) {
        $(tmp).find("a").eq(0).remove();
    }
    $(tmp).find('legend').text('level ' + num);
    $(group).append(tmp);
    const group__inputs = $(tmp).find(">.group__item>.group__inputs>.group__input");
    $(group__inputs[0]).val(key);
    $(group__inputs[1]).attr("data", lang);
    $(group__inputs[2]).val(value);

    return $(tmp);
}
function deleteRow(obj) {
    $(obj).parent().parent().parent().parent().remove();
}

function findClass(obj) {
    var className = $(obj).parent().parent().parent().parent().attr('class');
    var num = parseInt(className.split("--")[1]) + 1;
    return "group__level--" + num;
}
function checkMultiMenu(dom, result) {
    result || (result = []);

    var valid = true;

    $(dom).find(">.group__level").map((index, item) => {
        const group__inputs = $(item).find(">.group__item .group__input");
        const key = $(group__inputs[0]).val();
        const value = $(group__inputs[2]).val();
        const lang = ($(group__inputs[1]).attr("data") == undefined) ? "" : $(group__inputs[1]).attr("data");
        if (key == "" || value == "") {
            valid = false;
            return false;
        }
        const nextDom = $(item);
        let child = [];
        if (nextDom.length) {
            checkMultiMenu(nextDom, child);
        }
        result.push({ key, value, lang, child });
    });
    if (!valid) {
        return false;
    } else {
        return result;
    }

}
function load(data, dom, level) {
    level || (level = 0)
    dom || (dom = $('#multiSelectSetting'));
    for (let i = 0; i < data.length; i++) {
        const item = data[i];
        const key = item.key;
        const value = item.value;
        const child = item.child;
        const lang = item.lang;
        let levelName = 'group__level--' + (level + 1);
        const nexDom = addNewRow(dom, levelName, key, value, lang);
        load(child, nexDom, level + 1);
    }
}
function selectEmpty(dom, level) {

    for (var i = 3; i >= level; i--) {
        console.log(i);
        $(dom).find("select").eq(i).empty();
    }

}
function selectChange(dom, data, element, level, containOther, otherTextStr) {
    selectEmpty(dom, level);
    $(dom).find("select").selectpicker('refresh');
    var index = $(element)[0].selectedIndex - 1;
    var value = $(element)[0].value;
    var optionText = $(element)[0].selectedOptions[0].text;


    var datas;
    if(containOther && (value == otherTextStr)){
    	$(dom).find("input[name='answerText']").val('').prop("disabled",false).parents("div.radio").show();
    	datas = [];
    }else{
    	if(optionText == otherTextStr){
    		$(dom).find("input[name='answerText']").val('').prop("disabled",false).parents("div.radio").show();
        	datas = [];
    	}else{
    		$(dom).find("input[name='answerText']").val('').prop("disabled",true).parents("div.radio").hide();
    		$(dom).find("select").slice(level).selectpicker('hide');
        	datas = multiSelectSearchOption(dom, data, level, index, containOther, otherTextStr);	
    	}    	
    }

    var $select = $(dom).find("select").eq(level);
    $select.attr("data", JSON.stringify(datas));
    $select.selectpicker('refresh');
    if(datas.length > 0){ 	
    	$select.selectpicker('show');
    } else{
    	$(dom).find("select").slice(level).selectpicker('hide');
    }
}
function multiSelectSearchOption(dom, data, level, index, containOther, otherTextStr) {
	if (!data) {
        data = multiSelectJSON;
    }

    data = JSON.parse(data);
    console.log(data);

    if (level > 0) {
    	if(index == -1){
    		data = [];
    	}else{
            data = data[index].child;    		
    	}
    }

    for (let i = 0; i < data.length; i++) {
        const item = data[i];
        var text = item.key;
        const value = item.value;
        if (item.lang != "") {
            var lang = JSON.parse(item.lang);
            $.each(lang, function (key) {

                if (key == langType && lang[key] != "") {
                    text = lang[key];

                    return false;
                }

            })
        }
        $(dom).find("select").eq(level).append("<option value='" + value + "'>" + text + "</option");
        if(containOther && i ==data.length-1){
        	$(dom).find("select").eq(level).append("<option value='" + otherTextStr + "'>" + otherTextStr + "</option");
        }
    }


    return data;



}
function openLangModal(obj, modal) {
    langTarget = obj;
    $(modal).find("input").val("");

    if ($(obj).attr("data") != undefined && $(obj).attr("data") != "") {
        var lang = JSON.parse($(obj).attr("data"));
        $.each(lang, function (key, item) {
            console.log(key, lang[key]);
            $(modal).find("input[name='" + key + "']").val(item);
        })
    }



    $('#childerMutiLang').show()
}
function saveLang(obj) {
    var lang = new Object();
    $(obj).find(".fieldMutiType").each(function (idx, item) {
        lang[$(item).attr('name')] = $(item).val();

    })


    $(langTarget).attr("data", JSON.stringify(lang));
    $(obj).hide()
}
function fieldNode(key){
	this.key = key.toString();
	this.value = key.toString();
	this.lang = '{}';
	this.child = [];
	this.descendantMap = new Map();
}

function processDatas(datas){
	datas.forEach((value) =>{
		if(value.descendantMap.size == 0){
			return;
		}else{
			processDatas(value.descendantMap);
			value.descendantMap.forEach((value2) =>{
				value.child.push(value2);
			});
			value.descendantMap.clear();
		}
		
	});
	
}

function processCsvFile(result){
	
	var lines = result.split('\r\n');
	let dataArr;
	let langArr;
	let title;
	let titleLangArr;
	let dataMap = new Map();
	let map4Loop = dataMap;
	let node4Loop;
	
	for(var j = 0; j<lines.length; j++){
		if(j == 0){
			title = lines[j].split(",");
			titleLangArr = title.slice(4);
			
		}else{
			var row = lines[j];
			dataArr = row.split(",",-1).slice(0,4);
			langArr = row.split(",",-1).slice(4);
			map4Loop = dataMap;
			node4Loop = undefined;
			for(a in dataArr){
				if(dataArr[a]!=''){
					if(!map4Loop.has(dataArr[a])){
						map4Loop.set(dataArr[a],new fieldNode(dataArr[a]));
					}
					node4Loop = map4Loop.get(dataArr[a]);
					map4Loop = node4Loop.descendantMap;
				}
				else{
					break;
				}
			
			}
			if(node4Loop!=undefined){
				node4Loop.lang = JSON.parse(node4Loop.lang);
				for(i in titleLangArr){
					if(langArr[i]!=''){
						node4Loop.lang[titleLangArr[i]] = langArr[i];
					}					
				}
				node4Loop.lang = JSON.stringify(node4Loop.lang);
			
			}
		}
		
	}	
	processDatas(dataMap);
	console.log(dataMap);
	return dataMap;
	
}

