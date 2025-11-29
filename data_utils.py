import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import streamlit as st

# ===================== 基础工具 =====================

def get_tushare_pro():
    try:
        if hasattr(st, 'secrets') and 'TUSHARE_TOKEN' in st.secrets:
            token = st.secrets['TUSHARE_TOKEN']
        else:
            token = os.getenv("TUSHARE_TOKEN", "")
        
        if not token: return None
        ts.set_token(token)
        return ts.pro_api()
    except: return None

def validate_stock_code(code):
    clean = re.sub(r'[^\d]', '', str(code))
    if len(clean) == 5: return True, clean + ".HK"
    if len(clean) == 6:
        if clean.startswith('6'): s = ".SH"
        elif clean.startswith(('0','3')): s = ".SZ"
        elif clean.startswith(('8','4')): s = ".BJ"
        else: return False, "未知前缀"
        return True, clean + s
    return False, "格式错误"

def get_stock_name_by_code(ts_code):
    pro = get_tushare_pro()
    if not pro: return "未连接"
    try:
        if ts_code.endswith('.HK'):
            df = pro.hk_basic(ts_code=ts_code)
        else:
            df = pro.stock_basic(ts_code=ts_code)
        if not df.empty: return df.iloc[0]['name']
    except: pass
    return ts_code

def search_stocks(keyword):
    pro = get_tushare_pro()
    if not pro: return []
    res = []
    try:
        # A股
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
        if not df.empty:
            mask = df['name'].str.contains(keyword, na=False) | df['ts_code'].str.contains(keyword, na=False)
            res.extend([{"代码":r['ts_code'],"名称":r['name'],"类型":"A股"} for _,r in df[mask].head(5).iterrows()])
        # 港股
        try:
            df_hk = pro.hk_basic(list_status='L', fields='ts_code,name')
            if not df_hk.empty:
                mask = df_hk['name'].str.contains(keyword, na=False) | df_hk['ts_code'].str.contains(keyword, na=False)
                res.extend([{"代码":r['ts_code'],"名称":r['name'],"类型":"港股"} for _,r in df_hk[mask].head(5).iterrows()])
        except: pass
        return res[:10]
    except: return []

# ===================== 核心指标获取 (仅A股) =====================

def get_latest_metrics(pro, ts_code):
    """
    统一获取基本面指标
    注意：Tushare 目前仅支持 A股 的 daily_basic
    """
    metrics = {
        "turnover_rate": "N/A",
        "pe_ttm": "N/A", 
        "pb": "N/A", 
        "total_mv": "N/A"
    }
    
    # 港股：目前Tushare API不支持每日估值指标，直接返回 N/A
    if ts_code.endswith('.HK'):
        metrics["turnover_rate"] = "N/A (Tushare源缺)"
        metrics["pe_ttm"] = "N/A (Tushare源缺)"
        metrics["pb"] = "N/A (Tushare源缺)"
        metrics["total_mv"] = "N/A (Tushare源缺)"
        return metrics

    # A股：正常获取
    try:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=20)).strftime('%Y%m%d')
        
        fields = 'trade_date,turnover_rate,pe_ttm,pb,total_mv'
        df = pro.daily_basic(ts_code=ts_code, start_date=start, end_date=end, fields=fields)
        
        if not df.empty:
            r = df.sort_values('trade_date', ascending=False).iloc[0]
            if pd.notna(r.get('turnover_rate')): metrics['turnover_rate'] = f"{r['turnover_rate']:.2f}%"
            if pd.notna(r.get('pe_ttm')): metrics['pe_ttm'] = f"{r['pe_ttm']:.2f}"
            if pd.notna(r.get('pb')): metrics['pb'] = f"{r['pb']:.2f}"
            if pd.notna(r.get('total_mv')): metrics['total_mv'] = f"{r['total_mv']/10000:.2f}亿"
            
    except Exception as e:
        print(f"Metrics Error: {e}")
        pass
        
    return metrics

# ===================== 技术指标计算 =====================

def get_enhanced_technical_indicators(df):
    try:
        if df.empty: return df
        df = df.sort_values('trade_date').reset_index(drop=True)
        close = df['close']
        
        df['ma5'] = close.rolling(5).mean()
        df['ma10'] = close.rolling(10).mean()
        df['ma20'] = close.rolling(20).mean()
        
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['dif'] = exp1 - exp2
        df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
        df['macd'] = (df['dif'] - df['dea']) * 2
        
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['bb_mid'] = close.rolling(20).mean()
        std = close.rolling(20).std()
        df['bb_up'] = df['bb_mid'] + 2 * std
        df['bb_low'] = df['bb_mid'] - 2 * std
        df['volatility'] = df['pct_chg'].rolling(20).std()
        
        return df
    except: return df

# ===================== 数据获取主入口 =====================

@st.cache_data(ttl=600) 
def get_clean_market_data(ts_code, days=90):
    pro = get_tushare_pro()
    if not pro: return {"错误": "Token无效"}
    
    try:
        # 1. 获取基本面指标 (A股有，港股无)
        metrics = get_latest_metrics(pro, ts_code)
        
        # 2. 获取K线行情 (A股/港股都有)
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        df = pd.DataFrame()
        if ts_code.endswith('.HK'):
            try: df = pro.hk_daily(ts_code=ts_code, start_date=start, end_date=end)
            except Exception as e: return {"错误": f"港股接口错: {e}"}
        else:
            df = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
        
        if df.empty: return {"错误": "暂无行情数据"}
        
        # 3. 计算技术指标
        df = get_enhanced_technical_indicators(df)
        latest = df.iloc[-1]

        return {
            "收盘价": f"{latest['close']}",
            "涨跌幅": f"{latest['pct_chg']:.2f}%",
            "成交量": f"{latest['vol']/10000:.2f}万手",
            "换手率": metrics['turnover_rate'], 
            "5日均线": f"{latest['ma5']:.2f}" if pd.notna(latest['ma5']) else "-",
            "10日均线": f"{latest['ma10']:.2f}" if pd.notna(latest['ma10']) else "-",
            "20日均线": f"{latest['ma20']:.2f}" if pd.notna(latest['ma20']) else "-",
            "MACD": f"{latest['macd']:.4f}" if pd.notna(latest['macd']) else "-",
            "RSI": f"{latest['rsi']:.2f}" if pd.notna(latest['rsi']) else "-",
            "布林上轨": f"{latest['bb_up']:.2f}" if pd.notna(latest['bb_up']) else "-",
            "布林中轨": f"{latest['bb_mid']:.2f}" if pd.notna(latest['bb_mid']) else "-",
            "布林下轨": f"{latest['bb_low']:.2f}" if pd.notna(latest['bb_low']) else "-",
            "波动率": f"{latest['volatility']:.4f}" if pd.notna(latest['volatility']) else "-",
            "_metrics_cache": metrics 
        }
    except Exception as e: return {"错误": str(e)}

def get_clean_fundamental_data(ts_code, daily_data=None):
    pro = get_tushare_pro()
    
    industry = "未知"
    
    # 复用缓存
    metrics = None
    if daily_data and '_metrics_cache' in daily_data:
        metrics = daily_data['_metrics_cache']
    if not metrics:
        metrics = get_latest_metrics(pro, ts_code)

    try:
        # 获取行业
        if ts_code.endswith('.HK'):
            try:
                b = pro.hk_basic(ts_code=ts_code)
                if not b.empty: industry = b.iloc[0].get('industry', '港股')
            except: pass
        else:
            b = pro.stock_basic(ts_code=ts_code, fields='industry')
            if not b.empty: industry = b.iloc[0]['industry']
    except: pass

    return {
        "PE(TTM)": metrics['pe_ttm'],
        "PB": metrics['pb'],
        "总市值": metrics['total_mv'],
        "所属行业": industry
    }

def get_market_environment_data(ts_code):
    pro = get_tushare_pro()
    change, sentiment, name = "0.00%", "中性", "未知"
    try:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        # 1. 沪深300兜底
        try:
            df = pro.index_daily(ts_code='399300.SZ', start_date=start, end_date=end)
            if not df.empty:
                change = f"{df.iloc[0]['pct_chg']:.2f}%"
                name = "沪深300"
        except: pass

        # 2. 港股尝试恒指
        if ts_code.endswith('.HK'):
            try:
                df = pro.index_daily(ts_code='HSI', start_date=start, end_date=end)
                if not df.empty:
                    change = f"{df.iloc[0]['pct_chg']:.2f}%"
                    name = "恒生指数"
            except: pass
        
        try:
            val = float(change.replace('%',''))
            if val > 1: sentiment = "乐观"
            elif val < -1: sentiment = "悲观"
        except: pass
    except: pass
    return {"市场指数涨跌幅": f"{change} ({name})", "市场情绪": sentiment}
