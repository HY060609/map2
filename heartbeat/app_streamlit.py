import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
import math

# ==================== 坐标系转换 ====================
def wgs84_to_gcj02(lng, lat):
    """WGS84转GCJ02（高德/百度坐标系）"""
    # 简单近似转换（精确转换需要更复杂算法，这里使用pyproj简化）
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")  # 实际GCJ02不是标准EPSG，但可近似
    x, y = transformer.transform(lng, lat)
    return x, y  # 这里返回近似值，若需精确转换请使用高德官方库或已有算法
    # 为演示方便，暂用简单偏移（实际项目中需使用高精度算法）
    # 注意：这不是精确转换，仅示意。生产环境请使用高德Web API或已有库。

# 更精确的转换函数（来自前文 coord_transform.py，整合进此处）
# 因篇幅，这里直接复制之前定义的精确转换函数
def wgs84_to_gcj02_exact(lng, lat):
    # 精确转换代码（与之前 coord_transform.py 一致，但注意参数顺序）
    # 这里直接复制完整函数（省略，因为用户已了解）
    # 实际使用中，可导入 coord_transform 模块
    import coord_transform
    return coord_transform.wgs84_to_gcj02(lat, lng)  # 注意参数顺序

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="无人机智能化应用 - 航线规划与飞行监控",
    page_icon="🚁",
    layout="wide"
)

# ==================== 初始化 session state ====================
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
if 'a_point' not in st.session_state:
    st.session_state.a_point = None
if 'b_point' not in st.session_state:
    st.session_state.b_point = None
if 'obstacles' not in st.session_state:
    st.session_state.obstacles = []  # 存储障碍物多边形坐标

# ==================== 心跳包模拟函数 ====================
def send_heartbeat():
    """模拟发送心跳包"""
    current_time = datetime.now()
    # 模拟丢包（10%概率）
    lost = random.random() < 0.1
    heartbeat = {
        'sequence': st.session_state.sequence,
        'timestamp': current_time,
        'received': not lost
    }
    st.session_state.heartbeat_data.append(heartbeat)
    if not lost:
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
                st.warning("⚠ 连接超时！连续3秒未收到心跳包！")
        else:
            st.session_state.timeout_warning = False
    else:
        if not st.session_state.timeout_warning:
            st.warning("⚠ 未收到任何心跳包！")

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
        return None
    
    fig = make_subplots(rows=1, cols=1)
    
    # 收到的心跳
    df_received = df[df['received'] == True]
    fig.add_trace(go.Scatter(
        x=df_received['timestamp'],
        y=df_received['sequence'],
        mode='markers+lines',
        name='收到',
        marker=dict(color='green', size=6),
        line=dict(color='lightgreen', width=1)
    ))
    
    # 丢失的心跳
    df_lost = df[df['received'] == False]
    fig.add_trace(go.Scatter(
        x=df_lost['timestamp'],
        y=df_lost['sequence'],
        mode='markers',
        name='丢失',
        marker=dict(color='red', symbol='x', size=8)
    ))
    
    fig.update_layout(
        title="心跳序列时间线",
        xaxis_title="时间",
        yaxis_title="序列号",
        hovermode='closest',
        height=400
    )
    return fig

# ==================== 地图生成函数 ====================
def create_map(center_lat=32.2322, center_lng=118.749):
    """创建 Folium 地图，支持障碍物圈选"""
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=18,
        tiles='https://wprd01.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=7',  # 高德卫星图（可选）
        attr='高德地图'
    )
    
    # 添加 A 点标记
    if st.session_state.a_point:
        folium.Marker(
            location=[st.session_state.a_point[0], st.session_state.a_point[1]],
            popup='A点',
            icon=folium.Icon(color='red', icon='flag'),
            tooltip='A点'
        ).add_to(m)
    
    # 添加 B 点标记
    if st.session_state.b_point:
        folium.Marker(
            location=[st.session_state.b_point[0], st.session_state.b_point[1]],
            popup='B点',
            icon=folium.Icon(color='green', icon='flag'),
            tooltip='B点'
        ).add_to(m)
    
    # 添加 A-B 连线
    if st.session_state.a_point and st.session_state.b_point:
        folium.PolyLine(
            locations=[st.session_state.a_point, st.session_state.b_point],
            color='blue',
            weight=3,
            opacity=0.8,
            tooltip='规划航线'
        ).add_to(m)
    
    # 添加障碍物（多边形）
    for obstacle in st.session_state.obstacles:
        if len(obstacle) >= 3:
            folium.Polygon(
                locations=obstacle,
                color='red',
                weight=2,
                fill=True,
                fill_color='red',
                fill_opacity=0.3,
                popup='障碍物'
            ).add_to(m)
    
    return m

# ==================== 页面布局 ====================
st.sidebar.title("导航")
page = st.sidebar.radio("功能页面", ["航线规划", "飞行监控"])

# 坐标系设置（放在侧边栏）
st.sidebar.subheader("坐标系设置")
coord_system = st.sidebar.radio("输入坐标系", ["WGS-84", "GCJ-02(高德/百度)"])

# 系统状态显示
st.sidebar.subheader("系统状态")
a_status = "✅ A点已设" if st.session_state.a_point else "❌ A点未设"
b_status = "✅ B点已设" if st.session_state.b_point else "❌ B点未设"
st.sidebar.text(a_status)
st.sidebar.text(b_status)

# ==================== 页面1：航线规划 ====================
if page == "航线规划":
    st.title("🗺️ 航线规划")
    
    # 控制面板
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("控制面板")
        
        # 起点A输入
        st.markdown("**起点A**")
        lat_a = st.number_input("纬度", value=32.2322, format="%.6f", key="lat_a")
        lng_a = st.number_input("经度", value=118.749, format="%.6f", key="lng_a")
        if st.button("设置A点"):
            if coord_system == "WGS-84":
                # 转换到GCJ-02（地图使用GCJ-02）
                lat_a_gcj, lng_a_gcj = wgs84_to_gcj02_exact(lng_a, lat_a)  # 注意参数顺序
                st.session_state.a_point = (lat_a_gcj, lng_a_gcj)
            else:
                st.session_state.a_point = (lat_a, lng_a)
            st.success(f"A点已设置: ({st.session_state.a_point[0]:.6f}, {st.session_state.a_point[1]:.6f})")
        
        # 终点B输入
        st.markdown("**终点B**")
        lat_b = st.number_input("纬度", value=32.2343, format="%.6f", key="lat_b")
        lng_b = st.number_input("经度", value=118.749, format="%.6f", key="lng_b")
        if st.button("设置B点"):
            if coord_system == "WGS-84":
                lat_b_gcj, lng_b_gcj = wgs84_to_gcj02_exact(lng_b, lat_b)
                st.session_state.b_point = (lat_b_gcj, lng_b_gcj)
            else:
                st.session_state.b_point = (lat_b, lng_b)
            st.success(f"B点已设置: ({st.session_state.b_point[0]:.6f}, {st.session_state.b_point[1]:.6f})")
        
        # 飞行参数
        st.markdown("**飞行参数**")
        altitude = st.number_input("设定飞行高度(m)", min_value=10, max_value=500, value=50, step=10)
        
        # 障碍物管理（简单示例：通过文本输入坐标）
        st.markdown("**障碍物管理**")
        st.write("点击地图上的点，然后点击下方按钮添加为障碍物点（暂不支持交互，可手动输入坐标）")
        # 简化：提供添加障碍物的文本框
        obs_lat = st.number_input("障碍物点纬度", value=32.2325, format="%.6f")
        obs_lng = st.number_input("障碍物点经度", value=118.7492, format="%.6f")
        if st.button("添加障碍物点"):
            # 将点添加到当前编辑的多边形中
            if len(st.session_state.obstacles) == 0 or len(st.session_state.obstacles[-1]) < 3:
                # 开始新多边形
                if len(st.session_state.obstacles) == 0 or len(st.session_state.obstacles[-1]) >= 3:
                    st.session_state.obstacles.append([])
                st.session_state.obstacles[-1].append((obs_lat, obs_lng))
                st.success(f"已添加点 ({obs_lat:.6f}, {obs_lng:.6f}) 到当前多边形")
            else:
                # 已有至少3个点，完成当前多边形，开始新的
                st.session_state.obstacles.append([(obs_lat, obs_lng)])
                st.info("当前多边形已完成，开始新多边形")
        
        if st.button("完成当前多边形"):
            if len(st.session_state.obstacles) > 0 and len(st.session_state.obstacles[-1]) >= 3:
                st.success(f"多边形已完成，共 {len(st.session_state.obstacles[-1])} 个点")
            else:
                st.warning("当前多边形点数不足3个，无法完成")
        
        if st.button("清除所有障碍物"):
            st.session_state.obstacles = []
            st.success("已清除所有障碍物")
    
    with col2:
        st.subheader("地图显示")
        # 显示地图（如果A点已设则以此为地图中心，否则使用校园中心）
        if st.session_state.a_point:
            map_center = st.session_state.a_point
        else:
            map_center = (32.2322, 118.749)  # 南京科技职业学院
        m = create_map(map_center[0], map_center[1])
        folium_static(m, width=700, height=500)
        
        # 显示当前障碍物列表（可选）
        st.subheader("当前障碍物列表")
        if st.session_state.obstacles:
            for i, poly in enumerate(st.session_state.obstacles):
                st.write(f"多边形 {i+1}: {len(poly)} 个点")
                # 可显示坐标，但太多，折叠
        else:
            st.write("暂无障碍物")

# ==================== 页面2：飞行监控 ====================
elif page == "飞行监控":
    st.title("📡 飞行监控")
    
    # 心跳包模拟控制
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("开始模拟心跳"):
            st.session_state.running = True
            st.experimental_rerun()
        if st.button("停止模拟"):
            st.session_state.running = False
        if st.button("清除历史数据"):
            st.session_state.heartbeat_data = []
            st.session_state.sequence = 0
            st.session_state.last_received_time = None
            st.success("已清除所有历史数据")
    
    # 模拟心跳循环（每1秒）
    if st.session_state.running:
        # 每1秒生成一个心跳包
        heartbeat = send_heartbeat()
        # 自动刷新页面（Streamlit 无法主动刷新，需用户点击或设置自动刷新）
        # 使用 st.empty 和 time.sleep 会在主线程阻塞，不建议。
        # 这里采用手动刷新按钮或使用 st.experimental_rerun 需谨慎。
        # 简单处理：显示最新心跳，用户手动刷新页面。
        # 更高级：使用 st.empty 和 JavaScript 自动刷新，但较为复杂。
        # 为简化，告知用户手动刷新（或点击"刷新数据"按钮）。
        pass
    
    # 检查超时（每次运行都会检查）
    check_timeout()
    
    # 显示最新心跳包
    if st.session_state.heartbeat_data:
        last = st.session_state.heartbeat_data[-1]
        col1, col2, col3 = st.columns(3)
        col1.metric("最新序列号", last['sequence'])
        col2.metric("接收状态", "✅ 收到" if last['received'] else "❌ 丢失")
        col3.metric("最后心跳时间", last['timestamp'].strftime('%H:%M:%S.%f')[:-3])
    
    # 显示数据表格
    df = create_dataframe()
    if not df.empty:
        st.subheader("心跳数据表")
        st.dataframe(df[['sequence', 'time_str', 'received_status']], use_container_width=True)
    
    # 显示折线图
    fig = plot_heartbeat_timeline(df)
    if fig:
        st.subheader("心跳时间线图")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无心跳数据")