import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 设置页面配置
st.set_page_config(
    page_title="无人机心跳监控系统",
    page_icon="🚁",
    layout="wide"
)

# 初始化session state变量
if 'running' not in st.session_state:
    st.session_state.running = False
if 'heartbeat_data' not in st.session_state:
    st.session_state.heartbeat_data = []
if 'last_received_time' not in st.session_state:
    st.session_state.last_received_time = None
if 'timeout_warning' not in st.session_state:
    st.session_state.timeout_warning = False
if 'sequence' not in st.session_state:
    st.session_state.sequence = 0

def send_heartbeat():
    """模拟发送心跳包"""
    current_time = datetime.now()
    heartbeat = {
        'sequence': st.session_state.sequence,
        'timestamp': current_time,
        'received': True  # 假设地面站正常接收
    }
    st.session_state.heartbeat_data.append(heartbeat)
    st.session_state.last_received_time = current_time
    st.session_state.sequence += 1
    return heartbeat

def check_timeout():
    """检查是否超时"""
    if st.session_state.last_received_time:
        time_diff = (datetime.now() - st.session_state.last_received_time).total_seconds()
        if time_diff > 3:
            if not st.session_state.timeout_warning:
                st.session_state.timeout_warning = True
                st.warning("⚠️ 连接超时！连续3秒未收到心跳包！")
        else:
            st.session_state.timeout_warning = False

def simulate_packet_loss():
    """模拟数据包丢失（10%的概率）"""
    return random.random() < 0.1

def create_dataframe():
    """创建数据框用于显示和可视化"""
    if not st.session_state.heartbeat_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(st.session_state.heartbeat_data)
    df['time_str'] = df['timestamp'].dt.strftime('%H:%M:%S.%f')[:-3]
    df['received_status'] = df['received'].map({True: '✅ 收到', False: '❌ 丢失'})
    return df

def plot_heartbeat_timeline(df):
    """绘制心跳时间线图"""
    if df.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('心跳接收状态', '时间间隔分析'),
        vertical_spacing=0.15
    )
    
    # 心跳接收状态图
    colors = ['green' if x else 'red' for x in df['received']]
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=[1] * len(df),
            mode='markers',
            marker=dict(size=10, color=colors),
            text=df['received_status'],
            hoverinfo='text+x',
            name='心跳包'
        ),
        row=1, col=1
    )
    
    # 计算时间间隔
    if len(df) > 1:
        time_diffs = []
        for i in range(1, len(df)):
            diff = (df['timestamp'].iloc[i] - df['timestamp'].iloc[i-1]).total_seconds()
            time_diffs.append(diff)
        
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'][1:],
                y=time_diffs,
                mode='lines+markers',
                line=dict(color='blue', width=2),
                marker=dict(size=6),
                name='时间间隔'
            ),
            row=2, col=1
        )
        
        # 添加超时阈值线
        fig.add_hline(
            y=3, 
            line_dash="dash", 
            line_color="red",
            annotation_text="超时阈值 (3秒)",
            row=2, col=1
        )
    
    # 更新布局
    fig.update_layout(
        height=600,
        showlegend=True,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="时间", row=2, col=1)
    fig.update_yaxes(title_text="状态", row=1, col=1, ticktext=['丢失', '收到'], tickvals=[0, 1])
    fig.update_yaxes(title_text="间隔(秒)", row=2, col=1)
    
    return fig

# 主界面
st.title("🚁 无人机心跳包监控系统")
st.markdown("---")

# 侧边栏控制
with st.sidebar:
    st.header("控制面板")
    
    # 模拟参数设置
    st.subheader("模拟参数")
    simulation_speed = st.slider("模拟速度 (秒/心跳)", 0.5, 2.0, 1.0, 0.1)
    packet_loss_rate = st.slider("丢包率 (%)", 0, 30, 10, 1)
    
    # 控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ 开始模拟", use_container_width=True):
            st.session_state.running = True
            st.session_state.heartbeat_data = []
            st.session_state.sequence = 0
            st.session_state.last_received_time = None
            st.session_state.timeout_warning = False
    
    with col2:
        if st.button("⏹️ 停止模拟", use_container_width=True):
            st.session_state.running = False
    
    # 数据操作
    st.subheader("数据操作")
    if st.button("🗑️ 清空数据", use_container_width=True):
        st.session_state.heartbeat_data = []
        st.session_state.sequence = 0
        st.session_state.last_received_time = None
        st.session_state.timeout_warning = False
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 系统状态")
    
    # 显示当前状态
    if st.session_state.running:
        st.success("🟢 模拟运行中")
    else:
        st.error("🔴 模拟已停止")
    
    st.info(f"已发送心跳: {len(st.session_state.heartbeat_data)}")

# 主内容区
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("心跳总数", len(st.session_state.heartbeat_data))

with col2:
    if st.session_state.heartbeat_data:
        received_count = sum(1 for h in st.session_state.heartbeat_data if h['received'])
        st.metric("成功接收", received_count)
    else:
        st.metric("成功接收", 0)

with col3:
    if st.session_state.heartbeat_data:
        lost_count = sum(1 for h in st.session_state.heartbeat_data if not h['received'])
        st.metric("丢失数量", lost_count)
    else:
        st.metric("丢失数量", 0)

# 实时数据更新区域
chart_placeholder = st.empty()
data_placeholder = st.empty()
warning_placeholder = st.empty()

# 模拟主循环
if st.session_state.running:
    # 创建进度条
    progress_bar = st.progress(0)
    
    for i in range(100):  # 模拟100个心跳包
        if not st.session_state.running:
            break
        
        # 模拟丢包
        if simulate_packet_loss():
            # 丢包：发送但未收到
            current_time = datetime.now()
            heartbeat = {
                'sequence': st.session_state.sequence,
                'timestamp': current_time,
                'received': False
            }
            st.session_state.heartbeat_data.append(heartbeat)
            st.session_state.sequence += 1
        else:
            # 正常接收
            send_heartbeat()
        
        # 检查超时
        check_timeout()
        
        # 更新显示
        df = create_dataframe()
        
        if not df.empty:
            # 更新图表
            fig = plot_heartbeat_timeline(df)
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            
            # 显示数据表
            with data_placeholder.expander("查看详细数据", expanded=False):
                st.dataframe(
                    df[['sequence', 'time_str', 'received_status']].rename(
                        columns={
                            'sequence': '序号',
                            'time_str': '时间',
                            'received_status': '接收状态'
                        }
                    ),
                    use_container_width=True,
                    hide_index=True
                )
        
        # 更新进度条
        progress_bar.progress((i + 1) / 100)
        
        # 等待
        time.sleep(simulation_speed)
    
    progress_bar.empty()

# 如果模拟停止，显示已有数据
else:
    if st.session_state.heartbeat_data:
        df = create_dataframe()
        fig = plot_heartbeat_timeline(df)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("查看详细数据"):
            st.dataframe(
                df[['sequence', 'time_str', 'received_status']].rename(
                    columns={
                        'sequence': '序号',
                        'time_str': '时间',
                        'received_status': '接收状态'
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

# 底部说明
st.markdown("---")
st.markdown("""
### 📝 使用说明
1. 点击 **开始模拟** 启动心跳监控系统
2. 无人机每秒发送一次心跳包（包含序号和时间戳）
3. 地面站持续监控，如果连续3秒未收到心跳包，系统会发出警告
4. 可以通过侧边栏调整模拟速度和丢包率
5. 图表展示心跳接收状态和时间间隔分析
""")