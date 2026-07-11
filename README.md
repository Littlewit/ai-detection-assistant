# AI 检测助手

> AI 智能检测辅助系统

面向第三方检测认证实验室的 AI 工具，基于通义千问大模型，为检测工程师提供智能问答、样板拆分图生成和报告五步审核三大核心功能。

---

## 功能特性

### 🤖 智能问答（RAG 增强）
- 基于标准库（IEC/EN/GB/ASTM/UL/REACH/RoHS 等）的专业问答
- 支持 10 大检测类别分区检索
- **流式输出** + **Markdown 实时渲染**

### 🖼️ 样板拆分图生成
- 上传产品图片，千问 VL 多模态模型自动识别组件结构
- 生成标准样板拆分示意图
- AI 自审拆分结果质量

### 📝 报告审核（五步工作流）
1. 一致性审核 — 申请表 vs 报告
2. 标准合规审核 — 拆分表 vs 报告
3. 数据完整性审核
4. CNAS/CMA 格式合规审核
5. 标准版本有效性审核
- **流式进度反馈** + **流式报告输出**

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | Python 3.13 + FastAPI |
| AI 框架 | LangChain + LangGraph |
| 大模型 | 通义千问（qwen-max / qwen-vl-max / text-embedding-v3） |
| 向量数据库 | ChromaDB |
| 异步任务 | Celery + Redis |
| 前端 | HTML + JavaScript + CSS |
| 部署 | Docker + docker-compose |

---

## 项目结构

```
AI-detection-assistant/
├── app/                        # 后端核心代码
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 全局配置（含 10 大检测类别）
│   ├── agents/                 # AI Agent
│   │   ├── qa_agent.py         # RAG 问答 Agent（流式）
│   │   ├── split_agent.py      # 样板拆分 Agent
│   │   └── review_agent.py     # 五步审核 Agent（流式）
│   ├── api/                    # API 路由
│   │   ├── qa_router.py        # 问答接口
│   │   ├── split_router.py     # 拆分接口
│   │   └── review_router.py    # 审核接口
│   ├── models/                 # 数据模型
│   │   ├── llm.py              # 千问模型初始化
│   │   └── schemas.py          # Pydantic 模型
│   └── services/               # 业务服务
│       ├── knowledge_base.py   # 知识库管理
│       ├── document_parser.py  # 文档解析
│       └── image_analyzer.py   # 图像分析
├── static/                     # 前端资源
│   ├── index.html              # 主页面
│   ├── css/style.css           # 样式表
│   └── js/app.js               # 交互逻辑
├── workers/                    # Celery 异步任务
│   ├── celery_app.py
│   └── tasks.py
├── scripts/                    # 脚本
│   └── init_knowledge_base.py  # 知识库初始化
├── data/                       # 数据目录（运行时生成）
│   ├── standards/              # 标准文档（按 10 大类别）
│   ├── uploads/                # 用户上传文件
│   ├── chroma_db/              # 向量数据库
│   └── reports/                # 审核报告
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example                # 环境变量模板
└── README.md
```

---

## 快速开始

### 前置条件

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 包管理器（推荐）或 pip
- 阿里云 DashScope API Key（[获取地址](https://dashscope.console.aliyun.com/apiKey)）

### 本地开发

```bash
# 1. 克隆项目
git clone https://github.com/your-username/ai-detection-assistant.git
cd ai-detection-assistant

# 2. 创建虚拟环境（使用 uv）
uv venv .venv --python 3.13
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. 安装依赖
uv pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY

# 5. 初始化知识库（可选）
python scripts/init_knowledge_base.py

# 6. 启动开发服务器
python -m uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

访问 http://localhost:8888 即可使用。

---

## Docker 部署（阿里云 ECS 2C2G）

### 前置条件

- Docker + Docker Compose
- 已配置好 `.env` 文件

### 部署步骤

```bash
# 1. 在服务器上克隆项目
git clone https://github.com/your-username/ai-detection-assistant.git
cd AI-detection-assistant

# 2. 配置环境变量
cp .env.example .env
vi .env   # 填入 DASHSCOPE_API_KEY

# 3. 构建并启动
docker compose up -d --build

# 4. 查看日志
docker compose logs -f app
```

### 资源分配（2 核 2G）

| 容器 | 内存 | CPU | 说明 |
|---|---|---|---|
| ai-detect-app | 1024 MB | 1.0 核 | FastAPI 主服务 |
| ai-detect-worker | 512 MB | 0.5 核 | Celery 异步任务（并发 2） |
| ai-detect-redis | 256 MB | 0.5 核 | Redis（上限 128MB） |

### 常用命令

```bash
# 重启服务
docker compose restart

# 停止服务
docker compose down

# 重新构建
docker compose up -d --build

# 查看容器状态
docker compose ps
```

---

## API 接口

### 智能问答

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/qa/ask` | 完整响应 |
| POST | `/api/qa/ask/stream` | SSE 流式响应 |

```json
// 请求
{ "question": "RoHS 2.0 对邻苯二甲酸酯的限制值是多少？", "category": "chemical" }
```

### 样板拆分

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/split/upload` | 上传产品图片 |
| POST | `/api/split/analyze/{filename}` | 分析图片生成拆分图 |
| GET | `/api/split/diagram/{filename}` | 获取拆分示意图 |

### 报告审核

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/review/upload` | 上传审核文件 |
| POST | `/api/review/review` | 完整审核响应 |
| POST | `/api/review/review/stream` | SSE 流式审核（含步骤进度） |

### 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 服务健康状态 |

---

## 检测类别

| 分区 | 类别 |
|---|---|
| `chemical` | 有害物质检测（RoHS/REACH/CPSIA/加州65/POPs） |
| `safety` | 安规检测（IEC/EN/UL/GB 电气安全） |
| `emc` | 电磁兼容检测（EMI/EMS/FCC Part 15） |
| `reliability` | 环境可靠性（温湿度/盐雾/振动/老化） |
| `material` | 材料分析（金属/非金属/REACH SVHC） |
| `textile` | 纺织品/鞋类/皮革（GB/T/ISO/AATCC） |
| `toy` | 玩具检测（EN71/ASTM F963/GB 6675） |
| `food_contact` | 食品接触材料（FDA/EU 10/2011/GB 4806） |
| `energy` | 能效检测（ErP/Energy Star） |
| `certification` | 认证流程（CE/FCC/UL/CB/CCC） |

---

## 资质信息

- **CNAS**: L7462
- **CMA**: 2016192581Z
- **CPSC**: #1517

---

## License

MIT License
