import streamlit as st
import json
from datetime import datetime
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

def main():
    st.set_page_config(page_title="DeepSeek 股票分析", page_icon="📈", layout="wide")
    
    # === 检查配置 ===
    if not get_tushare_pro():
        st.error("🚨 未配置 Tushare Token，请在 Secrets 中配置 `TUSHARE_TOKEN`。")
        st.stop()
        
    st.title("📈 DeepSeek + Tushare 智能分析")
    st.info("💡 提示：A股数据通常免费；港股数据(.HK)需要 Tushare 2000+ 积分权限。")
    
    # Session State
    if 'target_code' not in st.session_state: st.session_state.target_code = ""
    if 'stock_name' not in st.session_state: st.session_state.stock_name = ""

    # === 侧边栏 ===
    st.sidebar.header("🔍 查询")
    search_mode = st.sidebar.radio("模式", ["输入代码", "名称搜索"])
    
    stock_code, stock_name = "", ""
    
    if search_mode == "输入代码":
        code_input = st.sidebar.text_input("代码 (支持A股/港股)", value=st.session_state.target_code, placeholder="例: 600519 或 00700")
        if code_input:
            is_valid, result = validate_stock_code(code_input)
            if is_valid:
                stock_code = result
                st.session_state.target_code = code_input
                with st.spinner("验证中..."):
                    stock_name = get_stock_name_by_code(stock_code)
                    st.session_state.stock_name = stock_name
                st.sidebar.success(f"✅ {stock_name} ({stock_code})")
            else:
                st.sidebar.error(result)
    else:
        keyword = st.sidebar.text_input("输入名称")
        if keyword:
            res = search_stocks(keyword)
            if res:
                opts = {f"{r['名称']} ({r['代码']}) - {r['类型']}": r['代码'] for r in res}
                sel = st.sidebar.selectbox("选择股票", list(opts.keys()))
                if sel:
                    stock_code = opts[sel]
                    stock_name = sel.split(' (')[0]
                    st.session_state.target_code = stock_code
                    st.session_state.stock_name = stock_name
            else:
                st.sidebar.warning("未找到结果")

    predict_cycle = st.sidebar.selectbox("周期", ["次日", "本周", "月度"])
    start_btn = st.sidebar.button("🚀 开始分析", type="primary", disabled=not stock_code)

    # === 主界面 ===
    if start_btn and stock_code:
        st.divider()
        st.header(f"{stock_name} ({stock_code})")
        
        with st.status("正在拉取数据...", expanded=True) as status:
            st.write("📥 获取行情...")
            daily_data = get_clean_market_data(stock_code)
            
            if "错误" in daily_data:
                status.update(label="❌ 数据获取失败", state="error")
                st.error(daily_data["错误"])
                if ".HK" in stock_code:
                    st.warning("⚠️ 提示：港股数据失败通常是因为 Tushare 积分不足 2000。")
                return

            st.write("📥 获取基本面...")
            fund_data = get_clean_fundamental_data(stock_code, daily_data)
            
            st.write("📥 获取市场环境...")
            mkt_data = get_market_environment_data(stock_code)
            
            status.update(label="✅ 数据就绪", state="complete")
        
        # 1. 使用 Expander 查看原始数据 (调试用)
        with st.expander("📊 点击查看所有详细数据 JSON"):
            st.json({
                "技术面": daily_data,
                "基本面": fund_data,
                "市场面": mkt_data
            })

        # 2. 核心指标面板 (全量展示)
        st.subheader("📊 详细数据面板")
        
        # 第一行：价格与成交
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("收盘价", daily_data.get('收盘价'), daily_data.get('涨跌幅'))
        with c2:
            st.metric("成交量", daily_data.get('成交量'))
            # 兼容港股可能没有换手率
            turnover = daily_data.get('换手率', 'N/A')
            st.caption(f"换手率: {turnover}")
        with c3:
            st.metric("波动率", daily_data.get('波动率'))
        with c4:
            st.metric("PE(TTM)", fund_data.get('PE(TTM)'))
            st.caption(f"PB: {fund_data.get('PB')}")

        st.divider()

        # 第二行：技术指标
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 📈 趋势均线")
            st.write(f"**MA5**: {daily_data.get('5日均线')}")
            st.write(f"**MA10**: {daily_data.get('10日均线')}")
            st.write(f"**MA20**: {daily_data.get('20日均线')}")
            
        with c2:
            st.markdown("#### 📊 震荡指标")
            st.write(f"**MACD**: {daily_data.get('MACD')}")
            st.write(f"**RSI (14)**: {daily_data.get('RSI')}")
            
        with c3:
            st.markdown("#### 🛡️ 布林带通道")
            st.write(f"**上轨**: {daily_data.get('布林上轨')}")
            st.write(f"**中轨**: {daily_data.get('布林中轨')}")
            st.write(f"**下轨**: {daily_data.get('布林下轨')}")

        st.divider()

        # 第三行：基本面与环境
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏢 公司基本面")
            st.write(f"**所属行业**: {fund_data.get('所属行业')}")
            st.write(f"**总市值**: {fund_data.get('总市值')}")
            st.write(f"**上市地**: {'港股' if '.HK' in stock_code else 'A股'}")
        
        with c2:
            st.markdown("#### 🌍 市场环境")
            st.write(f"**参考指数涨跌**: {mkt_data.get('市场指数涨跌幅')}")
            st.write(f"**市场情绪**: {mkt_data.get('市场情绪')}")

        # AI 分析
        st.subheader("🤖 DeepSeek 分析")
        with st.spinner("AI 正在思考策略..."):
            prompt = generate_analysis_prompt(stock_code, stock_name, predict_cycle, daily_data, fund_data, mkt_data)
            res = call_deepseek_api(prompt)
        
        if res.startswith("❌"): st.error(res)
        else: st.markdown(res)

if __name__ == "__main__":
    main()
