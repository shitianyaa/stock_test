import streamlit as st
import pandas as pd
from datetime import datetime
import time

from data_utils import (
    get_tushare_pro,
    validate_stock_code, 
    get_stock_name_by_code, 
    search_stocks, 
    get_clean_market_data, 
    get_clean_fundamental_data, 
    get_market_environment_data
)
# 注意：generate_analysis_prompt 的参数变了，这里引用会自动更新
from core_logic import call_deepseek_api, generate_analysis_prompt

# ... (保持前面的 CSS 和 check_password 不变) ...
# 为了节省篇幅，这里省略 check_password 和 set_page_config 代码
# 请保留你原文件最上方的 check_password 函数和 st.set_page_config

# ===================== 1. 页面基础配置 =====================
st.set_page_config(
    page_title="DeepSeek 智能投研",
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ... (请保留原有的 check_password 函数 和 CSS 样式代码) ...
# ... (如果不确定，就把上一次给你的 app.py 的 CSS 和 check_password 复制到这里) ...

def check_password():
    if st.session_state.get("password_correct", False):
        return True
    # ... (简写，请保持原有的密码逻辑) ...
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        password_input = st.text_input("Password", type="password")
        if password_input:
            if password_input == st.secrets.get("APP_PASSWORD", ""):
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("❌ 密码错误")
    return False

# ===================== 辅助函数 =====================
def render_data_card(title_en, title_cn, value, sub_info=None, trend=None):
    # ... (保持原有的卡片渲染函数不变) ...
    trend_html = ""
    if trend == "up": trend_html = f"<span style='color:#d93025'>▲ {sub_info}</span>"
    elif trend == "down": trend_html = f"<span style='color:#1e8e3e'>▼ {sub_info}</span>"
    elif sub_info: trend_html = f"<span style='color:#999; font-size:0.9rem;'>{sub_info}</span>"
    st.markdown(f"""
    <div style="background:white; padding:1.5rem; border-radius:12px; border:1px solid #f0f0f0; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#888; font-size:0.85rem; font-weight:600; text-transform:uppercase;">{title_en}</span>
            <span style="font-size:0.75rem; background:#f5f5f5; padding:2px 6px; border-radius:4px; color:#666;">{title_cn}</span>
        </div>
        <div style="color:#2c3e50; font-size:1.8rem; font-weight:700; margin:5px 0;">{value}</div>
        <div>{trend_html}</div>
    </div>
    """, unsafe_allow_html=True)

def show_landing_page():
    # ... (保持原有的 Landing Page 代码不变) ...
    st.title("DeepSeek 智能投研")
    st.info("👈 请在左侧侧边栏输入股票代码开始分析")

# ===================== 主程序逻辑 =====================

def run_app():
    # 初始化 Session
    if 'history_data' not in st.session_state: st.session_state.history_data = []
    if 'target_code' not in st.session_state: st.session_state.target_code = ""
    if 'stock_name' not in st.session_state: st.session_state.stock_name = ""

    # 注入 CSS (请把上个回答的完整 CSS 贴在这里，为了运行不报错我简写一点)
    st.markdown("""<style>.stApp {background-color: #f8f9fa;}</style>""", unsafe_allow_html=True)

    if not get_tushare_pro():
        st.error("🚨 配置错误: 未找到 Tushare Token")
        st.stop()

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
                    with st.spinner("验证中..."):
                        fetched = get_stock_name_by_code(stock_code)
                        st.session_state.stock_name = fetched
                        stock_name = fetched
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
        st.markdown("### ⚙️ 分析设置")
        
        # === 新增：AI 性格选择 ===
        analysis_style = st.select_slider(
            "AI 分析风格",
            options=["稳健理智", "短线博弈", "激进犀利"],
            value="稳健理智",
            help="稳健：适合价值投资；激进：适合游资/超短线，观点更鲜明。"
        )
        
        predict_cycle = st.selectbox("预测周期", ["次日波动", "本周趋势", "月度展望"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 生成投研报告", type="primary")

    # --- 主视图 ---
    if not analyze_btn or not stock_code:
        if not st.session_state.history_data:
            show_landing_page()
    else:
        # 1. 头部
        st.markdown(f"## {stock_name} <span style='color:#888;font-size:1.2rem'>{stock_code}</span>", unsafe_allow_html=True)

        # 数据加载
        with st.status("🔄 正在构建多因子模型...", expanded=True) as status:
            daily_data = get_clean_market_data(stock_code)
            if "错误" in daily_data:
                status.update(label="❌ 失败", state="error")
                st.error(daily_data["错误"])
                return
            fund_data = get_clean_fundamental_data(stock_code, daily_data)
            mkt_data = get_market_environment_data(stock_code)
            status.update(label="✅ 完成", state="complete")
            time.sleep(0.5)

        # 记录历史
        new_record = {
            "时间": datetime.now().strftime('%m-%d %H:%M'),
            "代码": stock_code, "名称": stock_name,
            "价格": daily_data.get('收盘价'), "涨跌": daily_data.get('涨跌幅'),
            "风格": analysis_style  # 记录风格
        }
        if not st.session_state.history_data or st.session_state.history_data[0]["代码"] != stock_code:
            st.session_state.history_data.insert(0, new_record)

        # 2. 核心指标卡片 (保持原样，这里为了代码简洁省略了 render 调用，请保留你原来的代码)
        c1, c2, c3, c4 = st.columns(4, gap="large")
        # ... (请保留你原来的 render_data_card 调用代码) ...
        # 示例：
        pchg = daily_data.get('涨跌幅', '0%')
        trend = "up" if '-' not in pchg and pchg != '0.00%' else ("down" if '-' in pchg else "neutral")
        with c1: render_data_card("Close", "最新收盘", daily_data.get('收盘价'), pchg, trend)
        with c2: render_data_card("Volume", "成交量", daily_data.get('成交量'), f"换手: {daily_data.get('换手率')}")
        with c3: render_data_card("PE (TTM)", "滚动市盈率", fund_data.get('PE(TTM)'), f"PB: {fund_data.get('PB')}")
        with c4: render_data_card("Volatility", "年化波动率", daily_data.get('波动率'), "20日标准差")

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. 详细指标面板 (保持原样，请保留你原来的代码)
        # ...

        # 4. AI 报告
        # 根据风格显示不同的 Emoji
        icon_map = {"稳健理智": "🧐", "短线博弈": "⚡", "激进犀利": "🔥"}
        color_map = {"稳健理智": "#1e3c72", "短线博弈": "#f39c12", "激进犀利": "#c0392b"}
        
        current_icon = icon_map.get(analysis_style, "🤖")
        current_color = color_map.get(analysis_style, "#333")

        st.markdown(f"""
        <div style="background:#fff; padding:2rem; border-radius:15px; border-left:5px solid {current_color}; box-shadow:0 4px 20px rgba(0,0,0,0.05); margin-top:2rem;">
            <div style="display:flex; align-items:center; gap:15px; margin-bottom:1.5rem; border-bottom:1px solid #eee; padding-bottom:1rem;">
                <span style="font-size: 2.2rem;">{current_icon}</span>
                <div>
                    <h3 style="margin:0; color:{current_color};">DeepSeek {analysis_style}研报</h3>
                    <span style="font-size:0.9rem; color:#888;">AI 扮演角色：{analysis_style}操盘手</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.spinner(f"🧠 {analysis_style}模式：DeepSeek 正在犀利分析中..."):
            # === 关键修改：传入 style 参数 ===
            prompt = generate_analysis_prompt(
                stock_code, stock_name, predict_cycle, 
                daily_data, fund_data, mkt_data, 
                style=analysis_style # <--- 传入风格
            )
            res = call_deepseek_api(prompt)
        
        if res.startswith("❌"): st.error(res)
        else: st.markdown(res)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # 历史记录区 (保持原样)
    if st.session_state.history_data:
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        with st.expander("📜 历史分析记录", expanded=True):
            st.dataframe(pd.DataFrame(st.session_state.history_data), use_container_width=True)

if __name__ == "__main__":
    if check_password():
        run_app()
