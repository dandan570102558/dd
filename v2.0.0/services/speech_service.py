import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.api_client import APIClient
from core.version_manager import Version

import random
from typing import Dict, Optional, Tuple


try:
    from core.version_manager import Version
except ImportError:
    # 备用方案：内联Version类定义
    class Version:
        def __init__(self, version_str: str = "V1.0.0"):
            if not version_str.startswith('V'):
                raise ValueError("Version must start with 'V'")
            self.prefix = 'V'
            self.major, self.minor, self.patch = map(int, version_str[1:].split('.'))
        
        def increment_major(self) -> str:
            self.major += 1
            self.minor = 0
            self.patch = 0
            return str(self)
        
        def __str__(self) -> str:
            return f"{self.prefix}{self.major}.{self.minor}.{self.patch}"

class SpeechService:
    def __init__(self, config_path: str):
        """
        初始化语音服务
        :param config_path: 配置文件路径
        """
        self.client = APIClient(config_path)
        self.config = self.client.config
        self.random_suffix = ''.join(random.choices('0123456789', k=6))

    def create_speech_workflow(self) -> Dict:
        """
        完整的话术创建工作流
        返回: {
            "base_speech": 基础话术信息,
            "new_version": 新版本信息,
            "copied_speech": 复制的话术信息
        }
        """
        try:
            # 1. 获取业务ID
            biz2_id, biz_scene = self._get_business_ids()
            
            # 2. 获取意图集合ID
            intent_id = self._get_intention_id(biz2_id)
            
            # 3. 创建基础话术
            base_speech = self._create_base_speech(biz2_id, biz_scene, intent_id)
            
            # 4. 创建版本迭代
            new_version = self._create_speech_version(
                base_speech["groupId"],
                base_speech["speechGuid"]
            )
            
            # 5. 复制话术
            copied_speech = self._copy_speech(
                biz2_id,
                biz_scene,
                intent_id,
                new_version["speechGuid"]
            )
            
            return {
                "base_speech": base_speech,
                "new_version": new_version,
                "copied_speech": copied_speech
            }
            
        except Exception as e:
            self.print_error(f"💢 话术工作流执行失败: {str(e)}")
            raise

    def _get_business_ids(self) -> Tuple[str, str]:
        """
        获取业务ID和场景ID
        返回: (biz2_id, biz_scene)
        """
        try:
            response = self.client.post(
                "bizTree/list",
                {"includeScene": True, "bffAction": "css.call.bizTree.list"}
            )
            
            # 添加None检查
            if not response or not isinstance(response.get('data'), list):
                raise ValueError("API返回的业务树数据无效")
            
            biz2_id = self._find_id_in_tree(response['data'], self.config["bizName_2"])
            biz_scene = self._find_id_in_tree(response['data'], self.config["bizName_3"])
            
            if not biz2_id:
                raise ValueError(f"未找到业务分类: {self.config['bizName_2']}")
            if not biz_scene:
                raise ValueError(f"未找到业务场景: {self.config['bizName_3']}")
                
            return biz2_id, biz_scene
        except Exception as e:
            self.print_error("🔍 获取业务ID失败！")
            raise

    def _find_id_in_tree(self, data: list, target_name: str) -> Optional[str]:
        """
        递归查找树形结构中的ID
        """
        if not isinstance(data, list):  # 安全检查
            return None
            
        for item in data:
            if not isinstance(item, dict):
                continue
                
            if item.get('name') == target_name:
                return item.get('id')
            if 'children' in item:
                if found := self._find_id_in_tree(item['children'], target_name):
                    return found
        return None

    def _get_intention_id(self, biz_id: str) -> str:
        """
        获取意图集合ID
        """
        try:
            response = self.client.post(
                "intention/list",
                {
                    "bizId": biz_id,
                    "bffAction": "css.call.new.intention.kcList"
                }
            )
            
            # 添加None检查
            if not response or not isinstance(response.get('data'), list):
                raise ValueError("API返回的意图列表数据无效")
            
            intent_name = self.config["intentionCollectionName"]
            for item in response['data']:
                if isinstance(item, dict) and item.get('name') == intent_name:
                    if not item.get('guid'):
                        raise ValueError("找到的意图集合GUID为空")
                    return item['guid']
                    
            raise ValueError(f"未找到意图集合: {intent_name}")
        except Exception as e:
            self.print_error("🧠 获取意图集合ID失败！")
            raise

    def _create_base_speech(self, biz_id: str, biz_scene: str, intent_id: str) -> Dict:
        """
        创建基础话术
        返回: {
            "groupId": str,   # 话术组ID 
            "speechGuid": str  # 话术唯一标识
        }
        """
        try:
            body = {
                "speechName": f"TEST话术{self.random_suffix}",
                "bizId": biz_id,
                "tenant": self.config["tenant"],
                "intentionCollectionIds": [intent_id],
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
            
            response = self.client.post("speech/create", body)
            if not response or response.get('code') != "0":
                self.print_error("🔥 新增话术失败！")
                raise RuntimeError(f"API返回异常: {response.get('msg') if response else '空响应'}")
            
            if not response.get('data') or not response['data'].get('groupId'):
                raise ValueError("API返回缺少groupId字段")
                
            return {
                "groupId": self._get_speech_group_id(),
                "speechGuid": self._get_speech_guid(response['data']['groupId'])
            }
        except Exception as e:
            self.print_error("🔥 新增话术流程异常！")
            raise

    def _get_speech_group_id(self) -> str:
        """
        获取话术组ID
        """
        try:
            response = self.client.post(
                "speech/list",
                {
                    "pageNum": 1,
                    "pageSize": 100,
                    "tenants": [],
                    "notAllowRepeat": "true",
                    "bffAction": "css.call.speech.listSpeech"
                }
            )
            
            if not response or not response.get('data') or not response['data'].get('list'):
                raise RuntimeError("获取话术组ID失败: API返回数据无效")
            
            first_item = response['data']['list'][0]
            if not first_item.get('groupId'):
                raise ValueError("首个话术项的groupId为空")
                
            return first_item['groupId']
        except Exception as e:
            self.print_error("📦 获取话术组ID失败！")
            raise

    def _get_speech_guid(self, group_id: str) -> str:
        """
        获取话术GUID
        """
        try:
            response = self.client.post(
                "speech/version",
                {
                    "bffAction": "css.call.speech.versionTab",
                    "groupId": group_id
                }
            )
            
            if not response or not response.get('data'):
                raise RuntimeError("获取speechGuid失败: API返回数据无效")
            
            first_version = response['data'][0]
            if not first_version.get('speechGuid'):
                raise ValueError("首个版本项的speechGuid为空")
                
            return first_version['speechGuid']
        except Exception as e:
            self.print_error("🆔 获取speechGuid失败！")
            raise

    def _create_speech_version(self, group_id: str, speech_guid: str) -> Dict:
        """
        创建话术新版本
        返回: {
            "version": str,    # 版本号 
            "speechGuid": str  # 新版本GUID
        }
        """
        try:
            new_version = Version().increment_major()
            
            body = {
                "bffAction": "css.call.speech.draft.create",
                "copySpeechGuid": speech_guid,
                "groupId": group_id,
                "speechVersion": new_version,
                "versionDesc": "auto-created",
                "speechVersionName": new_version
            }
            
            response = self.client.post("speech/version/create", body)
            if not response or response.get('code') != "0":
                self.print_error("🚨 新增迭代失败！")
                raise RuntimeError(f"API返回异常: {response.get('msg') if response else '空响应'}")
            
            if not response.get('data') or not response['data'].get('speechGuid'):
                raise ValueError("API返回缺少speechGuid字段")
                
            return {
                "version": new_version,
                "speechGuid": response['data']['speechGuid']
            }
        except Exception as e:
            self.print_error("🚨 版本创建流程异常！")
            raise

    def _copy_speech(self, biz_id: str, biz_scene: str, intent_id: str, copy_guid: str) -> Dict:
        """
        复制话术
        返回: dict 包含新话术的所有信息
        """
        try:
            body = {
                "speechName": f"TESTcopy话术{self.random_suffix}",
                "bizId": biz_id,
                "tenant": self.config["tenant"],
                "intentionCollectionIds": [intent_id],
                "isFullTtsCompose": "false",
                "copySpeechGuid": copy_guid,
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
            
            response = self.client.post("speech/copy", body)
            if not response or response.get('code') != "0":
                self.print_error("💥 复制话术失败！")
                raise RuntimeError(f"API返回异常: {response.get('msg') if response else '空响应'}")
                
            if not response.get('data'):
                raise ValueError("API返回数据为空")
                
            return response['data']
        except Exception as e:
            self.print_error("💥 话术复制流程异常！")
            raise

    def print_success(self, message: str):
        """打印成功信息（绿色）"""
        print(f"\033[32m✅ {message}\033[0m")

    def print_error(self, message: str):
        """打印错误信息（红色+符号）"""
        print(f"\033[31m❗️ {message}\033[0m")

if __name__ == "__main__":
    try:
        service = SpeechService("configs/global_config.json")
        result = service.create_speech_workflow()
        
        service.print_success("话术创建流程完成！")
        print("基础话术:", result["base_speech"])
        print("新版本:", result["new_version"])
        print("复制话术:", result["copied_speech"])
        
    except Exception as e:
        print(f"\033[31m❗️ 程序终止: {str(e)}\033[0m")
        exit(1)