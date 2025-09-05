#!/usr/bin/env python3
"""
Web-based Database Viewer for MC L10n
提供一个基于浏览器的数据库查看和分析界面
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uvicorn
import argparse

app = FastAPI(title="MC L10n Database Viewer", version="1.0.0")

# 添加CORS支持
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
        raise HTTPException(status_code=404, detail=f"Database file not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面 - 数据库查看器UI"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MC L10n 数据库查看器</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            
            .tab {
                padding: 12px 24px;
                background: white;
                border: none;
                border-radius: 8px 8px 0 0;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: all 0.3s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .tab:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            
            .tab.active {
                background: #4CAF50;
                color: white;
            }
            
            .content {
                background: white;
                border-radius: 0 8px 8px 8px;
                padding: 30px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                min-height: 600px;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                transition: transform 0.3s;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .stat-label {
                font-size: 1rem;
                opacity: 0.9;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }
            
            th {
                background: #f5f5f5;
                font-weight: 600;
                color: #333;
                position: sticky;
                top: 0;
                z-index: 10;
            }
            
            tr:hover {
                background: #f9f9f9;
            }
            
            .search-box {
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
            }
            
            .search-input {
                flex: 1;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            
            .search-input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .btn {
                padding: 12px 24px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s;
            }
            
            .btn:hover {
                background: #764ba2;
                transform: translateY(-2px);
            }
            
            .loading {
                text-align: center;
                padding: 50px;
                font-size: 1.2rem;
                color: #666;
            }
            
            .error {
                background: #ff5252;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .success {
                background: #4CAF50;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .mod-name {
                font-weight: 500;
                color: #333;
            }
            
            .mod-version {
                color: #666;
                font-size: 0.9rem;
            }
            
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin: 5px 0;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #8BC34A);
                transition: width 0.3s;
            }
            
            .filter-section {
                margin-bottom: 20px;
                padding: 15px;
                background: #f5f5f5;
                border-radius: 8px;
            }
            
            .filter-group {
                display: flex;
                gap: 10px;
                align-items: center;
                margin-bottom: 10px;
            }
            
            .filter-label {
                font-weight: 500;
                min-width: 80px;
            }
            
            select {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 MC L10n 数据库查看器</h1>
            
            <div class="tabs">
                <button class="tab active" onclick="showTab('overview')">📊 概览</button>
                <button class="tab" onclick="showTab('sessions')">🔍 扫描会话</button>
                <button class="tab" onclick="showTab('mods')">📦 模组列表</button>
                <button class="tab" onclick="showTab('results')">📝 扫描结果</button>
                <button class="tab" onclick="showTab('export')">💾 导出数据</button>
            </div>
            
            <div class="content">
                <div id="overview" class="tab-content">
                    <h2>数据库统计概览</h2>
                    <div class="stats-grid" id="stats"></div>
                    <h3>TOP 10 模组（按翻译键数量）</h3>
                    <div id="top-mods"></div>
                </div>
                
                <div id="sessions" class="tab-content" style="display:none;">
                    <h2>扫描会话历史</h2>
                    <div id="sessions-list"></div>
                </div>
                
                <div id="mods" class="tab-content" style="display:none;">
                    <h2>模组列表</h2>
                    <div class="search-box">
                        <input type="text" class="search-input" id="mod-search" placeholder="搜索模组名称...">
                        <button class="btn" onclick="searchMods()">搜索</button>
                    </div>
                    <div id="mods-list"></div>
                </div>
                
                <div id="results" class="tab-content" style="display:none;">
                    <h2>扫描结果详情</h2>
                    <div class="filter-section">
                        <div class="filter-group">
                            <span class="filter-label">扫描会话:</span>
                            <select id="scan-filter" onchange="loadResults()">
                                <option value="">所有会话</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <span class="filter-label">语言代码:</span>
                            <select id="lang-filter" onchange="loadResults()">
                                <option value="">所有语言</option>
                            </select>
                        </div>
                    </div>
                    <div id="results-list"></div>
                </div>
                
                <div id="export" class="tab-content" style="display:none;">
                    <h2>导出数据</h2>
                    <p style="margin: 20px 0;">选择要导出的数据类型：</p>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button class="btn" onclick="exportData('summary')">📊 导出统计摘要</button>
                        <button class="btn" onclick="exportData('sessions')">🔍 导出扫描会话</button>
                        <button class="btn" onclick="exportData('mods')">📦 导出模组列表</button>
                        <button class="btn" onclick="exportData('results')">📝 导出扫描结果</button>
                        <button class="btn" onclick="exportData('all')">💾 导出全部数据</button>
                    </div>
                    <div id="export-status" style="margin-top: 20px;"></div>
                </div>
            </div>
        </div>
        
        <script>
            // 页面加载时初始化
            window.onload = function() {
                loadOverview();
                loadScanSessions();
                loadLanguages();
            };
            
            // 标签切换
            function showTab(tabName) {
                // 隐藏所有内容
                const contents = document.querySelectorAll('.tab-content');
                contents.forEach(c => c.style.display = 'none');
                
                // 移除所有标签的active状态
                const tabs = document.querySelectorAll('.tab');
                tabs.forEach(t => t.classList.remove('active'));
                
                // 显示选中的内容
                document.getElementById(tabName).style.display = 'block';
                
                // 设置选中的标签为active
                event.target.classList.add('active');
                
                // 根据标签加载相应数据
                switch(tabName) {
                    case 'overview':
                        loadOverview();
                        break;
                    case 'sessions':
                        loadSessions();
                        break;
                    case 'mods':
                        loadMods();
                        break;
                    case 'results':
                        loadResults();
                        break;
                }
            }
            
            // 加载概览数据
            async function loadOverview() {
                try {
                    const response = await fetch('/api/overview');
                    const data = await response.json();
                    
                    // 显示统计数据
                    const statsHtml = `
                        <div class="stat-card">
                            <div class="stat-number">${data.total_scans}</div>
                            <div class="stat-label">扫描次数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.total_mods}</div>
                            <div class="stat-label">模组总数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.total_language_files}</div>
                            <div class="stat-label">语言文件</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${data.total_keys}</div>
                            <div class="stat-label">翻译键</div>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;
                    
                    // 显示TOP模组
                    if (data.top_mods && data.top_mods.length > 0) {
                        let tableHtml = '<table><thead><tr><th>排名</th><th>模组名称</th><th>版本</th><th>翻译键数</th><th>语言数</th></tr></thead><tbody>';
                        data.top_mods.forEach((mod, index) => {
                            tableHtml += `
                                <tr>
                                    <td>${index + 1}</td>
                                    <td class="mod-name">${mod.mod_name}</td>
                                    <td class="mod-version">${mod.mod_version || 'N/A'}</td>
                                    <td>${mod.max_keys}</td>
                                    <td>${mod.lang_count}</td>
                                </tr>
                            `;
                        });
                        tableHtml += '</tbody></table>';
                        document.getElementById('top-mods').innerHTML = tableHtml;
                    }
                } catch (error) {
                    console.error('Error loading overview:', error);
                }
            }
            
            // 加载扫描会话
            async function loadSessions() {
                try {
                    const response = await fetch('/api/sessions');
                    const sessions = await response.json();
                    
                    if (sessions.length > 0) {
                        let html = '<table><thead><tr><th>扫描ID</th><th>状态</th><th>路径</th><th>进度</th><th>模组数</th><th>开始时间</th><th>耗时</th></tr></thead><tbody>';
                        sessions.forEach(session => {
                            const statusColor = session.status === 'completed' ? 'green' : session.status === 'scanning' ? 'orange' : 'gray';
                            html += `
                                <tr>
                                    <td>${session.scan_id.substring(0, 12)}...</td>
                                    <td style="color: ${statusColor}; font-weight: bold;">${session.status}</td>
                                    <td>${session.target_path || session.path}</td>
                                    <td>
                                        <div class="progress-bar">
                                            <div class="progress-fill" style="width: ${session.progress_percent}%"></div>
                                        </div>
                                        ${session.progress_percent.toFixed(1)}%
                                    </td>
                                    <td>${session.total_mods}</td>
                                    <td>${new Date(session.started_at).toLocaleString('zh-CN')}</td>
                                    <td>${session.duration ? session.duration + 's' : '-'}</td>
                                </tr>
                            `;
                        });
                        html += '</tbody></table>';
                        document.getElementById('sessions-list').innerHTML = html;
                        
                        // 更新扫描会话过滤器
                        const scanFilter = document.getElementById('scan-filter');
                        scanFilter.innerHTML = '<option value="">所有会话</option>';
                        sessions.forEach(session => {
                            scanFilter.innerHTML += `<option value="${session.scan_id}">${session.scan_id.substring(0, 12)}... - ${session.target_path || session.path}</option>`;
                        });
                    } else {
                        document.getElementById('sessions-list').innerHTML = '<p>暂无扫描会话记录</p>';
                    }
                } catch (error) {
                    console.error('Error loading sessions:', error);
                    document.getElementById('sessions-list').innerHTML = '<p class="error">加载失败: ' + error.message + '</p>';
                }
            }
            
            // 加载扫描会话列表（用于过滤器）
            async function loadScanSessions() {
                try {
                    const response = await fetch('/api/sessions');
                    const sessions = await response.json();
                    
                    const scanFilter = document.getElementById('scan-filter');
                    scanFilter.innerHTML = '<option value="">所有会话</option>';
                    sessions.forEach(session => {
                        scanFilter.innerHTML += `<option value="${session.scan_id}">${session.scan_id.substring(0, 12)}...</option>`;
                    });
                } catch (error) {
                    console.error('Error loading scan sessions:', error);
                }
            }
            
            // 加载语言列表
            async function loadLanguages() {
                try {
                    const response = await fetch('/api/languages');
                    const languages = await response.json();
                    
                    const langFilter = document.getElementById('lang-filter');
                    langFilter.innerHTML = '<option value="">所有语言</option>';
                    languages.forEach(lang => {
                        langFilter.innerHTML += `<option value="${lang}">${lang}</option>`;
                    });
                } catch (error) {
                    console.error('Error loading languages:', error);
                }
            }
            
            // 加载模组列表
            async function loadMods(search = '') {
                try {
                    const url = search ? `/api/mods?search=${encodeURIComponent(search)}` : '/api/mods';
                    const response = await fetch(url);
                    const mods = await response.json();
                    
                    if (mods.length > 0) {
                        let html = '<table><thead><tr><th>模组名称</th><th>模组ID</th><th>版本</th><th>翻译键数</th><th>语言数</th></tr></thead><tbody>';
                        mods.forEach(mod => {
                            html += `
                                <tr>
                                    <td class="mod-name">${mod.mod_name || mod.mod_id}</td>
                                    <td>${mod.mod_id || '-'}</td>
                                    <td class="mod-version">${mod.mod_version || 'N/A'}</td>
                                    <td>${mod.max_keys}</td>
                                    <td>${mod.lang_count}</td>
                                </tr>
                            `;
                        });
                        html += '</tbody></table>';
                        document.getElementById('mods-list').innerHTML = html;
                    } else {
                        document.getElementById('mods-list').innerHTML = '<p>没有找到匹配的模组</p>';
                    }
                } catch (error) {
                    console.error('Error loading mods:', error);
                    document.getElementById('mods-list').innerHTML = '<p class="error">加载失败: ' + error.message + '</p>';
                }
            }
            
            // 搜索模组
            function searchMods() {
                const searchTerm = document.getElementById('mod-search').value;
                loadMods(searchTerm);
            }
            
            // 加载扫描结果
            async function loadResults() {
                try {
                    const scanId = document.getElementById('scan-filter').value;
                    const langCode = document.getElementById('lang-filter').value;
                    
                    let url = '/api/results?';
                    if (scanId) url += `scan_id=${scanId}&`;
                    if (langCode) url += `language=${langCode}&`;
                    
                    const response = await fetch(url);
                    const results = await response.json();
                    
                    if (results.length > 0) {
                        let html = '<table><thead><tr><th>模组名称</th><th>版本</th><th>语言</th><th>翻译键数</th><th>文件路径</th></tr></thead><tbody>';
                        results.forEach(result => {
                            html += `
                                <tr>
                                    <td class="mod-name">${result.mod_name || result.mod_id || 'Unknown'}</td>
                                    <td class="mod-version">${result.mod_version || 'N/A'}</td>
                                    <td>${result.language_code || 'en_us'}</td>
                                    <td>${result.keys_count}</td>
                                    <td style="font-size: 0.85rem; color: #666;">${result.file_path}</td>
                                </tr>
                            `;
                        });
                        html += '</tbody></table>';
                        document.getElementById('results-list').innerHTML = html;
                    } else {
                        document.getElementById('results-list').innerHTML = '<p>没有找到扫描结果</p>';
                    }
                } catch (error) {
                    console.error('Error loading results:', error);
                    document.getElementById('results-list').innerHTML = '<p class="error">加载失败: ' + error.message + '</p>';
                }
            }
            
            // 导出数据
            async function exportData(type) {
                try {
                    const statusDiv = document.getElementById('export-status');
                    statusDiv.innerHTML = '<p class="loading">正在导出...</p>';
                    
                    const response = await fetch(`/api/export/${type}`);
                    const data = await response.blob();
                    
                    // 创建下载链接
                    const url = window.URL.createObjectURL(data);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `mc_l10n_${type}_${new Date().getTime()}.json`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    statusDiv.innerHTML = '<p class="success">✅ 导出成功！文件已开始下载。</p>';
                } catch (error) {
                    console.error('Error exporting data:', error);
                    document.getElementById('export-status').innerHTML = '<p class="error">导出失败: ' + error.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/api/overview")
async def get_overview():
    """获取数据库概览统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取统计数据
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT scan_id) as total_scans,
                SUM(total_mods) as total_mods,
                SUM(total_language_files) as total_language_files,
                SUM(total_keys) as total_keys
            FROM scan_sessions 
            WHERE status = 'completed'
        """)
        stats = cursor.fetchone()
        
        # 获取TOP模组
        cursor.execute("""
            SELECT 
                mod_name,
                mod_version,
                MAX(keys_count) as max_keys,
                COUNT(DISTINCT language_code) as lang_count
            FROM scan_results 
            WHERE mod_name IS NOT NULL
            GROUP BY mod_name, mod_version
            ORDER BY max_keys DESC
            LIMIT 10
        """)
        top_mods = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_scans": stats["total_scans"] or 0,
            "total_mods": stats["total_mods"] or 0,
            "total_language_files": stats["total_language_files"] or 0,
            "total_keys": stats["total_keys"] or 0,
            "top_mods": top_mods
        }
    finally:
        conn.close()


@app.get("/api/sessions")
async def get_sessions(limit: int = 50):
    """获取扫描会话列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                scan_id,
                status,
                path,
                target_path,
                scan_mode,
                started_at,
                completed_at,
                total_mods,
                total_language_files,
                total_keys,
                progress_percent,
                CASE 
                    WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
                    THEN ROUND((julianday(completed_at) - julianday(started_at)) * 86400, 2)
                    ELSE NULL
                END as duration
            FROM scan_sessions 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (limit,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        return sessions
    finally:
        conn.close()


@app.get("/api/mods")
async def get_mods(search: Optional[str] = None, limit: int = 100):
    """获取模组列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT 
                mod_id,
                mod_name,
                mod_version,
                MAX(keys_count) as max_keys,
                COUNT(DISTINCT language_code) as lang_count
            FROM scan_results
        """
        
        if search:
            query += " WHERE mod_name LIKE ? OR mod_id LIKE ?"
            params = (f"%{search}%", f"%{search}%", limit)
        else:
            params = (limit,)
        
        query += """
            GROUP BY mod_id, mod_name, mod_version
            ORDER BY max_keys DESC
            LIMIT ?
        """
        
        cursor.execute(query, params)
        mods = [dict(row) for row in cursor.fetchall()]
        return mods
    finally:
        conn.close()


@app.get("/api/results")
async def get_results(
    scan_id: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 200
):
    """获取扫描结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM scan_results WHERE 1=1"
        params = []
        
        if scan_id:
            query += " AND scan_id = ?"
            params.append(scan_id)
        
        if language:
            query += " AND language_code = ?"
            params.append(language)
        
        query += " ORDER BY keys_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    finally:
        conn.close()


@app.get("/api/languages")
async def get_languages():
    """获取所有语言代码"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT DISTINCT language_code 
            FROM scan_results 
            WHERE language_code IS NOT NULL
            ORDER BY language_code
        """)
        languages = [row[0] for row in cursor.fetchall()]
        return languages
    finally:
        conn.close()


@app.get("/api/export/{export_type}")
async def export_data(export_type: str):
    """导出数据为JSON"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        export_data = {}
        
        if export_type in ["summary", "all"]:
            # 导出统计摘要
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT scan_id) as total_scans,
                    SUM(total_mods) as total_mods,
                    SUM(total_language_files) as total_language_files,
                    SUM(total_keys) as total_keys
                FROM scan_sessions 
                WHERE status = 'completed'
            """)
            export_data["summary"] = dict(cursor.fetchone())
        
        if export_type in ["sessions", "all"]:
            # 导出扫描会话
            cursor.execute("SELECT * FROM scan_sessions ORDER BY started_at DESC")
            export_data["sessions"] = [dict(row) for row in cursor.fetchall()]
        
        if export_type in ["mods", "all"]:
            # 导出模组列表
            cursor.execute("""
                SELECT 
                    mod_id,
                    mod_name,
                    mod_version,
                    MAX(keys_count) as max_keys,
                    COUNT(DISTINCT language_code) as lang_count
                FROM scan_results
                GROUP BY mod_id, mod_name, mod_version
                ORDER BY max_keys DESC
            """)
            export_data["mods"] = [dict(row) for row in cursor.fetchall()]
        
        if export_type in ["results", "all"]:
            # 导出扫描结果
            cursor.execute("SELECT * FROM scan_results ORDER BY keys_count DESC")
            export_data["results"] = [dict(row) for row in cursor.fetchall()]
        
        # 添加导出时间
        export_data["export_time"] = datetime.now().isoformat()
        export_data["export_type"] = export_type
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=mc_l10n_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    finally:
        conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MC L10n Web数据库查看器')
    parser.add_argument('--db', default='mc_l10n_unified.db', help='数据库文件路径')
    parser.add_argument('--port', type=int, default=18080, help='Web服务端口')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    
    args = parser.parse_args()
    
    global DB_PATH
    DB_PATH = args.db
    
    # 检查数据库文件
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    print(f"""
    ╔════════════════════════════════════════════════════╗
    ║     🎮 MC L10n Web 数据库查看器 v1.0.0           ║
    ╠════════════════════════════════════════════════════╣
    ║                                                    ║
    ║  📁 数据库: {DB_PATH:<38} ║
    ║  🌐 地址:   http://{args.host}:{args.port:<29} ║
    ║                                                    ║
    ║  按 Ctrl+C 停止服务器                              ║
    ╚════════════════════════════════════════════════════╝
    """)
    
    # 启动服务器
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()