# 需求生成系统（Demo论文演示版）

本仓库为原项目的演示仓库结构，保持原有逻辑与代码不变，仅对目录进行清晰拆分：前端、后端与实现代码分离。同时提供快速运行说明，便于论文 Demo 演示。

## 仓库结构
- frontend/ 前端演示（Streamlit）
  - frontend.py
- backend/ 后端服务（FastAPI）
  - server/
    - main.py
    - static/index.html
- Req/ 实现代码（保持原目录与模块命名）
  - config、llm、tools、filters、experiment、demo 等
- storage/ 运行期存储（后端自动创建）
  - uploads/、downloads/
- jobs.json 任务记录文件（后端使用）

核心代码参考：
- 后端入口: [main.py](file:///d:/nju/需求生成系统/github/backend/server/main.py)
- 前端演示: [frontend.py](file:///d:/nju/需求生成系统/github/frontend/frontend.py)
- 生成流程: [run_multi_model_unified6_demo.py](file:///d:/nju/需求生成系统/github/Req/demo/run_multi_model_unified6_demo.py)

## 环境准备
- Python ≥ 3.11
- 建议使用虚拟环境（venv/conda）
- 依赖安装（示例）：

```bash
  pip install -r requirements.txt
  ```

### 外部工具

- apktool（用于 APK 解析），需安装并可被系统找到：
  - 方式一：将 apktool 加入 PATH
  - 方式二：设置环境变量 APKTOOL / APKTOOL_PATH / APKTOOL_HOME 指向 apktool(.bat/.exe/.jar)
- Java 环境（如使用 apktool.jar）

## 运行说明
### 启动后端服务（FastAPI）
在仓库根目录运行：

```bash
python backend/server/main.py
```

默认监听 0.0.0.0:8001，静态页面为 backend/server/static/index.html。

接口功能：
- /api/upload：上传 APK，返回 job_id
- /api/generate：启动生成任务（异步）
- /api/status/{job_id}：查询任务状态与结果
- /api/download/{job_id}/{file_type}：下载生成结果（srs/tests/test_json/report/zip）

### 启动前端演示（Streamlit）
在仓库根目录运行：

```bash
streamlit run frontend/frontend.py
```

在页面中选择语言与生成策略，输入应用目录路径（已解析的目录），进行演示生成。

## 环境变量
- DASHSCOPE_API_KEY：模型调用密钥（也可通过后端 /api/config 设置）
- DASHSCOPE_TEMPERATURE：采样温度（默认 0.01）
- DASHSCOPE_TOP_P：采样 top_p（默认 1.0）

## 输出位置
- 统一输出目录由 [RunConfig.py](file:///d:/nju/需求生成系统/github/Req/config/RunConfig.py) 定义：
  - Req/output/software_requirements
  - Req/output/test_requirements
  - Req/output/test_json
  - Req/output/analysis
- Demo组合输出位于：Req/demo/output/{组合}/{应用名}/
  - {应用名}_SRS.json
  - {应用名}_TestRequirements.json
  - {应用名}_data.zip（包含 SRS、Tests 及可用的 test_json）
  - 生成的 Word 报告：{应用名}_功能测试报告.docx



