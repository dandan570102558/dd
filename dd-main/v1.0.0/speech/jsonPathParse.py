import os
import jpype
current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"3rd/jar")

required_jars = [
    "ApacheJMeter_core.jar",      # JMeter 核心
    "json-path-2.4.0.jar",        # JSONPath 实现
    "json-smart-2.3.jar",         # 缺失的依赖
    "accessors-smart-1.2.jar",    # 可选但推荐
    "slf4j-api-1.7.30.jar"        # 日志依赖
]
classpath = [os.path.join(current_dir, jar) for jar in required_jars]
jpype.startJVM(
    classpath=classpath,
    convertStrings=True  # 自动处理 Java/String 转换
)

def jsonPathParse(body,jsPd):
    JsonPath = jpype.JClass("com.jayway.jsonpath.JsonPath")
    try:
        json_str = body
        json_path_date = jsPd
        result = JsonPath.read(json_str, json_path_date)
        return result
    except Exception as e:
        print(f"Error in jsonPath: {e}")
        return None
    
