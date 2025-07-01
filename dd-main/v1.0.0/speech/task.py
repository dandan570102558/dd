import json
import os
import random
import getResponseBody
from getResponseBody import getResponseBody
import jsonPathParse
from jsonPathParse import jsonPathParse
import requests
import openpyxl
from urllib.parse import unquote, urlparse
import warnings
from requests_toolbelt.utils import dump
from requests_toolbelt.multipart.encoder import MultipartEncoder

num = ''.join(random.choices('0123456789', k=6))
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config/config.json")
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        #------------------------用户自定义数据
        bizName_2 = config.get("bizName_2")
        bizName_3 = config.get("bizName_3")
        intentionList_name = config.get("intentionCollectionName")
        tenant = config.get("tenant")
        tenantLineGroupName = config.get("tenantLineGroupName")
        speechName = config.get("speechName")
        # filePath = config.get("filePath")
        phone = config.get("phone")
        upload_url = config.get("upload_url")
        Token = config.get("Token")
        #------------------------用户自定义数据
except Exception as e:
    print(f"Error reading config file: {e}")
    exit(1)
    
#------------------------根据租户获取线路组：tenantLineGroup[]
body_tenantLineGroup = {"bffAction":"css.call.tenant.linegroup.list","tenantCode":tenant}

data_tenantGroupGuid = json.dumps(getResponseBody(body_tenantLineGroup))

json_path_tenantLineGroup = "$.data[*][?(@.tenantLineGroupName == '{}')].tenantLineGroupId".format(tenantLineGroupName)
tenantLineGroup = jsonPathParse(data_tenantGroupGuid, json_path_tenantLineGroup)

# print(f"线路组：{tenantLineGroup}")

#------------------------根据租户获取话术列表：taskSpeechGroupId、taskSpeechName
def get_speechGroupId(tenant, speechName=""):
    body_taskSpeechGroupId = {
            "bffAction": "css.call.speech.listSpeech",
            "pageSize": 999,
            "pageNum": 1,
            "tenant": tenant,
            "status": 1,
            "needSpeechVariable": 1
        }
    taskSpeech_result = getResponseBody(body_taskSpeechGroupId)
    data_taskSpeech = json.dumps(taskSpeech_result)
    """如果没有给话术名称，则默认拿列表返回的第一个话术"""
    if not speechName:
        json_path_data_taskSpeechGroupId = "$.data.list[0].groupId"
        json_path_data_taskSpeechName = "$.data.list[0].speechName"
        taskSpeechGroupId = jsonPathParse(data_taskSpeech, json_path_data_taskSpeechGroupId)
        taskSpeechName = jsonPathParse(data_taskSpeech, json_path_data_taskSpeechName)
        # print(f"为空时话术id:{taskSpeechGroupId}, 话术名称：{taskSpeechName}")
        return taskSpeechGroupId, taskSpeechName
    else:
        json_path_data_taskSpeechGroupId ="".join("$.data.list[?(@.speechName == '{}')].groupId".format(speechName))
        taskSpeechGroupId = jsonPathParse(data_taskSpeech, json_path_data_taskSpeechGroupId)
        taskSpeechName = speechName
        # print(f"不为空时话术id:{taskSpeechGroupId[0]}, 话术名称：{taskSpeechName}")
        return taskSpeechGroupId[0], taskSpeechName
    
taskSpeechGroupId, taskSpeechName = get_speechGroupId(tenant, speechName)

#------------------------创建任务:获取taskId
body_createTask = {
"bffAction": "task.createTask",
"name": f"HMY任务{num}",
"exeStartTime": "07:00",
"exeEndTime": "20:00",
"expectLoadCount": 1,
"tenant": tenant,
"faqGuid": taskSpeechGroupId,
"autoRetry": "0",
"ext": "{\"callDuration\":[{\"startTime\":\"07:00\",\"endTime\":\"20:00\"}]}",
"groupId": taskSpeechGroupId,
"taskType": 0,
"transfer": 0,
"phoneType": 1,
"callbackSwitch": 0,
"loadFlag": 1,
"tenantLineGroupId": tenantLineGroup[0],
"thirdBlacklistIntercept": 0,
"featureIntercept": 0,
"carrierAreaLimit": [],
"faqName": taskSpeechName,
"multipleSmsLink": 0
}
createTask_result = getResponseBody(body_createTask)
data_createTask = json.dumps(createTask_result)
json_getTaskId = "$.data"
taskId = jsonPathParse(data_createTask, json_getTaskId)

if createTask_result.get('code') != "0":
    print(f"\033[1;31;42m任务创建失败: {createTask_result.get('msg')}\033[0m")
    exit(1)
else:
    print(f"\033[4;33m任务创建成功\033[0m")

#------------------------获取当前任务下的模板下载地址：ossUrl
body_getPhoneTemplate = {
"bffAction": "css.call.task.downloadTemplate",
"guid": taskId,
"uploadType": "0",
"fileType": 2
}
getPhoneTemplate_result = getResponseBody(body_getPhoneTemplate)
data_getPhoneTemplate = json.dumps(getPhoneTemplate_result)
json_ossUrl = "$.data.ossUrl"
ossUrl = jsonPathParse(data_getPhoneTemplate, json_ossUrl)
# print(ossUrl)
#------------------------下载模板并维护名单
def download_file(url, save_path):
    # 下载模版
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ 下载成功！文件保存到: {save_path}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")
    # 维护名单
    try:
        warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
        wb = openpyxl.load_workbook(save_path)
        sheet = wb["数据页"]
        sheet['A2'] = "1"
        sheet['B2'] = phone
        wb.save(save_path)
        print(f"✅ 名单维护完成: {save_path}")
        return True
    except Exception as e:
        print(f"❌ 修改失败: {type(e).__name__}: {str(e)}")
        return False
script_dir = os.path.dirname(os.path.abspath(__file__))
filePath = os.path.join(script_dir, "modified.xlsx")
download_file(ossUrl, filePath)
#------------------------名单上传
def upload_file_func(up_url, token, task_guid):
    try:
        multipart_data = MultipartEncoder(
            fields={
                "bffAction": "task.uploadDataFile",
                "taskGuid": str(task_guid),  
                "fileName": "modified.xlsx",
                "uploadType": "0",  
                "file": (
                    "modified.xlsx",  
                    open(filePath, 'rb'),
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            },
            boundary="----WebKitFormBoundaryIXmRyDI6AJAmUKAM" 
        )

        headers = {
            "Token": token,
            "Content-Type": multipart_data.content_type 
        }
        
        response = requests.post(
            up_url,
            data=multipart_data,  
            headers=headers
        )
        
        response.raise_for_status()
        print(f"✅ 文件上传成功！响应: {response.text}")
        return response.json()
        
    except Exception as e:
        print(f"❌ 上传失败: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"错误详情: {e.response.text}")
        return None
upload_file_func(upload_url, Token, taskId)