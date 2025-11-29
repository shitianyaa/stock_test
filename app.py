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

# ===================== 页面配置与 CSS 美化 =====================
st.set_page_config(
    page_title="DeepSeek 智能投研系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS
st.markdown("""
<style>
    /* 全局字体与背景 */
    .stApp {
        background-color: #f5f7f9;
    }
    
    /* 侧边栏美化 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }

    /* 标题样式 */
    .main-header {
        background: linear-gradient(120deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
    }

    /* 数据卡片样式 */
    .data-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        height: 100%;
        transition: transform 0.2s;
    }
    .data-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .card-title {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .card-value {
        color: #1a1a1a;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .card-sub {
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .trend-up { color: #d93025; }
    .trend-down { color: #1e8e3e; }
    .trend-neutral { color: #666; }

    /* AI 分析报告容器 */
    .ai-box {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        border-left: 5px solid #764ba2;
        box-shadow: 0 4px 20px rgba(118, 75, 162, 0.1);
        margin-top: 2rem;
    }
    .ai-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1.5rem;
        color: #2c3e50;
    }
    
    /* 按钮美化 */
    .stButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        opacity: 0.9;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# ===================== 辅助显示函数 =====================

def render_metric_card(title, value, sub_value=None, trend=None):
    """渲染一个美化的指标卡片"""
    trend_class = "trend-neutral"
    trend_icon = ""
    
    if trend == "up":
        trend_class = "trend-up"
        trend_icon = "▲"
    elif trend == "down":
        trend_class = "trend-down"
        trend_icon = "▼"
        
    sub_html = ""
    if sub_value:
        sub_html = f'<div class="card-sub {trend_class}">{trend_icon} {sub_value}</div>'
        
    st.markdown(f"""
    <div class="data-card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

# ===================== 主逻辑 =====================

def main():
    # 检查 Token
    if not get_tushare_pro():
        st.error("🚨 系统配置错误")
        st.warning("请在 Secrets 中配置 TUSHARE_TOKEN")
        st.stop()

    # Session State
    if 'target_code' not in st.session_state: st.session_state.target_code = ""
    if 'stock_name' not in st.session_state: st.session_state.stock_name = ""

    # --- 侧边栏 ---
    with st.sidebar:
        st.markdown("### 🔍 股票检索")
        
        tab1, tab2 = st.tabs(["代码", "搜索"])
        
        stock_code = ""
        stock_name = ""
        
        with tab1:
            code_input = st.text_input("输入代码", 
                                     value=st.session_state.target_code,
                                     placeholder="如 600519 或 00700",
                                     help="支持 A股(6位) 和 港股(5位)")
            if code_input:
                is_valid, result = validate_stock_code(code_input)
                if is_valid:
                    stock_code = result
                    st.session_state.target_code = code_input
                    with st.spinner("验证中..."):
                        stock_name = get_stock_name_by_code(stock_code)
                        st.session_state.stock_name = stock_name
                    st.success(f"已锁定: {stock_name}")
                else:
                    st.error(result)

        with tab2:
            keyword = st.text_input("输入名称", placeholder="如：腾讯控股")
            if keyword:
                res = search_stocks(keyword)
                if res:
                    opts = {f"{r['名称']} ({r['代码']})": r['代码'] for r in res}
                    sel = st.selectbox("选择结果", list(opts.keys()))
                    if sel:
                        stock_code = opts[sel]
                        stock_name = sel.split(' (')[0]
                        st.session_state.target_code = stock_code
                        st.session_state.stock_name = stock_name
                else:
                    st.warning("未找到匹配项")

        st.markdown("---")
        st.markdown("### ⚙️ 分析参数")
        predict_cycle = st.selectbox("预测周期", ["次日波动", "本周趋势", "月度展望"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 生成投研报告", type="primary", use_container_width=True, disabled=not stock_code)
        
        st.markdown("""
        <div style='margin-top: 2rem; font-size: 0.8rem; color: #888; text-align: center;'>
            DeepSeek Intelligence<br>Tushare Pro Data
        </div>
        """, unsafe_allow_html=True)

    # --- 主区域 ---
    
    # 顶部 Hero 区域
    st.markdown(f"""
    <div class="main-header">
        <h1>DeepSeek 智能投研系统</h1>
        <p>实时连接 Tushare 金融大数据，由 DeepSeek V3 提供深度量化分析</p>
    </div>
    """, unsafe_allow_html=True)

    if analyze_btn and stock_code:
        # 数据加载状态
        with st.status("🔄 正在构建分析模型...", expanded=True) as status:
            st.write("📡 连接交易所数据源...")
            daily_data = get_clean_market_data(stock_code)
            
            if "错误" in daily_data:
                status.update(label="❌ 数据拉取失败", state="error")
                st.error(daily_data["错误"])
                return

            st.write("📊 计算基本面估值模型...")
            fund_data = get_clean_fundamental_data(stock_code, daily_data)
            
            st.write("🌍 扫描宏观市场情绪...")
            mkt_data = get_market_environment_data(stock_code)
            
            status.update(label="✅ 数据建模完成", state="complete")
            time.sleep(0.5) # 稍微停顿提升体验

        # 标题栏
        st.markdown(f"## 🏢 {stock_name} <span style='color:#666; font-size:1.2rem;'>{stock_code}</span>", unsafe_allow_html=True)
        st.markdown("---")

        # === 第一行：核心行情 ===
        st.subheader("📈 核心行情")
        row1_1, row1_2, row1_3, row1_4 = st.columns(4)
        
        # 处理涨跌颜色
        pchg = daily_data.get('涨跌幅', '0%')
        trend = "neutral"
        try:
            val = float(pchg.replace('%', ''))
            if val > 0: trend = "up"
            elif val < 0: trend = "down"
        except: pass

        with row1_1:
            render_metric_card("最新收盘", daily_data.get('收盘价'), pchg, trend)
        with row1_2:
            render_metric_card("成交量", daily_data.get('成交量'), f"换手: {daily_data.get('换手率')}")
        with row1_3:
            render_metric_card("PE (TTM)", fund_data.get('PE(TTM)'), "估值水平")
        with row1_4:
            render_metric_card("波动率", daily_data.get('波动率'), "20日标准差")

        # === 第二行：技术与环境 ===
        st.markdown("<br>", unsafe_allow_html=True)
        row2_1, row2_2 = st.columns([2, 1])
        
        with row2_1:
            st.subheader("🛠 技术指标监控")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.info(f"**MA5**: {daily_data.get('5日均线')}")
                st.info(f"**MA20**: {daily_data.get('20日均线')}")
            with col_t2:
                st.success(f"**MACD**: {daily_data.get('MACD')}")
                st.success(f"**RSI**: {daily_data.get('RSI')}")
            with col_t3:
                st.warning(f"**布林上**: {daily_data.get('布林上轨')}")
                st.warning(f"**布林下**: {daily_data.get('布林下轨')}")

        with row2_2:
            st.subheader("🌍 市场罗盘")
            # 市场情绪卡片
            sentiment = mkt_data.get('市场情绪')
            bg_color = "#f0f2f6"
            if sentiment == "乐观": bg_color = "#e6fffa"
            elif sentiment == "悲观": bg_color = "#fff5f5"
            
            st.markdown(f"""
            <div style="background:{bg_color}; padding:15px; border-radius:10px; text-align:center;">
                <h3 style="margin:0; color:#333;">{sentiment}</h3>
                <p style="margin:5px 0 0 0; color:#666; font-size:0.8rem;">市场情绪</p>
                <div style="margin-top:10px; font-weight:bold; color:#444;">
                    指数: {mkt_data.get('市场指数涨跌幅')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="margin-top:10px; padding:10px; border:1px dashed #ddd; border-radius:8px; font-size:0.85rem; color:#555;">
                <div>🏢 行业: <b>{fund_data.get('所属行业')}</b></div>
                <div>💰 市值: <b>{fund_data.get('总市值')}</b></div>
            </div>
            """, unsafe_allow_html=True)

        # === AI 分析报告区 ===
        st.markdown(f"""
        <div class="ai-box">
            <div class="ai-header">
                <span style="font-size: 2rem;">🤖</span>
                <div>
                    <h2 style="margin:0;">DeepSeek 深度研报</h2>
                    <span style="font-size:0.9rem; color:#666;">基于 {predict_cycle} 视角的量化推理</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.spinner("🧠 正在进行多维度逻辑推理..."):
            prompt = generate_analysis_prompt(
                stock_code, stock_name, predict_cycle,
                daily_data, fund_data, mkt_data
            )
            analysis_result = call_deepseek_api(prompt)
        
        if analysis_result.startswith("❌"):
            st.error(analysis_result)
        else:
            st.markdown(analysis_result)
            st.markdown(f"""
            <div style="text-align:right; margin-top:20px; color:#999; font-size:0.8rem;">
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 仅供参考，不构成投资建议
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # 初始欢迎页
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("👈 请在左侧侧边栏输入股票代码或名称，开始您的 AI 投研之旅。")

if __name__ == "__main__":
    main()
