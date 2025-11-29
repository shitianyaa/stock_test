import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 引入原有逻辑
from data_utils import (
    get_tushare_pro,
    validate_stock_code, 
    get_stock_name_by_code, 
    search_stocks, 
    get_clean_market_data, 
    get_clean_fundamental_data, 
    get_market_environment_data
)
from core_logic import call_deepseek_api, generate_analysis_prompt

# ===================== 1. 页面基础配置 =====================
st.set_page_config(
    page_title="DeepSeek 智能投研",
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===================== 2. 密码验证模块 (保持不变) =====================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("""
    <style>
        .stTextInput input { text-align: center; font-size: 1.2rem; }
        .login-container { max-width: 400px; margin: 100px auto; text-align: center; }
        .lock-icon { font-size: 5rem; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='text-align:center; margin-top:50px;'>", unsafe_allow_html=True)
        st.markdown("<div class='lock-icon'>🔒</div>", unsafe_allow_html=True)
        st.markdown("<h2>系统已锁定</h2>", unsafe_allow_html=True)
        
        password_input = st.text_input("Password", type="password", label_visibility="collapsed")
        
        if password_input:
            correct_password = st.secrets.get("APP_PASSWORD", "")
            if password_input == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# ===================== 3. 主程序逻辑 =====================

def run_app():
    # === CSS 深度美化 (优化间距与排版) ===
    st.markdown("""
    <style>
        /* 全局背景与字体 */
        .stApp {
            background-color: #f8f9fa; /* 极淡的灰背景，护眼 */
        }
        
        /* 侧边栏 */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
        }
        [data-testid="stSidebar"] * {
            color: #333333 !important;
        }

        /* 顶部 Header */
        .main-header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); /* 清爽蓝渐变 */
            padding: 2.5rem 2rem;
            border-radius: 16px;
            color: white;
            margin-bottom: 2.5rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        }
        .main-header h1 {
            color: white !important;
            font-size: 2.2rem;
            font-weight: 800;
        }
        
        /* 通用卡片样式 */
        .data-card {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            border: 1px solid #f0f0f0;
            height: 100%; /* 撑满高度 */
            min-height: 160px; /* 最小高度，防止太挤 */
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: transform 0.2s;
        }
        .data-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        }

        /* 卡片内部排版 */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .card-title {
            color: #555;
            font-size: 1rem;
            font-weight: 700;
        }
        .card-badge {
            font-size: 0.75rem;
            background: #f0f2f5;
            color: #666;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .card-value {
            color: #2c3e50;
            font-size: 2rem;
            font-weight: 800;
            margin: 0.5rem 0;
            line-height: 1.2;
        }
        .card-sub {
            font-size: 0.9rem;
            color: #888;
        }
        .explain-text {
            font-size: 0.8rem;
            color: #999;
            margin-top: 2px;
        }

        /* 指标颜色 */
        .up-text { color: #d93025; font-weight: bold; }
        .down-text { color: #1e8e3e; font-weight: bold; }

        /* 技术指标小卡片 */
        .tech-card {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #ddd;
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        }
        .tech-title { font-weight: bold; color: #333; font-size: 0.95rem; }
        .tech-cn { font-size: 0.8rem; color: #888; margin-left: 5px; }
        .tech-val { float: right; font-weight: bold; color: #444; }

        /* AI 报告框 */
        .ai-box {
            background: #ffffff;
            border-radius: 20px;
            padding: 3rem;
            border: 1px solid #eef0f5;
            box-shadow: 0 10px 40px rgba(0,0,0,0.06);
            margin-top: 3rem;
            position: relative;
        }
        .ai-box::before {
            content: "";
            position: absolute;
            top: 0; left: 0; width: 8px; height: 100%;
            background: linear-gradient(180deg, #4facfe 0%, #00f2fe 100%);
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
        }

        /* 按钮 */
        div.stButton > button {
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            color: white !important;
            border: none;
            padding: 0.7rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            font-size: 1rem;
            box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

    # ===================== 辅助函数 =====================

    def render_data_card(title_en, title_cn, value, sub_info=None, trend=None):
        """渲染带中文标注的宽敞卡片"""
        trend_html = ""
        if trend == "up":
            trend_html = f"<span class='up-text'>▲ {sub_info}</span>"
        elif trend == "down":
            trend_html = f"<span class='down-text'>▼ {sub_info}</span>"
        elif sub_info:
            trend_html = f"<span style='color:#666'>{sub_info}</span>"
            
        st.markdown(f"""
        <div class="data-card">
            <div class="card-header">
                <span class="card-title">{title_en}</span>
                <span class="card-badge">{title_cn}</span>
            </div>
            <div class="card-value">{value}</div>
            <div class="card-sub">{trend_html}</div>
        </div>
        """, unsafe_allow_html=True)

    def render_tech_row(label_en, label_cn, value, border_color="#ddd"):
        """渲染技术指标行"""
        st.markdown(f"""
        <div class="tech-card" style="border-left-color: {border_color};">
            <span class="tech-title">{label_en}</span>
            <span class="tech-cn">{label_cn}</span>
            <span class="tech-val">{value}</span>
        </div>
        """, unsafe_allow_html=True)

    def show_landing_page():
        st.markdown("""
        <div class="main-header" style="text-align: center;">
            <h1>📊 DeepSeek 智能投研系统</h1>
            <p style="opacity: 0.9; margin-top: 10px;">整合 Tushare 金融大数据 × DeepSeek V3 深度推理模型</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c2:
            st.markdown("""
            <div style="text-align:center; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
                <h2 style="color:#333;">🚀 开始您的分析</h2>
                <p style="color:#666;">请点击左上角 <b>></b> 展开侧边栏<br>输入股票代码（如 600519）即可生成报告</p>
            </div>
            """, unsafe_allow_html=True)

    # ===================== 业务逻辑 =====================

    if not get_tushare_pro():
        st.error("🚨 系统配置错误: 未找到 Tushare Token")
        st.stop()

    if 'target_code' not in st.session_state: st.session_state.target_code = ""
    if 'stock_name' not in st.session_state: st.session_state.stock_name = ""

    # --- 侧边栏 ---
    with st.sidebar:
        st.markdown("### 🔍 股票检索")
        search_mode = st.radio("查询模式", ["输入代码", "名称搜索"], horizontal=True)
        
        stock_code = ""
        stock_name = ""
        
        if search_mode == "输入代码":
            code_input = st.text_input("代码", value=st.session_state.target_code, placeholder="如: 600519")
            if code_input:
                is_valid, result = validate_stock_code(code_input)
                if is_valid:
                    stock_code = result
                    st.session_state.target_code = code_input
                    if st.session_state.stock_name == "":
                        stock_name = get_stock_name_by_code(stock_code)
                        st.session_state.stock_name = stock_name
                    else: stock_name = st.session_state.stock_name
                    st.success(f"已锁定: {stock_name}")
                else: st.error(result)
        else:
            keyword = st.text_input("名称", placeholder="如: 腾讯控股")
            if keyword:
                res = search_stocks(keyword)
                if res:
                    opts = {f"{r['名称']} ({r['代码']})": r['代码'] for r in res}
                    sel = st.selectbox("结果", list(opts.keys()))
                    if sel:
                        stock_code = opts[sel]
                        stock_name = sel.split(' (')[0]
                        st.session_state.target_code = stock_code
                        st.session_state.stock_name = stock_name
        
        st.markdown("---")
        predict_cycle = st.selectbox("周期", ["次日波动", "本周趋势", "月度展望"])
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 生成投研报告", type="primary")

    # --- 主视图 ---
    if not analyze_btn or not stock_code:
        show_landing_page()
    else:
        # 1. 顶部 Header
        st.markdown(f"""
        <div class="main-header">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h1 style="margin:0;">{stock_name}</h1>
                    <p style="margin:5px 0 0 0; opacity:0.8;">股票代码: {stock_code}</p>
                </div>
                <div style="text-align:right;">
                    <h2 style="margin:0;">DeepSeek 深度分析</h2>
                    <p style="margin:5px 0 0 0; opacity:0.8;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 数据加载
        with st.status("🔄 正在构建多因子分析模型...", expanded=True) as status:
            daily_data = get_clean_market_data(stock_code)
            if "错误" in daily_data:
                status.update(label="❌ 失败", state="error")
                st.error(daily_data["错误"])
                return
            fund_data = get_clean_fundamental_data(stock_code, daily_data)
            mkt_data = get_market_environment_data(stock_code)
            status.update(label="✅ 数据获取完成", state="complete")
            time.sleep(0.5)

        # 2. 核心指标区 (增加间距 gap="large")
        st.markdown("### 📈 核心概览")
        c1, c2, c3, c4 = st.columns(4, gap="large") # <--- 关键修改：增加列间距
        
        pchg = daily_data.get('涨跌幅', '0%')
        trend = "neutral"
        if '-' in pchg: trend = "down"
        elif pchg != '0.00%': trend = "up"

        with c1: render_data_card("Close", "最新收盘", daily_data.get('收盘价'), pchg, trend)
        with c2: render_data_card("Volume", "成交量", daily_data.get('成交量'), f"换手率: {daily_data.get('换手率')}")
        with c3: render_data_card("PE (TTM)", "滚动市盈率", fund_data.get('PE(TTM)'), f"PB (市净率): {fund_data.get('PB')}")
        with c4: render_data_card("Volatility", "年化波动率", daily_data.get('波动率'), "20日标准差")

        st.markdown("<br><br>", unsafe_allow_html=True) # 增加垂直间距

        # 3. 详细指标面板
        col_tech, col_market = st.columns([2, 1], gap="large")
        
        with col_tech:
            st.markdown("### 🛠 技术指标监控")
            st.markdown("<div style='color:#666; font-size:0.9rem; margin-bottom:15px;'>结合均线趋势与震荡指标的综合技术形态分析</div>", unsafe_allow_html=True)
            
            # 使用3列布局，让卡片不那么挤
            t1, t2, t3 = st.columns(3, gap="medium")
            with t1:
                render_tech_row("MA5", "5日短期均线", daily_data.get('5日均线'), "#4facfe")
                render_tech_row("MA10", "10日均线", daily_data.get('10日均线'), "#4facfe")
                render_tech_row("MA20", "20日生命线", daily_data.get('20日均线'), "#00f2fe")
            with t2:
                render_tech_row("MACD", "平滑异同移动平均", daily_data.get('MACD'), "#a18cd1")
                render_tech_row("RSI", "相对强弱指标(14)", daily_data.get('RSI'), "#fbc2eb")
                render_tech_row("Trend", "短期趋势", "多头" if trend=="up" else "空头", "#ff9a9e")
            with t3:
                render_tech_row("BOLL UP", "布林带上轨(压力)", daily_data.get('布林上轨'), "#fa709a")
                render_tech_row("BOLL MID", "布林带中轨", daily_data.get('布林中轨'), "#fee140")
                render_tech_row("BOLL LOW", "布林带下轨(支撑)", daily_data.get('布林下轨'), "#fa709a")

        with col_market:
            st.markdown("### 🌍 市场罗盘")
            st.markdown("<div style='color:#666; font-size:0.9rem; margin-bottom:15px;'>宏观环境与基本面扫描</div>", unsafe_allow_html=True)
            
            # 市场情绪大卡片
            sent = mkt_data.get('市场情绪')
            bg_color = "#f9f9f9"
            text_color = "#333"
            if sent == "乐观": 
                bg_color = "linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)"
                text_color = "#006400"
            elif sent == "悲观": 
                bg_color = "linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)"
                text_color = "#8b0000"
            
            st.markdown(f"""
            <div style="background:{bg_color}; padding:30px 20px; border-radius:16px; text-align:center; box-shadow:0 4px 15px rgba(0,0,0,0.05); color:{text_color};">
                <h2 style="margin:0; font-size:2rem;">{sent}</h2>
                <p style="margin:5px 0 0 0; opacity:0.8; font-weight:bold;">当前市场情绪</p>
                <div style="margin-top:20px; font-size:1.1rem; border-top:1px solid rgba(0,0,0,0.1); padding-top:10px;">
                    参考指数: <b>{mkt_data.get('市场指数涨跌幅')}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="margin-top:20px; padding:20px; background:white; border-radius:16px; border:1px solid #eee; box-shadow:0 2px 10px rgba(0,0,0,0.02);">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="color:#888;">🏢 所属行业</span>
                    <span style="font-weight:bold; color:#333;">{fund_data.get('所属行业')}</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#888;">💰 总市值</span>
                    <span style="font-weight:bold; color:#333;">{fund_data.get('总市值')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 4. AI 报告
        st.markdown(f"""
        <div class="ai-box">
            <div style="display:flex; align-items:center; gap:15px; margin-bottom:2rem; border-bottom:1px solid #eee; padding-bottom:1.5rem;">
                <span style="font-size: 2.5rem;">🤖</span>
                <div>
                    <h2 style="margin:0; color:#2c3e50;">DeepSeek 深度研报</h2>
                    <span style="font-size:1rem; color:#888;">基于 {predict_cycle} 的多因子量化推理模型 • 自动生成</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.spinner("🧠 DeepSeek 正在思考策略..."):
            prompt = generate_analysis_prompt(stock_code, stock_name, predict_cycle, daily_data, fund_data, mkt_data)
            res = call_deepseek_api(prompt)
        
        if res.startswith("❌"):
            st.error(res)
        else:
            st.markdown(res)
            st.markdown(f"""
            <div style="text-align:right; margin-top:30px; padding-top:20px; border-top:1px dashed #eee; color:#ccc; font-size:0.8rem;">
                生成 ID: {datetime.now().strftime('%Y%m%d%H%M%S')} | 数据来源: Tushare Pro | 模型: DeepSeek-V3
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ===================== 4. 程序入口 =====================
if __name__ == "__main__":
    if check_password():
        run_app()