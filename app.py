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

# ===================== 页面配置 =====================
st.set_page_config(
    page_title="DeepSeek 智能投研",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== CSS 深度美化 =====================
st.markdown("""
<style>
    /* 全局重置 */
    .stApp {
        background-color: #ffffff;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #eee;
    }
    /* 强制侧边栏文字深色 */
    [data-testid="stSidebar"] * {
        color: #333333 !important;
    }

    /* --- 首页 (Landing Page) 特有样式 --- */
    .landing-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 15px;
        color: white;
        text-align: left;
        margin-bottom: 3rem;
        box-shadow: 0 10px 30px rgba(118, 75, 162, 0.2);
    }
    .landing-header h1 {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: white !important;
    }
    .landing-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    .feature-container {
        text-align: center;
        padding: 1rem;
        transition: all 0.3s ease;
    }
    .feature-container:hover {
        transform: translateY(-5px);
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
    }
    .feature-title {
        font-weight: 700;
        font-size: 1.1rem;
        color: #333;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        color: #666;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* --- 分析页 (Dashboard) 样式 --- */
    .dashboard-header {
        background: white;
        padding: 1.5rem 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 2rem;
    }
    
    /* 指标卡片 */
    .data-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        height: 100%;
        text-align: center;
    }
    .card-title { color: #888; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.5rem; }
    .card-value { color: #2c3e50; font-size: 1.8rem; font-weight: 800; }
    
    /* AI 报告框 */
    .ai-box {
        background: #fdfdfd;
        border-radius: 16px;
        padding: 2.5rem;
        border: 1px solid #eef0f5;
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        margin-top: 2rem;
        position: relative;
        overflow: hidden;
    }
    .ai-box::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 6px; height: 100%;
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }

    /* 按钮样式 */
    div.stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        box-shadow: 0 4px 10px rgba(118, 75, 162, 0.3);
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 15px rgba(118, 75, 162, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ===================== 辅助函数 =====================

def render_metric_card(title, value, sub_value=None, trend=None):
    """渲染指标卡片"""
    trend_color = "#888"
    trend_icon = ""
    if trend == "up":
        trend_color = "#d93025"
        trend_icon = "▲"
    elif trend == "down":
        trend_color = "#1e8e3e"
        trend_icon = "▼"
        
    sub_html = ""
    if sub_value:
        sub_html = f'<div style="color:{trend_color}; font-size:0.85rem; margin-top:8px; font-weight:500;">{trend_icon} {sub_value}</div>'
        
    st.markdown(f"""
    <div class="data-card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def show_landing_page():
    """显示首页（未开始分析状态）"""
    # 1. 顶部大横幅
    st.markdown("""
    <div class="landing-header">
        <h1>📊 DeepSeek + Tushare 智能股票分析</h1>
        <p>基于 Tushare 专业数据源与 AI 大模型的实时智能分析系统</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. 欢迎语
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <h2 style="font-size: 2rem; color: #2c3e50; margin-bottom: 1rem;">🚀 欢迎使用 DeepSeek 智能股票分析系统</h2>
        <p style="color: #666; font-size: 1.1rem;">请在左侧侧边栏选择股票并开始 AI 深度分析，系统将为您提供专业的波动方向预测和投资建议。</p>
    </div>
    """, unsafe_allow_html=True)

    # 3. 特色功能区 (4列布局)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h3 style="color: #764ba2; font-weight: 700;">✨ 系统特色功能</h3>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("""
        <div class="feature-container">
            <span class="feature-icon">📊</span>
            <div class="feature-title">实时数据</div>
            <div class="feature-desc">Tushare 专业数据源<br>毫秒级行情接入</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="feature-container">
            <span class="feature-icon">🤖</span>
            <div class="feature-title">AI 分析</div>
            <div class="feature-desc">DeepSeek 大模型预测<br>深度逻辑推理</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="feature-container">
            <span class="feature-icon">📈</span>
            <div class="feature-title">技术指标</div>
            <div class="feature-desc">多维度技术分析<br>MACD / RSI / 均线</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown("""
        <div class="feature-container">
            <span class="feature-icon">🌍</span>
            <div class="feature-title">市场环境</div>
            <div class="feature-desc">全面市场情绪扫描<br>大盘资金流向</div>
        </div>
        """, unsafe_allow_html=True)

# ===================== 主逻辑 =====================

def main():
    # 检查 Token
    if not get_tushare_pro():
        st.error("🚨 系统配置错误: 未找到 Tushare Token")
        st.stop()

    # Session State
    if 'target_code' not in st.session_state: st.session_state.target_code = ""
    if 'stock_name' not in st.session_state: st.session_state.stock_name = ""

    # --- 侧边栏 ---
    with st.sidebar:
        st.markdown("### 🔍 股票检索")
        search_mode = st.radio("查询模式", ["输入代码", "名称搜索"], horizontal=True)
        
        stock_code = ""
        stock_name = ""
        
        if search_mode == "输入代码":
            code_input = st.text_input("代码", 
                                     value=st.session_state.target_code,
                                     placeholder="如: 600519 或 00700")
            if code_input:
                is_valid, result = validate_stock_code(code_input)
                if is_valid:
                    stock_code = result
                    st.session_state.target_code = code_input
                    if st.session_state.stock_name == "":
                        with st.spinner("验证中..."):
                            st.session_state.stock_name = get_stock_name_by_code(stock_code)
                    stock_name = st.session_state.stock_name
                    st.success(f"已锁定: {stock_name}")
                else:
                    st.error(result)
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
                else:
                    st.warning("未找到匹配股票")

        st.markdown("---")
        st.markdown("### ⚙️ 分析设置")
        predict_cycle = st.selectbox("周期", ["次日波动", "本周趋势", "月度展望"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 生成投研报告", type="primary", disabled=not stock_code)

    # --- 主区域逻辑判断 ---
    
    # 如果用户没有点击分析按钮，或者还没选股票 -> 显示首页 (Landing Page)
    if not analyze_btn or not stock_code:
        show_landing_page()
    
    # 如果用户点击了分析 -> 显示仪表盘 (Dashboard)
    else:
        # 1. 加载状态
        with st.status("🔄 正在构建分析模型...", expanded=True) as status:
            st.write("📡 接入交易所实时数据...")
            daily_data = get_clean_market_data(stock_code)
            if "错误" in daily_data:
                status.update(label="❌ 数据获取失败", state="error")
                st.error(daily_data["错误"])
                return

            st.write("📊 计算多因子估值模型...")
            fund_data = get_clean_fundamental_data(stock_code, daily_data)
            
            st.write("🌍 扫描宏观市场情绪...")
            mkt_data = get_market_environment_data(stock_code)
            
            status.update(label="✅ 数据建模完成", state="complete")
            time.sleep(0.5)

        # 2. 股票标题
        st.markdown(f"""
        <div class="dashboard-header">
            <h2 style="margin:0; color:#2c3e50;">{stock_name} <span style="font-size:1.2rem; color:#888; font-weight:400;">{stock_code}</span></h2>
        </div>
        """, unsafe_allow_html=True)

        # 3. 第一行：核心指标
        c1, c2, c3, c4 = st.columns(4)
        
        pchg = daily_data.get('涨跌幅', '0%')
        trend = "neutral"
        if '-' in pchg: trend = "down"
        elif pchg != '0.00%': trend = "up"

        with c1: render_metric_card("最新收盘", daily_data.get('收盘价'), pchg, trend)
        with c2: render_metric_card("成交量", daily_data.get('成交量'), f"换手: {daily_data.get('换手率')}")
        with c3: render_metric_card("PE (TTM)", fund_data.get('PE(TTM)'), f"PB: {fund_data.get('PB')}")
        with c4: render_metric_card("波动率", daily_data.get('波动率'), "20日标准差")

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. 第二行：技术与市场
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.markdown("#### 🛠 技术指标监控")
            t1, t2, t3 = st.columns(3)
            with t1:
                st.info(f"**MA5**: {daily_data.get('5日均线')}")
                st.info(f"**MA20**: {daily_data.get('20日均线')}")
            with t2:
                st.success(f"**MACD**: {daily_data.get('MACD')}")
                st.success(f"**RSI**: {daily_data.get('RSI')}")
            with t3:
                st.warning(f"**布林上**: {daily_data.get('布林上轨')}")
                st.warning(f"**布林下**: {daily_data.get('布林下轨')}")

        with col_right:
            st.markdown("#### 🌍 市场罗盘")
            sent = mkt_data.get('市场情绪')
            bg = "#f0f2f6"
            if sent == "乐观": bg = "#e6fffa"
            elif sent == "悲观": bg = "#fff5f5"
            
            st.markdown(f"""
            <div style="background:{bg}; padding:15px; border-radius:10px; text-align:center; border:1px solid #eee;">
                <h3 style="margin:0; color:#333;">{sent}</h3>
                <p style="margin:5px 0 0 0; color:#666; font-size:0.8rem;">市场情绪</p>
                <div style="margin-top:10px; color:#444; font-weight:bold;">指数: {mkt_data.get('市场指数涨跌幅')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="margin-top:10px; padding:10px; border:1px dashed #ccc; border-radius:8px; font-size:0.85rem; color:#555; background:white;">
                <div>🏢 行业: <b>{fund_data.get('所属行业')}</b></div>
                <div>💰 市值: <b>{fund_data.get('总市值')}</b></div>
            </div>
            """, unsafe_allow_html=True)

        # 5. AI 报告
        st.markdown(f"""
        <div class="ai-box">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:1.5rem; border-bottom:1px solid #eee; padding-bottom:1rem;">
                <span style="font-size: 2.2rem;">🤖</span>
                <div>
                    <h3 style="margin:0; color:#2c3e50;">DeepSeek 深度研报</h3>
                    <span style="font-size:0.9rem; color:#888;">AI 模型基于 {predict_cycle} 的多因子量化推理</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.spinner("🧠 AI 正在撰写分析报告..."):
            prompt = generate_analysis_prompt(
                stock_code, stock_name, predict_cycle,
                daily_data, fund_data, mkt_data
            )
            res = call_deepseek_api(prompt)
        
        if res.startswith("❌"):
            st.error(res)
        else:
            st.markdown(res)
            st.markdown(f"""
            <div style="text-align:right; margin-top:20px; color:#ccc; font-size:0.8rem;">
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据来源: Tushare Pro
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
