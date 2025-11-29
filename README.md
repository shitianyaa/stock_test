# 📈 DeepSeek 智能投研系统 (AI Investment Research)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Tushare](https://img.shields.io/badge/Data-Tushare%20Pro-red)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20V3-blueviolet)
![License](https://img.shields.io/badge/License-MIT-green)

**DeepSeek 智能投研系统** 是一款基于 **Streamlit** 开发的现代化金融分析工具。它深度整合了 **Tushare Pro** 的专业金融大数据与 **DeepSeek V3** 大语言模型的逻辑推理能力，为投资者提供“机构级”的实时个股分析报告。

---

## ✨ 核心功能特性

### 1. 📡 全市场实时数据接入
- **多市场支持**：完美支持 **A股**（如 `600519`）与 **港股**（如 `00700`，需积分权限）的实时行情查询。
- **智能搜索**：支持代码直接输入或中文名称模糊搜索（如输入“腾讯”自动匹配）。
- **核心指标**：自动获取收盘价、成交量、换手率、波动率、PE(TTM)、PB、总市值等关键数据。

### 2. 🧠 DeepSeek 深度推理 (多风格)
内置三种不同风格的 AI 分析师，满足不同投资偏好：
- 🧐 **稳健理智**：像机构首席一样思考，注重基本面与风险控制。
- 🔥 **激进犀利**：化身游资操盘手，观点鲜明，直击博弈痛点。
- ⚡ **短线博弈**：专注于次日或短周期的技术面爆发力。

### 3. 📊 专业量化看板
- **技术指标监控**：集成 **MA均线系统** (5/10/20日)、**MACD**、**RSI**、**布林带** (Bollinger Bands)。
- **宏观市场罗盘**：实时扫描大盘指数（沪深300/恒生指数）与市场情绪（乐观/悲观/中性）。
- **行业基本面**：展示所属行业板块及公司市值规模。

### 4. 🛡️ 企业级功能体验
- **历史记录回溯**：自动保存分析记录，支持随时查看过往判断与对比。
- **数据导出**：一键下载 **CSV 格式** 的完整数据与分析报告（完美适配 Excel，无乱码）。
- **安全访问**：内置密码访问拦截机制，保护您的 API 额度与数据安全。
- **高端 UI 设计**：采用“深海蓝”金融科技配色，响应式卡片布局，视觉体验极佳。

---

## 📂 项目结构

```text
stock_test/
├── app.py                # 项目主入口 (UI 与交互逻辑)
├── core_logic.py         # AI 核心逻辑 (DeepSeek API 调用与 Prompt 构建)
├── data_utils.py         # 数据层 (Tushare 接口封装、指标计算、异常处理)
├── requirements.txt      # 项目依赖库列表
└── README.md             # 项目说明文档
```

---

## 🚀 快速开始 (本地运行)

### 1. 克隆项目
```bash
git clone https://github.com/shitianyaa/stock_analysis.git
cd stock_analysis
```

### 2. 安装依赖
确保你的电脑已安装 Python 3.8 或以上版本。
```bash
pip install -r requirements.txt
```

### 3. 配置密钥 (Secrets)
本项目依赖外部 API，请在项目根目录下新建 `.streamlit` 文件夹，并在其中创建 `secrets.toml` 文件：

```bash
mkdir .streamlit
# Windows 用户请手动创建 .streamlit/secrets.toml 文件
```

在 `secrets.toml` 中填入以下内容：

```toml
# 1. 访问密码 (自定义，用于登录网页)
APP_PASSWORD = "admin"

# 2. 火山引擎 (DeepSeek) 配置
# 获取地址: https://console.volcengine.com/ark/region:ark+cn-beijing/endpoint
ARK_API_KEY = "你的火山引擎API_Key"
ARK_MODEL_ENDPOINT = "ep-202xxxxxxxx-xxxxx"  # 你的推理接入点ID

# 3. Tushare Pro 数据配置
# 获取地址: https://tushare.pro/user/token
TUSHARE_TOKEN = "你的Tushare_Token"
```

### 4. 运行应用
在终端输入以下命令启动：
```bash
streamlit run app.py
```
浏览器将自动打开 `http://localhost:8501`，输入你在配置文件中设置的密码即可进入。

---

## ☁️ 部署到 Streamlit Cloud (推荐)

本项目已针对 **Streamlit Community Cloud** 进行了优化，可一键免费部署。

1.  Fork 本仓库到你的 GitHub。
2.  访问 [Streamlit Cloud](https://share.streamlit.io/) 并连接你的 GitHub 账号。
3.  选择本项目 (`stock_test`) 进行部署。
4.  **关键步骤**：在部署界面的 "Advanced Settings" -> "Secrets" 中，填入上述 `secrets.toml` 中的内容。
5.  点击 **Deploy**，等待几分钟即可上线！

---

## 🛠️ 技术栈

*   **Frontend**: [Streamlit](https://streamlit.io/) (极速构建数据应用)
*   **Data Source**: [Tushare Pro](https://tushare.pro/) (专业的 Python 财经数据接口)
*   **LLM Model**: DeepSeek V3 (通过 [火山引擎/Volcengine](https://www.volcengine.com/) 调用)
*   **Data Processing**: Pandas, NumPy

---

## ⚠️ 免责声明

本项目生成的分析报告完全由人工智能基于历史数据推演生成，**不构成任何投资建议**。
*   股市有风险，投资需谨慎。
*   请勿完全依赖 AI 判断进行实盘操作。
*   开发者不对因使用本工具产生的任何资金损失负责。

---

## 📝 License

MIT License. 欢迎 Fork 和 Star！🌟
