import sys
from pathlib import Path
# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
import importlib
# from core import version_manager

# # 强制重新加载模块
# version_manager = importlib.reload(version_manager)
# version_manager = importlib.reload(version_manager)
# from core.version_manager import Version
import random
from typing import Dict, Optional, Tuple
from core.api_client import APIClient

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
            
            # 2. 获取意图集合ID <- 重要！后续流程依赖此ID
            intent_id = self._get_intention_id(biz2_id)
            
            # 3. 创建基础话术
            base_speech = self._create_base_speech(biz2_id, biz_scene, intent_id)
            
            # 4. 创建版本迭代 <- 重要！生成新版本GUID
            new_version = self._create_speech_version(
                base_speech["groupId"],  # <- 重要！话术组ID
                base_speech["speechGuid"]  # <- 重要！基础话术GUID
            )
            
            # 5. 复制话术
            copied_speech = self._copy_speech(
                biz2_id,
                biz_scene,
                intent_id,
                new_version["speechGuid"]  # <- 重要！使用新版本GUID复制
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
        返回: (biz2_id, biz_scene) <- 重要！这两个ID用于后续所有操作
        """
        try:
            response = self.client.post(
                "bizTree/list",
                {"includeScene": True, "bffAction": "css.call.bizTree.list"}
            )
            
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
        for item in data:
            if item.get('name') == target_name:
                return item['id']
            if 'children' in item:
                if found := self._find_id_in_tree(item['children'], target_name):
                    return found
        return None

    def _get_intention_id(self, biz_id: str) -> str:
        """
        获取意图集合ID <- 重要！用于话术创建的必需参数
        """
        try:
            response = self.client.post(
                "intention/list",
                {
                    "bizId": biz_id,
                    "bffAction": "css.call.new.intention.kcList"
                }
            )
            
            intent_name = self.config["intentionCollectionName"]
            for item in response['data']:
                if item.get('name') == intent_name:
                    return item['guid']  # <- 重要！意图集合GUID
                    
            raise ValueError(f"未找到意图集合: {intent_name}")
        except Exception as e:
            self.print_error("🧠 获取意图集合ID失败！")
            raise

    def _create_base_speech(self, biz_id: str, biz_scene: str, intent_id: str) -> Dict:
        """
        创建基础话术
        返回: {
            "groupId": str,   # <- 重要！话术组ID 
            "speechGuid": str  # <- 重要！话术唯一标识
        }
        """
        try:
            body = {
                "speechName": f"TEST话术{self.random_suffix}",
                "bizId": biz_id,
                "tenant": self.config["tenant"],
                "intentionCollectionIds": [intent_id],  # <- 重要！意图集合ID
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
            if response.get('code') != "0":
                self.print_error("🔥 新增话术失败！")
                raise RuntimeError(f"详情: {response.get('msg')}")
                
            return {
                "groupId": self._get_speech_group_id(),
                "speechGuid": self._get_speech_guid(response['data']['groupId'])  # <- 重要！
            }
        except Exception as e:
            self.print_error("🔥 新增话术流程异常！")
            raise

    def _get_speech_group_id(self) -> str:
        """
        获取话术组ID <- 重要！用于版本管理
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
            
            if not response['data']['list']:
                raise RuntimeError("话术列表为空")
                
            return response['data']['list'][0]['groupId']  # <- 重要！首个话术组ID
        except Exception as e:
            self.print_error("📦 获取话术组ID失败！")
            raise

    def _get_speech_guid(self, group_id: str) -> str:
        """
        获取话术GUID <- 重要！唯一标识符
        """
        try:
            response = self.client.post(
                "speech/version",
                {
                    "bffAction": "css.call.speech.versionTab",
                    "groupId": group_id
                }
            )
            
            if not response['data']:
                raise RuntimeError("版本数据为空")
                
            return response['data'][0]['speechGuid']  # <- 重要！最新版本GUID
        except Exception as e:
            self.print_error("🆔 获取speechGuid失败！")
            raise

    def _create_speech_version(self, group_id: str, speech_guid: str) -> Dict:
        """
        创建话术新版本
        返回: {
            "version": str,    # <- 重要！版本号 
            "speechGuid": str  # <- 重要！新版本GUID
        }
        """
        try:
            new_version = Version().increment_major()
            
            body = {
                "bffAction": "css.call.speech.draft.create",
                "copySpeechGuid": speech_guid,  # <- 重要！基于此GUID创建
                "groupId": group_id,
                "speechVersion": new_version,
                "versionDesc": "auto-created",
                "speechVersionName": new_version
            }
            
            response = self.client.post("speech/version/create", body)
            if response.get('code') != "0":
                self.print_error("🚨 新增迭代失败！")
                raise RuntimeError(f"详情: {response.get('msg')}")
                
            return {
                "version": new_version,
                "speechGuid": response['data']['speechGuid']  # <- 重要！
            }
        except Exception as e:
            self.print_error("🚨 版本创建流程异常！")
            raise

    def _copy_speech(self, biz_id: str, biz_scene: str, intent_id: str, copy_guid: str) -> Dict:
        """
        复制话术
        返回: dict <- 包含新话术的所有信息
        """
        try:
            body = {
                "speechName": f"TESTcopy话术{self.random_suffix}",
                "bizId": biz_id,
                "tenant": self.config["tenant"],
                "intentionCollectionIds": [intent_id],  # <- 重要！
                "isFullTtsCompose": "false",
                "copySpeechGuid": copy_guid,  # <- 重要！源话术GUID
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
            if response.get('code') != "0":
                self.print_error("💥 复制话术失败！")
                raise RuntimeError(f"详情: {response.get('msg')}")
                
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

# 示例用法
if __name__ == "__main__":
    try:
        service = SpeechService("configs/global_config.json")
        result = service.create_speech_workflow()
        
        service.print_success("话术创建流程完成！")
        print("基础话术:", result["base_speech"])
        print("新版本:", result["new_version"])
        print("复制话术:", result["copied_speech"])
        
    except Exception as e:
        service.print_error(f"程序终止: {str(e)}")
        exit(1)