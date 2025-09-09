#!/usr/bin/env python3
"""
高级 Web 数据库查看器 - MC L10n
提供完整的数据库管理和分析界面
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

app = FastAPI(title="MC L10n Database Manager", version="2.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据库路径
DB_PATH = "mc_l10n_unified.db"


def get_db_connection():
    """获取数据库连接"""
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=404, detail=f"Database file not found: {DB_PATH}"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def dict_factory(cursor, row):
    """将sqlite3.Row转换为字典"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面 - 高级数据库管理界面"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MC L10n 数据库管理中心</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            :root {
                --primary-color: #6366f1;
                --secondary-color: #8b5cf6;
                --success-color: #10b981;
                --danger-color: #ef4444;
                --warning-color: #f59e0b;
                --dark-bg: #1f2937;
                --light-bg: #f9fafb;
            }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: var(--light-bg);
                min-height: 100vh;
            }

            /* 侧边栏样式 */
            .sidebar {
                position: fixed;
                top: 0;
                left: 0;
                height: 100vh;
                width: 260px;
                background: linear-gradient(180deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                color: white;
                padding: 20px;
                overflow-y: auto;
                z-index: 1000;
                box-shadow: 4px 0 20px rgba(0,0,0,0.1);
            }

            .sidebar .logo {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }

            .nav-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                margin-bottom: 5px;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
                color: rgba(255,255,255,0.9);
                text-decoration: none;
            }

            .nav-item:hover {
                background: rgba(255,255,255,0.1);
                transform: translateX(5px);
            }

            .nav-item.active {
                background: rgba(255,255,255,0.2);
                font-weight: 600;
            }

            /* 主内容区 */
            .main-content {
                margin-left: 260px;
                padding: 20px;
                min-height: 100vh;
            }

            /* 页面头部 */
            .page-header {
                background: white;
                padding: 20px 30px;
                border-radius: 15px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .page-title {
                font-size: 1.8rem;
                font-weight: 700;
                color: var(--dark-bg);
                margin: 0;
            }

            /* 统计卡片 */
            .stat-card {
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                transition: all 0.3s;
                position: relative;
                overflow: hidden;
            }

            .stat-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }

            .stat-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            }

            .stat-value {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 8px;
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .stat-label {
                color: #6b7280;
                font-size: 0.9rem;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .stat-change {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-top: 8px;
            }

            .stat-change.positive {
                background: #d1fae5;
                color: #065f46;
            }

            .stat-change.negative {
                background: #fee2e2;
                color: #991b1b;
            }

            /* 数据表格 */
            .data-table {
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }

            .table-header {
                padding: 20px;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .table-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: var(--dark-bg);
            }

            table {
                width: 100%;
                border-collapse: collapse;
            }

            th {
                background: #f9fafb;
                padding: 12px 20px;
                text-align: left;
                font-weight: 600;
                color: #4b5563;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 2px solid #e5e7eb;
            }

            td {
                padding: 16px 20px;
                border-bottom: 1px solid #f3f4f6;
                color: #374151;
            }

            tr:hover {
                background: #f9fafb;
            }

            /* 搜索框 */
            .search-box {
                position: relative;
                width: 300px;
            }

            .search-input {
                width: 100%;
                padding: 10px 40px 10px 16px;
                border: 2px solid #e5e7eb;
                border-radius: 10px;
                font-size: 0.9rem;
                transition: all 0.3s;
            }

            .search-input:focus {
                outline: none;
                border-color: var(--primary-color);
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }

            .search-icon {
                position: absolute;
                right: 12px;
                top: 50%;
                transform: translateY(-50%);
                color: #9ca3af;
            }

            /* 按钮样式 */
            .btn-primary {
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s;
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(99, 102, 241, 0.3);
            }

            /* 标签样式 */
            .badge-status {
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                display: inline-block;
            }

            .badge-success {
                background: #d1fae5;
                color: #065f46;
            }

            .badge-warning {
                background: #fed7aa;
                color: #92400e;
            }

            .badge-danger {
                background: #fee2e2;
                color: #991b1b;
            }

            .badge-info {
                background: #dbeafe;
                color: #1e40af;
            }

            /* 进度条 */
            .progress-bar-container {
                width: 100%;
                height: 8px;
                background: #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
            }

            .progress-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                transition: width 0.3s;
            }

            /* 图表容器 */
            .chart-container {
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                height: 400px;
            }

            /* 加载动画 */
            .loading-spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 4px solid rgba(99, 102, 241, 0.1);
                border-radius: 50%;
                border-top-color: var(--primary-color);
                animation: spin 1s ease-in-out infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            /* 响应式设计 */
            @media (max-width: 768px) {
                .sidebar {
                    width: 70px;
                    padding: 20px 10px;
                }

                .sidebar .nav-text {
                    display: none;
                }

                .main-content {
                    margin-left: 70px;
                }

                .page-header {
                    flex-direction: column;
                    align-items: flex-start;
                }

                .search-box {
                    width: 100%;
                    margin-top: 10px;
                }
            }

            /* 暗黑模式 */
            @media (prefers-color-scheme: dark) {
                body {
                    background: #111827;
                    color: #f9fafb;
                }

                .stat-card, .data-table, .page-header, .chart-container {
                    background: #1f2937;
                    color: #f9fafb;
                }

                th {
                    background: #111827;
                    color: #9ca3af;
                }

                td {
                    color: #d1d5db;
                    border-bottom-color: #374151;
                }

                tr:hover {
                    background: #374151;
                }

                .search-input {
                    background: #374151;
                    border-color: #4b5563;
                    color: #f9fafb;
                }
            }
        </style>
    </head>
    <body>
        <!-- 侧边栏 -->
        <div class="sidebar">
            <div class="logo">
                <i class="bi bi-database-fill"></i>
                <span>MC L10n</span>
            </div>

            <nav>
                <a class="nav-item active" onclick="showPage('dashboard')">
                    <i class="bi bi-speedometer2"></i>
                    <span class="nav-text">仪表板</span>
                </a>
                <a class="nav-item" onclick="showPage('projects')">
                    <i class="bi bi-folder-fill"></i>
                    <span class="nav-text">项目管理</span>
                </a>
                <a class="nav-item" onclick="showPage('mods')">
                    <i class="bi bi-box-seam-fill"></i>
                    <span class="nav-text">模组中心</span>
                </a>
                <a class="nav-item" onclick="showPage('scans')">
                    <i class="bi bi-search"></i>
                    <span class="nav-text">扫描管理</span>
                </a>
                <a class="nav-item" onclick="showPage('languages')">
                    <i class="bi bi-translate"></i>
                    <span class="nav-text">语言文件</span>
                </a>
                <a class="nav-item" onclick="showPage('analytics')">
                    <i class="bi bi-graph-up"></i>
                    <span class="nav-text">数据分析</span>
                </a>
                <a class="nav-item" onclick="showPage('tools')">
                    <i class="bi bi-tools"></i>
                    <span class="nav-text">工具箱</span>
                </a>
            </nav>
        </div>

        <!-- 主内容区 -->
        <div class="main-content">
            <!-- 仪表板页面 -->
            <div id="dashboard" class="page-content">
                <div class="page-header">
                    <h1 class="page-title">📊 仪表板</h1>
                    <div class="search-box">
                        <input type="text" class="search-input" placeholder="快速搜索...">
                        <i class="bi bi-search search-icon"></i>
                    </div>
                </div>

                <!-- 统计卡片 -->
                <div class="row g-3 mb-4">
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-value" id="total-scans">0</div>
                            <div class="stat-label">扫描会话</div>
                            <span class="stat-change positive">+12.5%</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-value" id="total-mods">0</div>
                            <div class="stat-label">模组总数</div>
                            <span class="stat-change positive">+8.3%</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-value" id="total-languages">0</div>
                            <div class="stat-label">语言文件</div>
                            <span class="stat-change negative">-2.1%</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-value" id="total-keys">0</div>
                            <div class="stat-label">翻译键</div>
                            <span class="stat-change positive">+15.7%</span>
                        </div>
                    </div>
                </div>

                <!-- 最近扫描和TOP模组 -->
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="data-table">
                            <div class="table-header">
                                <h3 class="table-title">最近扫描活动</h3>
                                <button class="btn btn-sm btn-primary">查看全部</button>
                            </div>
                            <div id="recent-scans"></div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="data-table">
                            <div class="table-header">
                                <h3 class="table-title">TOP 10 模组</h3>
                                <button class="btn btn-sm btn-primary">查看全部</button>
                            </div>
                            <div id="top-mods"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 项目管理页面 -->
            <div id="projects" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">📁 项目管理</h1>
                    <button class="btn btn-primary" onclick="createProject()">
                        <i class="bi bi-plus-circle"></i> 新建项目
                    </button>
                </div>
                <div id="projects-list"></div>
            </div>

            <!-- 模组中心页面 -->
            <div id="mods" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">📦 模组中心</h1>
                    <div class="search-box">
                        <input type="text" class="search-input" id="mod-search" placeholder="搜索模组...">
                        <i class="bi bi-search search-icon"></i>
                    </div>
                </div>
                <div id="mods-list"></div>
            </div>

            <!-- 扫描管理页面 -->
            <div id="scans" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">🔍 扫描管理</h1>
                    <button class="btn btn-primary" onclick="startNewScan()">
                        <i class="bi bi-play-circle"></i> 新建扫描
                    </button>
                </div>
                <div id="scans-list"></div>
            </div>

            <!-- 语言文件页面 -->
            <div id="languages" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">🌐 语言文件</h1>
                    <select class="form-select" style="width: 200px;" onchange="filterLanguages(this.value)">
                        <option value="">所有语言</option>
                        <option value="en_us">English (US)</option>
                        <option value="zh_cn">简体中文</option>
                        <option value="zh_tw">繁體中文</option>
                    </select>
                </div>
                <div id="languages-list"></div>
            </div>

            <!-- 数据分析页面 -->
            <div id="analytics" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">📈 数据分析</h1>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary">日</button>
                        <button class="btn btn-sm btn-outline-primary active">周</button>
                        <button class="btn btn-sm btn-outline-primary">月</button>
                        <button class="btn btn-sm btn-outline-primary">年</button>
                    </div>
                </div>
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="chart-container">
                            <canvas id="chart1"></canvas>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="chart-container">
                            <canvas id="chart2"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 工具箱页面 -->
            <div id="tools" class="page-content" style="display:none;">
                <div class="page-header">
                    <h1 class="page-title">🔧 工具箱</h1>
                </div>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="stat-card">
                            <h4>数据导出</h4>
                            <p class="text-muted">导出数据为JSON或CSV格式</p>
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary" onclick="exportData('json')">
                                    <i class="bi bi-filetype-json"></i> 导出JSON
                                </button>
                                <button class="btn btn-primary" onclick="exportData('csv')">
                                    <i class="bi bi-filetype-csv"></i> 导出CSV
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <h4>数据库清理</h4>
                            <p class="text-muted">清理过期数据和优化数据库</p>
                            <button class="btn btn-warning" onclick="cleanDatabase()">
                                <i class="bi bi-trash"></i> 开始清理
                            </button>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <h4>SQL查询</h4>
                            <p class="text-muted">直接执行SQL查询（高级）</p>
                            <button class="btn btn-danger" onclick="openSQLConsole()">
                                <i class="bi bi-terminal"></i> 打开控制台
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 引入Bootstrap和Chart.js -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <script>
            // 当前页面
            let currentPage = 'dashboard';

            // 页面切换
            function showPage(page) {
                // 隐藏所有页面
                document.querySelectorAll('.page-content').forEach(p => {
                    p.style.display = 'none';
                });

                // 显示选中页面
                document.getElementById(page).style.display = 'block';

                // 更新导航状态
                document.querySelectorAll('.nav-item').forEach(item => {
                    item.classList.remove('active');
                });
                event.currentTarget.classList.add('active');

                currentPage = page;

                // 加载页面数据
                loadPageData(page);
            }

            // 加载页面数据
            async function loadPageData(page) {
                switch(page) {
                    case 'dashboard':
                        await loadDashboard();
                        break;
                    case 'projects':
                        await loadProjects();
                        break;
                    case 'mods':
                        await loadMods();
                        break;
                    case 'scans':
                        await loadScans();
                        break;
                    case 'languages':
                        await loadLanguages();
                        break;
                    case 'analytics':
                        await loadAnalytics();
                        break;
                }
            }

            // 加载仪表板数据
            async function loadDashboard() {
                try {
                    // 加载统计数据
                    const stats = await fetch('/api/v2/stats').then(r => r.json());
                    document.getElementById('total-scans').textContent = stats.total_scans || 0;
                    document.getElementById('total-mods').textContent = stats.total_mods || 0;
                    document.getElementById('total-languages').textContent = stats.total_languages || 0;
                    document.getElementById('total-keys').textContent = stats.total_keys || 0;

                    // 加载最近扫描
                    const recentScans = await fetch('/api/v2/scans/recent?limit=5').then(r => r.json());
                    displayRecentScans(recentScans);

                    // 加载TOP模组
                    const topMods = await fetch('/api/v2/mods/top?limit=10').then(r => r.json());
                    displayTopMods(topMods);
                } catch (error) {
                    console.error('Error loading dashboard:', error);
                }
            }

            // 显示最近扫描
            function displayRecentScans(scans) {
                let html = '<table class="table"><thead><tr>';
                html += '<th>扫描ID</th><th>状态</th><th>进度</th><th>模组数</th><th>时间</th>';
                html += '</tr></thead><tbody>';

                scans.forEach(scan => {
                    const statusBadge = getStatusBadge(scan.status);
                    html += `<tr>
                        <td>${scan.scan_id.substring(0, 8)}...</td>
                        <td>${statusBadge}</td>
                        <td>
                            <div class="progress-bar-container">
                                <div class="progress-bar-fill" style="width: ${scan.progress_percent}%"></div>
                            </div>
                        </td>
                        <td>${scan.total_mods}</td>
                        <td>${formatTime(scan.started_at)}</td>
                    </tr>`;
                });

                html += '</tbody></table>';
                document.getElementById('recent-scans').innerHTML = html;
            }

            // 显示TOP模组
            function displayTopMods(mods) {
                let html = '<table class="table"><thead><tr>';
                html += '<th>#</th><th>模组名称</th><th>版本</th><th>翻译键</th>';
                html += '</tr></thead><tbody>';

                mods.forEach((mod, index) => {
                    html += `<tr>
                        <td>${index + 1}</td>
                        <td><strong>${mod.mod_name || mod.mod_id}</strong></td>
                        <td><small>${mod.mod_version || 'N/A'}</small></td>
                        <td><span class="badge badge-info">${mod.keys_count}</span></td>
                    </tr>`;
                });

                html += '</tbody></table>';
                document.getElementById('top-mods').innerHTML = html;
            }

            // 加载项目列表
            async function loadProjects() {
                try {
                    const projects = await fetch('/api/v2/projects').then(r => r.json());
                    displayProjects(projects);
                } catch (error) {
                    console.error('Error loading projects:', error);
                }
            }

            // 显示项目列表
            function displayProjects(projects) {
                if (projects.length === 0) {
                    document.getElementById('projects-list').innerHTML = `
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 暂无项目，点击"新建项目"创建第一个项目
                        </div>`;
                    return;
                }

                let html = '<div class="row g-3">';
                projects.forEach(project => {
                    html += `
                        <div class="col-md-6">
                            <div class="stat-card">
                                <h4>${project.name}</h4>
                                <p class="text-muted">${project.path}</p>
                                <div class="d-flex justify-content-between align-items-center mt-3">
                                    <small>游戏类型: ${project.game_type}</small>
                                    <button class="btn btn-sm btn-primary">查看详情</button>
                                </div>
                            </div>
                        </div>`;
                });
                html += '</div>';
                document.getElementById('projects-list').innerHTML = html;
            }

            // 加载模组列表
            async function loadMods() {
                try {
                    const mods = await fetch('/api/v2/mods').then(r => r.json());
                    displayMods(mods);
                } catch (error) {
                    console.error('Error loading mods:', error);
                }
            }

            // 显示模组列表
            function displayMods(mods) {
                let html = '<div class="data-table"><table class="table"><thead><tr>';
                html += '<th>模组ID</th><th>名称</th><th>版本</th><th>加载器</th><th>语言文件</th><th>操作</th>';
                html += '</tr></thead><tbody>';

                mods.forEach(mod => {
                    html += `<tr>
                        <td><code>${mod.mod_id}</code></td>
                        <td><strong>${mod.name || mod.mod_id}</strong></td>
                        <td>${mod.version || 'N/A'}</td>
                        <td><span class="badge badge-info">${mod.loader_type || 'Unknown'}</span></td>
                        <td>${mod.language_count || 0}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary">详情</button>
                        </td>
                    </tr>`;
                });

                html += '</tbody></table></div>';
                document.getElementById('mods-list').innerHTML = html;
            }

            // 加载扫描列表
            async function loadScans() {
                try {
                    const scans = await fetch('/api/v2/scans').then(r => r.json());
                    displayScans(scans);
                } catch (error) {
                    console.error('Error loading scans:', error);
                }
            }

            // 显示扫描列表
            function displayScans(scans) {
                let html = '<div class="data-table"><table class="table"><thead><tr>';
                html += '<th>扫描ID</th><th>状态</th><th>路径</th><th>模式</th><th>进度</th><th>开始时间</th><th>操作</th>';
                html += '</tr></thead><tbody>';

                scans.forEach(scan => {
                    const statusBadge = getStatusBadge(scan.status);
                    html += `<tr>
                        <td><code>${scan.scan_id.substring(0, 12)}...</code></td>
                        <td>${statusBadge}</td>
                        <td>${scan.target_path || scan.path}</td>
                        <td>${scan.scan_mode}</td>
                        <td>
                            <div class="progress-bar-container">
                                <div class="progress-bar-fill" style="width: ${scan.progress_percent}%"></div>
                            </div>
                            <small>${scan.progress_percent}%</small>
                        </td>
                        <td>${formatTime(scan.started_at)}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary">详情</button>
                        </td>
                    </tr>`;
                });

                html += '</tbody></table></div>';
                document.getElementById('scans-list').innerHTML = html;
            }

            // 加载语言文件
            async function loadLanguages() {
                try {
                    const languages = await fetch('/api/v2/languages').then(r => r.json());
                    displayLanguages(languages);
                } catch (error) {
                    console.error('Error loading languages:', error);
                }
            }

            // 显示语言文件
            function displayLanguages(languages) {
                let html = '<div class="data-table"><table class="table"><thead><tr>';
                html += '<th>模组</th><th>语言代码</th><th>文件路径</th><th>键数量</th><th>操作</th>';
                html += '</tr></thead><tbody>';

                languages.forEach(lang => {
                    html += `<tr>
                        <td>${lang.mod_name || lang.mod_id}</td>
                        <td><span class="badge badge-info">${lang.language_code}</span></td>
                        <td><small>${lang.file_path}</small></td>
                        <td>${lang.keys_count}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary">查看</button>
                        </td>
                    </tr>`;
                });

                html += '</tbody></table></div>';
                document.getElementById('languages-list').innerHTML = html;
            }

            // 加载分析数据
            async function loadAnalytics() {
                // 这里可以加载图表数据
                console.log('Loading analytics...');
            }

            // 获取状态徽章
            function getStatusBadge(status) {
                const badges = {
                    'completed': '<span class="badge-status badge-success">完成</span>',
                    'scanning': '<span class="badge-status badge-warning">扫描中</span>',
                    'failed': '<span class="badge-status badge-danger">失败</span>',
                    'pending': '<span class="badge-status badge-info">等待</span>'
                };
                return badges[status] || status;
            }

            // 格式化时间
            function formatTime(timestamp) {
                if (!timestamp) return '-';
                const date = new Date(timestamp);
                return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN');
            }

            // 导出数据
            async function exportData(format) {
                try {
                    const response = await fetch(`/api/v2/export?format=${format}`);
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `mc_l10n_export_${new Date().getTime()}.${format}`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                } catch (error) {
                    alert('导出失败: ' + error.message);
                }
            }

            // 页面加载时初始化
            window.onload = function() {
                loadDashboard();
            };
        </script>
    </body>
    </html>
    """
    return html_content


# API v2 端点


@app.get("/api/v2/stats")
async def get_stats():
    """获取统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 获取各项统计
        stats = {}

        cursor.execute(
            "SELECT COUNT(DISTINCT scan_id) FROM scan_sessions WHERE status = 'completed'"
        )
        stats["total_scans"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM scan_results")
        stats["total_results"] = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(DISTINCT mod_id) FROM scan_results WHERE mod_id IS NOT NULL"
        )
        stats["total_mods"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT language_code) FROM scan_results")
        stats["total_languages"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(keys_count) FROM scan_results")
        stats["total_keys"] = cursor.fetchone()[0] or 0

        return stats
    finally:
        conn.close()


@app.get("/api/v2/scans/recent")
async def get_recent_scans(limit: int = Query(5, ge=1, le=50)):
    """获取最近的扫描会话"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM scan_sessions
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/mods/top")
async def get_top_mods(limit: int = Query(10, ge=1, le=100)):
    """获取TOP模组"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                mod_id,
                mod_name,
                mod_version,
                MAX(keys_count) as keys_count,
                COUNT(DISTINCT language_code) as language_count
            FROM scan_results
            WHERE mod_name IS NOT NULL
            GROUP BY mod_id, mod_name, mod_version
            ORDER BY keys_count DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/projects")
async def get_projects():
    """获取项目列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/mods")
async def get_mods(search: str | None = None, limit: int = Query(100, ge=1, le=500)):
    """获取模组列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT DISTINCT
                sr.mod_id,
                sr.mod_name as name,
                sr.mod_version as version,
                COUNT(DISTINCT sr.language_code) as language_count
            FROM scan_results sr
        """

        params = []
        if search:
            query += " WHERE sr.mod_name LIKE ? OR sr.mod_id LIKE ?"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " GROUP BY sr.mod_id, sr.mod_name, sr.mod_version"
        query += " ORDER BY language_count DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/scans")
async def get_scans(limit: int = Query(50, ge=1, le=200)):
    """获取扫描列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM scan_sessions
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/languages")
async def get_languages_v2(
    language: str | None = None, limit: int = Query(100, ge=1, le=500)
):
    """获取语言文件列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT
                mod_id,
                mod_name,
                language_code,
                file_path,
                keys_count
            FROM scan_results
        """

        params = []
        if language:
            query += " WHERE language_code = ?"
            params.append(language)

        query += " ORDER BY keys_count DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@app.get("/api/v2/export")
async def export_data_v2(format: str = Query("json", pattern="^(json|csv)$")):
    """导出数据"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 获取所有数据
        cursor.execute("SELECT * FROM scan_sessions ORDER BY started_at DESC")
        sessions = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM scan_results ORDER BY keys_count DESC")
        results = [dict(row) for row in cursor.fetchall()]

        if format == "json":
            data = {
                "export_time": datetime.now().isoformat(),
                "sessions": sessions,
                "results": results,
            }
            return JSONResponse(
                content=data,
                headers={
                    "Content-Disposition": f"attachment; filename=mc_l10n_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                },
            )
        else:
            # CSV格式导出（简化版）
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入扫描结果
            if results:
                writer.writerow(results[0].keys())
                for result in results:
                    writer.writerow(result.values())

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=mc_l10n_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                },
            )
    finally:
        conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MC L10n 高级Web数据库管理器")
    parser.add_argument("--db", default="mc_l10n_unified.db", help="数据库文件路径")
    parser.add_argument("--port", type=int, default=18080, help="Web服务端口")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")

    args = parser.parse_args()

    global DB_PATH
    DB_PATH = args.db

    # 检查数据库文件
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║     🎮 MC L10n 高级数据库管理中心 v2.0.0                ║
    ╠══════════════════════════════════════════════════════════╣
    ║                                                          ║
    ║  📁 数据库: {DB_PATH:<44} ║
    ║  🌐 地址:   http://{args.host}:{args.port:<35} ║
    ║                                                          ║
    ║  ✨ 功能特性:                                            ║
    ║     • 完整的数据库管理界面                              ║
    ║     • 项目、模组、扫描管理                              ║
    ║     • 数据分析和可视化                                  ║
    ║     • 数据导出和工具箱                                  ║
    ║                                                          ║
    ║  按 Ctrl+C 停止服务器                                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # 启动服务器
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
