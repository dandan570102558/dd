import json
import os
from sqlite3.dbapi2 import Timestamp
import getResponseBody
from getResponseBody import getResponseBody
import random


num = ''.join(random.choices('0123456789', k=6))
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        #------------------------用户自定义数据
        bizName_2 = config.get("bizName_2")
        bizName_3 = config.get("bizName_3")
        intentionList_name = config.get("intentionCollectionName")
        tenant = config.get("tenant")
        #------------------------用户自定义数据
except Exception as e:
    print(f"Error reading config file: {e}")
    exit(1)

#-------------------------------获取行业信息：biz2_id、biz_scene
body_bizTree = {"includeScene": True, "bffAction": "css.call.bizTree.list"}
data_biz = getResponseBody(body_bizTree)

biz2_id = None
biz_scene = None

# bizName_2_escaped = json.dumps(bizName_2)

# biz2_id = jmespath.search(f"data[*].children[*][?name=={bizName_2_escaped}].id | [0][0]", data_biz)
# print(f"二级话术：{biz2_id}")


def find_biz_id(data, biz_name):
    for item in data:
        if item.get('name') == biz_name:
            return item.get('id')
        if 'children' in item:
            result = find_biz_id(item['children'], biz_name)
            if result:
                return result
    return None
biz2_id = find_biz_id(data_biz['data'], bizName_2)
biz_scene = find_biz_id(data_biz['data'], bizName_3)
if not biz2_id:
    print(f"Business ID for '{bizName_2}' not found.")
    exit(1)
if not biz_scene:
    print(f"Business ID for '{bizName_3}' not found.")
    exit(1)
#-------------------------------获取行业信息：biz2_id、biz_scene

#-------------------------------获取意图集合：intentionCollectionIds
body_intentionList = {"bizId": biz2_id, "bffAction": "css.call.new.intention.kcList"}
data_intentionList = getResponseBody(body_intentionList)

intentionCollectionIds = []

def find_intention_collection_id(data, intentionList_name):
    for item in data:
        if item.get('name') == intentionList_name:
            return item.get('guid')
    return None
intentionCollectionIds = find_intention_collection_id(data_intentionList['data'], intentionList_name)
print(intentionCollectionIds)
if not intentionCollectionIds:
    print(f"Intention Collection ID for '{intentionList_name}' not found.")
    exit(1)
#-------------------------------获取意图集合：intentionCollectionIds

#-------------------------------新建话术
body_newSpeech = {
"speechName": f"TEST话术{num}",
"bizId": biz2_id,
"tenant": tenant,
"intentionCollectionIds": [
intentionCollectionIds
],
"isFullTtsCompose": "false",
"bizScene": biz_scene,
"asrServer": "alimrcp",
"asrCode": "default_alimrpc_asr_code",
"ttsServer": "alimrcp",
"modelId": "voice-d8e8f58",
"ttsModelParam": {
"speechRate": 0,
"pitchRate": 0,
"volume": 50
},
"bffAction": "css.call.speech.create"
}
data_newSpeech = getResponseBody(body_newSpeech)
if data_newSpeech.get('code') != "0":
    print(f"\033[1;31;42m话术创建失败: {data_newSpeech.get('msg')}\033[0m")
    exit(1)
else:
    print(f"\033[4;33m话术创建成功\033[0m")
#-------------------------------新建话术

#-------------------------------获取上一个新增话术的groupId
body_get_groupId = {
"pageNum": 1,
"pageSize": 100,
"tenants": [],
"notAllowRepeat": "true",
"bffAction": "css.call.speech.listSpeech"
}
data_get_groupId = getResponseBody(body_get_groupId)
groupId = data_get_groupId.get('data', {}).get('list', [{}])[0].get('groupId')
if not groupId:
    print("Group ID not found.")
    exit(1)
# else:
#     print(groupId)
#-------------------------------获取上一个新增话术的groupId

#-------------------------------获取speechGuid
body_get_speechGuid = {"bffAction":"css.call.speech.versionTab","groupId":groupId}
data_get_speechGuid = getResponseBody(body_get_speechGuid)
speechGuid = data_get_speechGuid.get('data', {})[0].get('speechGuid')
if not speechGuid:
    print("Speech Guid not found.")
    exit(1)
# else:
#     print(f"Speech Guid found: {speechGuid}")
#-------------------------------获取speechGuid

#-------------------------------新增迭代

# 按照迭代位为主版本号进行处理
class Version:
    def __init__(self, version_str):
        self.prefix = version_str[0]  # 获取V
        self.major, self.minor, self.patch = map(int, version_str[1:].split('.'))
    
    def increment_major(self):
        self.major += 1
        self.minor = 0
        self.patch = 0
        return self
    
    def __str__(self):
        return "{}{}.{}.{}".format(self.prefix, self.major, self.minor, self.patch)

# 获取版本字符串并创建Version对象
version_str = "V1.0.0"
if version_str:  # 确保有值
    version_obj = Version(version_str)  
    new_version = version_obj.increment_major()
    # print(f"新版本号: {new_version}")
else:
    print("lastVersion_1 is empty or None")
# 获取版本字符串并创建Version对象

body_new_version_speech = {
"bffAction": "css.call.speech.draft.create",
"copySpeechGuid": speechGuid,
"groupId": groupId,
"speechVersion": str(new_version),
"versionDesc": "test",
"speechVersionName": str(new_version)
}
new_speechGuid = None
data_new_version_speech = getResponseBody(body_new_version_speech)

if data_new_version_speech.get('code') != "0":
    print(f"新建迭代失败: {data_new_version_speech.get('msg')}")
    exit(1)
else:
    print(f"\033[4;33m新建迭代成功\033[0m")
    new_speechGuid = data_new_version_speech.get('data', {}).get('speechGuid')
    # print(speechGuid)
#-------------------------------新增迭代:speechGuid
    
#-------------------------------复制话术：使用上面新增迭代话术进行复制
body_copy_speech = {
"speechName": f"TESTcopy话术{num}",
"bizId": biz2_id,
"tenant": tenant,
"intentionCollectionIds": [
    intentionCollectionIds
],
"isFullTtsCompose": "false",
"copySpeechGuid": new_speechGuid,
"bizScene": biz_scene,
"asrServer": "alimrcp",
"asrCode": "default_alimrpc_asr_code",
"ttsServer": "alimrcp",
"modelId": "voice-d8e8f58",
"ttsModelParam": {
"speechRate": 0,
"pitchRate": 0,
"volume": 50
},
"bffAction": "css.call.speech.copy"
}
data_copy_speech = getResponseBody(body_copy_speech)
if data_copy_speech.get('code') != "0":
    print(f"\033[1;31;42m话术复制失败: {data_copy_speech.get('msg')}\033[0m")
    exit(1)
else:
    print(f"\033[4;33m话术复制成功\033[0m")
#-------------------------------复制话术：使用上面新增迭代话术进行复制