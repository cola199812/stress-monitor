# yingjiyuan

一个基于 Next.js + Flask 的信息管理/数据管理系统（前后端同仓库），用于"数据采集/舆情分析/知识问答/数据看板"的一体化展示与交互。

## 启动流程

### 首次启动（数据库初始化）

**⚠️ 首次使用需要先初始化数据库和导入数据**

#### 1. 环境准备
确保以下服务已安装并运行：
- **MySQL 8.x**：用于存储业务数据
- **Neo4j**：用于知识图谱（可选但推荐）
- **Node.js 18+**：前端运行环境
- **Python 3.10+**：后端运行环境

#### 2. 安装依赖
```bash
# 前端依赖
npm install

# 后端依赖
cd backend
pip install -r requirements.txt
cd ..
```

#### 4. 数据库初始化

**步骤 4.1：创建 Neo4j 数据库结构**
```bash
# 创建 Neo4j 数据库结构和约束
python backend/scripts/create_neo4j_schema.py

# 可选：创建示例数据结构
python backend/scripts/create_neo4j_schema.py --sample-data
```

**步骤 4.2：导入初始数据**
```bash
# 方式一：完整导入（推荐）- 先导入 Neo4j dump 文件，再导入 MySQL 数据
python backend/scripts/import_data_to_neo4j.py --action both

# 方式二：仅导入 Neo4j dump 文件
python backend/scripts/import_data_to_neo4j.py --action dump

# 方式三：仅从 MySQL 导入数据到 Neo4j
python backend/scripts/import_data_to_neo4j.py --action mysql
```

**注意事项：**
- Neo4j dump 文件导入需要停止 Neo4j 服务，导入完成后重启服务
- 如果没有现有的 MySQL 数据，可以跳过 MySQL 导入步骤
- 使用 `--clear` 参数可以清空现有数据后重新导入
- 使用 `--verbose` 参数可以查看详细的导入过程

#### 5. 启动服务

**启动后端：**
```bash
cd backend
python run.py
```
后端默认运行在 `http://127.0.0.1:5050`

**启动前端：**
```bash
# 开发模式
npm run dev

# 生产模式
npm run build
npm start
```
前端默认运行在 `http://localhost:3000`

### 日常启动（已初始化）

如果已经完成首次初始化，日常启动只需：

#### 前端
```bash
npm run dev
```

#### 后端
```bash
cd backend
python run.py
```

### 服务配置说明

#### Neo4j 配置
- **默认连接**：`bolt://localhost:7687`
- **默认用户**：`neo4j` / `123456789`
- **配置文件**：`backend/app/services/neo4j_client.py`
- **环境变量**：`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`

#### MySQL 配置
- **默认连接**：`127.0.0.1:3306`
- **默认用户**：`root` / `123456`
- **默认数据库**：`medical_system`
- **配置文件**：`backend/app/__init__.py`~
- **环境变量**：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DB`

### 故障排除

#### 常见问题

1. **Neo4j 连接失败**
   - 确认 Neo4j 服务已启动
   - 检查连接参数和密码
   - 查看 Neo4j 日志文件

2. **MySQL 连接失败**
   - 确认 MySQL 服务已启动
   - 检查数据库是否存在（`medical_system`）
   - 验证用户权限

3. **数据导入失败**
   - 使用 `--verbose` 参数查看详细错误信息
   - 确认 dump 文件路径正确
   - 检查磁盘空间是否充足

4. **前后端通信问题**
   - 检查 `NEXT_PUBLIC_API_BASE_URL` 环境变量
   - 确认后端服务正常运行在 5050 端口
   - 查看浏览器控制台错误信息

#### 重新初始化数据库

如需重新初始化，可以使用以下命令：
```bash
# 清空并重新导入所有数据
python backend/scripts/import_data_to_neo4j.py --action both --clear --verbose
```

## Tech Stack
- **Frontend**: Next.js 15, React 19, TypeScript, TailwindCSS, shadcn/ui
- **Backend**: Flask, SQLAlchemy, Flask-CORS
- **Database**: MySQL 8.x
- **Graph Database**: Neo4j（知识图谱）
- **AI/ML**: OpenAI API, sentence-transformers, ChromaDB
- **Translation**: Baidu/Youdao/Google Translation APIs

## Requirements
- Node.js 18+ (建议 20+)
- Python 3.10+
- MySQL 8.x
- Neo4j（可选，用于知识图谱功能）

## Project Structure
```
├── src/                  # Next.js 前端代码
│   ├── app/              # App Router 页面和布局
│   ├── components/       # React 组件
│   ├── lib/              # 工具函数和配置
│   └── store/            # 状态管理 (Zustand)
├── backend/              # Flask 后端代码
│   ├── app/              # 应用主体
│   │   ├── routes/       # API 路由
│   │   ├── services/     # 业务逻辑服务
│   │   └── models.py     # 数据模型
│   ├── scripts/          # 数据库脚本
│   └── run.py            # 后端启动入口
└── README.md
```

## 功能模块

- **数据看板** `/dashboard`
  - 趋势对比（文献/新闻/召回）、来源统计、情感占比、关键词词云
- **信息采集** `/collect`
  - 文献/新闻/召回 三类独立采集页；本地优先展示；"继续采集"触发后端爬虫并入库绑定
- **信息管理** `/info_management`
  - 管理实体，实体关系，数据，评分
- **知识问答** `/qa`
  - 知识图谱列表 + AI 问答

## 环境配置

### Frontend Env
在项目根目录创建 `.env.local`：
```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:5050
```

### Backend Env
后端支持读取环境变量（并会尝试加载 `.env`）。示例：
```env
# MySQL 数据库配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=medical_system

# 后端服务配置
BACKEND_HOST=127.0.0.1
BACKEND_PORT=5050
FLASK_DEBUG=1

# CORS 配置
CORS_ORIGINS=http://localhost:3000

# Neo4j 配置（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=123456789
NEO4J_ENCRYPTED=false

# 翻译服务配置（可选）
BAIDU_APPID=your_baidu_appid
BAIDU_KEY=your_baidu_key
YOUDAO_APP_KEY=your_youdao_key
YOUDAO_APP_SECRET=your_youdao_secret

# OpenAI 配置（可选）
OPENAI_API_KEY=your_openai_key
```

## Notes
- `backend/venv/`、`node_modules/`、`.next/`、`.env*` 等不应提交到仓库
- 如需部署，请分别构建前端并在服务器侧配置后端环境变量
- Neo4j、AI/ML 功能为可选模块，不影响基础功能运行

## License
Apache-2.0