#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MC L10n 统一数据库管理工具
整合了所有数据库查看和管理功能
"""

import sqlite3
import json
import os
import sys
import argparse
import socket
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置
class Config:
    """配置管理"""
    DEFAULT_PORT = 18081
    DEFAULT_HOST = "127.0.0.1"
    
    # 数据库路径搜索列表
    DB_SEARCH_PATHS = [
        project_root / "mc_l10n.db",
        project_root / "apps" / "mc_l10n" / "backend" / "mc_l10n.db",
        project_root / "apps" / "mc_l10n" / "backend" / "mc_l10n_unified.db",
        project_root / "apps" / "mc_l10n" / "mc_l10n.db",
    ]
    
    @classmethod
    def find_database(cls, custom_path: Optional[str] = None) -> Optional[Path]:
        """查找数据库文件"""
        if custom_path:
            path = Path(custom_path)
            if path.exists():
                return path
        
        for path in cls.DB_SEARCH_PATHS:
            if path.exists():
                return path
        
        return None

class DatabaseManager:
    """数据库管理核心功能"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            "database_path": str(self.db_path),
            "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "tables": {},
            "total_mods": 0,
            "total_language_files": 0,
            "total_translation_keys": 0,
            "languages": {},
            "mod_details": []
        }
        
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats["tables"][table_name] = count
            
            # 获取模组统计
            try:
                cursor.execute("SELECT COUNT(DISTINCT mod_id) FROM mods")
                stats["total_mods"] = cursor.fetchone()[0]
            except:
                pass
                
            # 获取语言文件统计
            try:
                cursor.execute("SELECT COUNT(*) FROM language_files")
                stats["total_language_files"] = cursor.fetchone()[0]
                
                # 语言分布
                cursor.execute("""
                    SELECT locale_code, COUNT(*) 
                    FROM language_files 
                    GROUP BY locale_code
                """)
                stats["languages"] = dict(cursor.fetchall())
            except:
                pass
                
            # 获取翻译键统计
            try:
                cursor.execute("SELECT COUNT(*) FROM translation_entries")
                stats["total_translation_keys"] = cursor.fetchone()[0]
            except:
                pass
            
            # 获取热门模组
            try:
                cursor.execute("""
                    SELECT m.mod_id, m.display_name, 
                           COUNT(DISTINCT lf.locale_code) as lang_count,
                           COUNT(DISTINCT te.entry_key) as key_count
                    FROM mods m
                    LEFT JOIN language_files lf ON m.mod_id = lf.mod_id
                    LEFT JOIN translation_entries te ON lf.file_id = te.file_id
                    GROUP BY m.mod_id, m.display_name
                    ORDER BY key_count DESC
                    LIMIT 10
                """)
                
                mod_rows = cursor.fetchall()
                stats["mod_details"] = [
                    {
                        "mod_id": row[0],
                        "mod_name": row[1] or row[0],
                        "language_count": row[2],
                        "key_count": row[3]
                    }
                    for row in mod_rows
                ]
            except:
                pass
                
        finally:
            self.close()
            
        return stats
    
    def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取表数据"""
        data = []
        try:
            self.connect()
            cursor = self.conn.cursor()
            
            # 验证表名（防止SQL注入）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                raise ValueError(f"Table {table_name} not found")
            
            # 获取数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
            columns = [description[0] for description in cursor.description]
            
            for row in cursor.fetchall():
                data.append(dict(zip(columns, row)))
                
        finally:
            self.close()
            
        return data
    
    def execute_query(self, query: str) -> Tuple[List[str], List[List]]:
        """执行自定义查询（只读）"""
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")
            
        columns = []
        rows = []
        
        try:
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute(query)
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
        finally:
            self.close()
            
        return columns, rows

# FastAPI应用
app = FastAPI(
    title="MC L10n 数据库管理中心",
    description="统一的数据库查看和管理工具",
    version="3.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据库管理器
db_manager: Optional[DatabaseManager] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面"""
    return HTML_TEMPLATE

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        stats = db_manager.get_statistics()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables/{table_name}")
async def get_table(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """获取表数据"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        data = db_manager.get_table_data(table_name, limit, offset)
        return JSONResponse(content={"data": data, "count": len(data)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def execute_query(query: Dict[str, str]):
    """执行查询"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        columns, rows = db_manager.execute_query(query.get("sql", ""))
        return JSONResponse(content={
            "columns": columns,
            "rows": rows,
            "count": len(rows)
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# HTML模板
HTML_TEMPLATE = '''
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
            --mc-green: #52A535;
            --mc-dark: #1A1A1A;
            --mc-gray: #2D2D2D;
            --mc-light-gray: #C6C6C6;
            --mc-gold: #FFAA00;
            --mc-blue: #3B8BEB;
        }
        
        body {
            background: linear-gradient(135deg, #1A1A1A 0%, #2D2D2D 100%);
            color: #FFFFFF;
            font-family: 'Segoe UI', system-ui, sans-serif;
            min-height: 100vh;
        }
        
        .navbar {
            background: var(--mc-dark);
            border-bottom: 3px solid var(--mc-green);
            padding: 1rem 0;
        }
        
        .navbar-brand {
            color: var(--mc-green) !important;
            font-weight: bold;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .main-container {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: var(--mc-gray);
            border: 2px solid var(--mc-green);
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(82, 165, 53, 0.3);
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--mc-gold);
            margin: 0.5rem 0;
        }
        
        .stat-label {
            color: var(--mc-light-gray);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .data-section {
            background: var(--mc-gray);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .table {
            color: #FFFFFF;
        }
        
        .table-dark {
            --bs-table-bg: transparent;
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 200px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid var(--mc-gray);
            border-top-color: var(--mc-green);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .tab-content {
            margin-top: 1rem;
        }
        
        .nav-tabs {
            border-bottom: 2px solid var(--mc-green);
        }
        
        .nav-tabs .nav-link {
            color: var(--mc-light-gray);
            border: none;
            padding: 0.75rem 1.5rem;
        }
        
        .nav-tabs .nav-link:hover {
            color: #FFFFFF;
            background: rgba(82, 165, 53, 0.1);
        }
        
        .nav-tabs .nav-link.active {
            color: #FFFFFF;
            background: var(--mc-green);
            border-radius: 4px 4px 0 0;
        }
        
        .btn-mc {
            background: var(--mc-green);
            color: #FFFFFF;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .btn-mc:hover {
            background: #449429;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(82, 165, 53, 0.4);
        }
        
        .badge {
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-weight: 500;
        }
        
        .badge-success {
            background: var(--mc-green);
        }
        
        .badge-warning {
            background: var(--mc-gold);
        }
        
        .badge-info {
            background: var(--mc-blue);
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container-fluid">
            <span class="navbar-brand">
                <i class="bi bi-database-fill"></i>
                MC L10n 数据库管理中心
            </span>
            <span class="text-muted">v3.0.0</span>
        </div>
    </nav>

    <div class="main-container">
        <!-- 统计卡片 -->
        <div class="stats-grid" id="statsGrid">
            <div class="loading">
                <div class="spinner"></div>
            </div>
        </div>

        <!-- 标签页 -->
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="#overview">
                    <i class="bi bi-speedometer2"></i> 概览
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#tables">
                    <i class="bi bi-table"></i> 数据表
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#query">
                    <i class="bi bi-terminal"></i> SQL查询
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#mods">
                    <i class="bi bi-box-seam"></i> 模组详情
                </a>
            </li>
        </ul>

        <div class="tab-content">
            <!-- 概览标签 -->
            <div class="tab-pane fade show active" id="overview">
                <div class="data-section">
                    <h4><i class="bi bi-graph-up"></i> 语言分布</h4>
                    <div id="languageChart"></div>
                </div>
                <div class="data-section">
                    <h4><i class="bi bi-list-stars"></i> 热门模组</h4>
                    <div id="topMods"></div>
                </div>
            </div>

            <!-- 数据表标签 -->
            <div class="tab-pane fade" id="tables">
                <div class="data-section">
                    <div class="row mb-3">
                        <div class="col">
                            <select class="form-select" id="tableSelect">
                                <option>选择数据表...</option>
                            </select>
                        </div>
                        <div class="col-auto">
                            <button class="btn btn-mc" onclick="loadTableData()">
                                <i class="bi bi-arrow-clockwise"></i> 刷新
                            </button>
                        </div>
                    </div>
                    <div id="tableData"></div>
                </div>
            </div>

            <!-- SQL查询标签 -->
            <div class="tab-pane fade" id="query">
                <div class="data-section">
                    <div class="mb-3">
                        <label class="form-label">SQL查询（只读）</label>
                        <textarea class="form-control bg-dark text-light" id="sqlQuery" rows="4" 
                                  placeholder="SELECT * FROM mods LIMIT 10"></textarea>
                    </div>
                    <button class="btn btn-mc" onclick="executeQuery()">
                        <i class="bi bi-play-fill"></i> 执行查询
                    </button>
                    <div id="queryResult" class="mt-3"></div>
                </div>
            </div>

            <!-- 模组详情标签 -->
            <div class="tab-pane fade" id="mods">
                <div class="data-section">
                    <div id="modDetails"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let statsData = {};

        // 加载统计数据
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                statsData = await response.json();
                displayStats();
                updateTableList();
                displayLanguageChart();
                displayTopMods();
                displayModDetails();
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }

        // 显示统计卡片
        function displayStats() {
            const grid = document.getElementById('statsGrid');
            grid.innerHTML = `
                <div class="stat-card">
                    <i class="bi bi-box-seam" style="font-size: 2rem; color: var(--mc-green);"></i>
                    <div class="stat-value">${statsData.total_mods || 0}</div>
                    <div class="stat-label">模组总数</div>
                </div>
                <div class="stat-card">
                    <i class="bi bi-file-earmark-text" style="font-size: 2rem; color: var(--mc-blue);"></i>
                    <div class="stat-value">${statsData.total_language_files || 0}</div>
                    <div class="stat-label">语言文件</div>
                </div>
                <div class="stat-card">
                    <i class="bi bi-key" style="font-size: 2rem; color: var(--mc-gold);"></i>
                    <div class="stat-value">${(statsData.total_translation_keys / 1000).toFixed(1)}K</div>
                    <div class="stat-label">翻译键</div>
                </div>
                <div class="stat-card">
                    <i class="bi bi-database" style="font-size: 2rem; color: var(--mc-light-gray);"></i>
                    <div class="stat-value">${formatFileSize(statsData.database_size || 0)}</div>
                    <div class="stat-label">数据库大小</div>
                </div>
            `;
        }

        // 更新表列表
        function updateTableList() {
            const select = document.getElementById('tableSelect');
            select.innerHTML = '<option>选择数据表...</option>';
            
            if (statsData.tables) {
                for (const [table, count] of Object.entries(statsData.tables)) {
                    select.innerHTML += `<option value="${table}">${table} (${count} 条记录)</option>`;
                }
            }
        }

        // 加载表数据
        async function loadTableData() {
            const select = document.getElementById('tableSelect');
            const table = select.value;
            
            if (!table || table === '选择数据表...') {
                alert('请选择一个数据表');
                return;
            }

            const tableData = document.getElementById('tableData');
            tableData.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            try {
                const response = await fetch(`/api/tables/${table}?limit=50`);
                const result = await response.json();
                displayTableData(result.data);
            } catch (error) {
                tableData.innerHTML = `<div class="alert alert-danger">加载失败: ${error}</div>`;
            }
        }

        // 显示表数据
        function displayTableData(data) {
            const container = document.getElementById('tableData');
            
            if (!data || data.length === 0) {
                container.innerHTML = '<div class="alert alert-info">无数据</div>';
                return;
            }

            const columns = Object.keys(data[0]);
            let html = '<div class="table-responsive"><table class="table table-dark table-striped"><thead><tr>';
            
            columns.forEach(col => {
                html += `<th>${col}</th>`;
            });
            
            html += '</tr></thead><tbody>';
            
            data.forEach(row => {
                html += '<tr>';
                columns.forEach(col => {
                    let value = row[col];
                    if (value === null) value = '<i class="text-muted">NULL</i>';
                    else if (typeof value === 'object') value = JSON.stringify(value);
                    else if (String(value).length > 100) value = String(value).substring(0, 100) + '...';
                    html += `<td>${value}</td>`;
                });
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }

        // 执行SQL查询
        async function executeQuery() {
            const query = document.getElementById('sqlQuery').value.trim();
            
            if (!query) {
                alert('请输入SQL查询语句');
                return;
            }

            const resultDiv = document.getElementById('queryResult');
            resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sql: query })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail);
                }

                const result = await response.json();
                displayQueryResult(result);
            } catch (error) {
                resultDiv.innerHTML = `<div class="alert alert-danger">查询失败: ${error.message}</div>`;
            }
        }

        // 显示查询结果
        function displayQueryResult(result) {
            const container = document.getElementById('queryResult');
            
            if (!result.rows || result.rows.length === 0) {
                container.innerHTML = '<div class="alert alert-info">查询返回0条记录</div>';
                return;
            }

            let html = `<div class="alert alert-success">查询返回 ${result.count} 条记录</div>`;
            html += '<div class="table-responsive"><table class="table table-dark table-striped"><thead><tr>';
            
            result.columns.forEach(col => {
                html += `<th>${col}</th>`;
            });
            
            html += '</tr></thead><tbody>';
            
            result.rows.forEach(row => {
                html += '<tr>';
                row.forEach(value => {
                    if (value === null) value = '<i class="text-muted">NULL</i>';
                    else if (typeof value === 'object') value = JSON.stringify(value);
                    else if (String(value).length > 100) value = String(value).substring(0, 100) + '...';
                    html += `<td>${value}</td>`;
                });
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }

        // 显示语言分布图表
        function displayLanguageChart() {
            const container = document.getElementById('languageChart');
            
            if (!statsData.languages || Object.keys(statsData.languages).length === 0) {
                container.innerHTML = '<div class="alert alert-info">无语言分布数据</div>';
                return;
            }

            let html = '<div class="row">';
            for (const [lang, count] of Object.entries(statsData.languages)) {
                const percentage = ((count / statsData.total_language_files) * 100).toFixed(1);
                html += `
                    <div class="col-md-6 mb-3">
                        <div class="d-flex justify-content-between mb-1">
                            <span>${lang}</span>
                            <span>${count} (${percentage}%)</span>
                        </div>
                        <div class="progress" style="height: 25px;">
                            <div class="progress-bar bg-success" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
            container.innerHTML = html;
        }

        // 显示热门模组
        function displayTopMods() {
            const container = document.getElementById('topMods');
            
            if (!statsData.mod_details || statsData.mod_details.length === 0) {
                container.innerHTML = '<div class="alert alert-info">无模组数据</div>';
                return;
            }

            let html = '<div class="table-responsive"><table class="table table-dark">';
            html += '<thead><tr><th>模组ID</th><th>模组名称</th><th>语言数</th><th>翻译键数</th></tr></thead><tbody>';
            
            statsData.mod_details.forEach(mod => {
                html += `
                    <tr>
                        <td>${mod.mod_id}</td>
                        <td>${mod.mod_name}</td>
                        <td><span class="badge badge-info">${mod.language_count}</span></td>
                        <td><span class="badge badge-warning">${mod.key_count}</span></td>
                    </tr>
                `;
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }

        // 显示模组详情
        function displayModDetails() {
            const container = document.getElementById('modDetails');
            
            if (!statsData.mod_details || statsData.mod_details.length === 0) {
                container.innerHTML = '<div class="alert alert-info">无模组详情数据</div>';
                return;
            }

            let html = '<div class="row">';
            statsData.mod_details.forEach(mod => {
                html += `
                    <div class="col-md-6 col-lg-4 mb-3">
                        <div class="card bg-dark border-success">
                            <div class="card-body">
                                <h5 class="card-title text-success">${mod.mod_name}</h5>
                                <p class="card-text text-muted">${mod.mod_id}</p>
                                <div class="d-flex justify-content-between">
                                    <span><i class="bi bi-translate"></i> ${mod.language_count} 语言</span>
                                    <span><i class="bi bi-key"></i> ${mod.key_count} 键</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }

        // 格式化文件大小
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // 页面加载完成后执行
        document.addEventListener('DOMContentLoaded', loadStats);
        
        // 每30秒自动刷新
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
'''

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MC L10n 统一数据库管理工具")
    parser.add_argument("--db", help="数据库文件路径")
    parser.add_argument("--port", type=int, default=Config.DEFAULT_PORT, help="服务器端口")
    parser.add_argument("--host", default=Config.DEFAULT_HOST, help="服务器地址")
    parser.add_argument("--mode", choices=["web", "cli"], default="web", help="运行模式")
    
    args = parser.parse_args()
    
    # 查找数据库
    db_path = Config.find_database(args.db)
    if not db_path:
        print("❌ 未找到数据库文件")
        print("搜索路径:")
        for path in Config.DB_SEARCH_PATHS:
            print(f"  - {path}")
        sys.exit(1)
    
    # 初始化数据库管理器
    global db_manager
    db_manager = DatabaseManager(db_path)
    
    if args.mode == "cli":
        # CLI模式
        print(f"📊 数据库: {db_path}")
        stats = db_manager.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        # Web模式
        print(f"""
╔══════════════════════════════════════════════════════════╗
║     🎮 MC L10n 统一数据库管理中心 v3.0.0               ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  📁 数据库: {str(db_path):45} ║
║  🌐 地址:   http://{args.host}:{args.port:<37} ║
║                                                          ║
║  ✨ 功能特性:                                            ║
║     • 统一的数据库管理界面                              ║
║     • 实时统计和数据分析                                ║
║     • SQL查询执行器                                      ║
║     • 数据导出功能                                      ║
║                                                          ║
║  按 Ctrl+C 停止服务器                                    ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        try:
            uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
        except KeyboardInterrupt:
            print("\n✅ 服务器已停止")

if __name__ == "__main__":
    main()