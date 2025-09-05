#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MC L10n 数据库审计工具 v2.0.0
提供高级Web界面查看和审计数据库内容
支持数据导出、SQL查询、详细统计
"""

import sqlite3
import json
import os
import sys
import socket
import signal
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置
# 检查多个可能的数据库位置
possible_db_paths = [
    Path(__file__).parent.parent / "backend" / "mc_l10n_unified.db",  # 优先使用统一数据库
    Path(__file__).parent.parent / "backend" / "mc_l10n.db",
    Path(__file__).parent.parent / "mc_l10n.db",
]

DB_PATH = None
for path in possible_db_paths:
    if path.exists():
        DB_PATH = path
        break

if not DB_PATH:
    print("[WARNING] Database file not found, tried the following paths:")
    for path in possible_db_paths:
        print(f"   - {path}")
    DB_PATH = possible_db_paths[0]  # 使用默认路径

# 默认配置
DEFAULT_PORT = 18082  # 使用18082端口，避免与db_manager冲突
DEFAULT_HOST = "127.0.0.1"

app = FastAPI(title="MC L10n Database Audit Tool", version="2.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TableInfo(BaseModel):
    name: str
    count: int
    columns: List[Dict[str, Any]]


class QueryResult(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    total: int


def get_db_connection():
    """获取数据库连接"""
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Database not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def serialize_row(row):
    """序列化数据库行"""
    result = []
    for value in row:
        if isinstance(value, bytes):
            try:
                # 尝试解码为 UTF-8
                result.append(value.decode('utf-8'))
            except:
                # 如果失败，转为十六进制字符串
                result.append(value.hex())
        elif isinstance(value, (datetime,)):
            result.append(value.isoformat())
        else:
            result.append(value)
    return result


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页 HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MC L10n 数据库审查工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }
        
        .sidebar {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            max-height: calc(100vh - 200px);
            overflow-y: auto;
        }
        
        .content {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            max-height: calc(100vh - 200px);
            overflow: auto;
        }
        
        .table-list {
            list-style: none;
        }
        
        .table-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .table-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .table-item.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .table-name {
            font-weight: 500;
        }
        
        .table-count {
            background: rgba(0, 0, 0, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        
        .controls {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        input[type="number"], input[type="text"], select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        
        button {
            padding: 8px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: scale(1.05);
        }
        
        button:active {
            transform: scale(0.95);
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        .data-table th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .data-table tr:hover {
            background: #f8f9fa;
        }
        
        .null-value {
            color: #999;
            font-style: italic;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        .info {
            background: #d1ecf1;
            color: #0c5460;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        
        .json-view {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 200px;
            overflow: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .search-box {
            flex: 1;
            max-width: 400px;
        }
        
        .search-box input {
            width: 100%;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                max-height: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🔍 MC L10n 数据库审查工具
            </h1>
            <div class="subtitle">
                数据库路径: <span id="dbPath"></span> | 
                状态: <span id="status">连接中...</span>
            </div>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <h3 style="margin-bottom: 15px; color: #333;">数据表</h3>
                <ul class="table-list" id="tableList">
                    <li class="loading">加载中...</li>
                </ul>
            </div>
            
            <div class="content">
                <div id="contentArea">
                    <div class="info">
                        请从左侧选择一个数据表开始审查
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentTable = null;
        let currentData = null;
        let currentPage = 1;
        let pageSize = 50;
        
        async function loadTables() {
            try {
                const response = await fetch('/api/tables');
                const data = await response.json();
                
                const tableList = document.getElementById('tableList');
                tableList.innerHTML = '';
                
                data.tables.forEach(table => {
                    const li = document.createElement('li');
                    li.className = 'table-item';
                    li.innerHTML = `
                        <span class="table-name">${table.name}</span>
                        <span class="table-count">${table.count.toLocaleString()} 行</span>
                    `;
                    li.onclick = () => loadTable(table.name);
                    tableList.appendChild(li);
                });
                
                document.getElementById('dbPath').textContent = data.db_path;
                document.getElementById('status').textContent = '已连接';
                document.getElementById('status').style.color = '#28a745';
            } catch (error) {
                console.error('Failed to load tables:', error);
                document.getElementById('status').textContent = '连接失败';
                document.getElementById('status').style.color = '#dc3545';
            }
        }
        
        async function loadTable(tableName, page = 1) {
            currentTable = tableName;
            currentPage = page;
            
            // 更新选中状态
            document.querySelectorAll('.table-item').forEach(item => {
                if (item.querySelector('.table-name').textContent === tableName) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
            
            const contentArea = document.getElementById('contentArea');
            contentArea.innerHTML = '<div class="loading">加载数据中...</div>';
            
            try {
                // 获取表结构
                const schemaResponse = await fetch(`/api/table/${tableName}/schema`);
                const schema = await schemaResponse.json();
                
                // 获取表数据
                const dataResponse = await fetch(
                    `/api/table/${tableName}/data?page=${page}&page_size=${pageSize}`
                );
                const data = await dataResponse.json();
                currentData = data;
                
                // 渲染内容
                let html = `
                    <h2 style="margin-bottom: 20px; color: #333;">
                        表: ${tableName}
                    </h2>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-label">总行数</div>
                            <div class="stat-value">${data.total.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">列数</div>
                            <div class="stat-value">${data.columns.length}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">当前页</div>
                            <div class="stat-value">${page} / ${Math.ceil(data.total / pageSize)}</div>
                        </div>
                    </div>
                    
                    <div class="controls">
                        <div class="control-group">
                            <label>每页显示:</label>
                            <select id="pageSizeSelect" onchange="changePageSize(this.value)">
                                <option value="10" ${pageSize === 10 ? 'selected' : ''}>10</option>
                                <option value="25" ${pageSize === 25 ? 'selected' : ''}>25</option>
                                <option value="50" ${pageSize === 50 ? 'selected' : ''}>50</option>
                                <option value="100" ${pageSize === 100 ? 'selected' : ''}>100</option>
                                <option value="500" ${pageSize === 500 ? 'selected' : ''}>500</option>
                            </select>
                        </div>
                        
                        <div class="control-group">
                            <button onclick="previousPage()" ${page === 1 ? 'disabled' : ''}>
                                上一页
                            </button>
                            <input type="number" 
                                   value="${page}" 
                                   min="1" 
                                   max="${Math.ceil(data.total / pageSize)}"
                                   onchange="goToPage(this.value)"
                                   style="width: 80px;">
                            <button onclick="nextPage()" 
                                    ${page >= Math.ceil(data.total / pageSize) ? 'disabled' : ''}>
                                下一页
                            </button>
                        </div>
                        
                        <div class="control-group search-box">
                            <input type="text" 
                                   id="searchInput" 
                                   placeholder="搜索表内容..." 
                                   onkeyup="searchTable(this.value)">
                        </div>
                        
                        <div class="control-group">
                            <button onclick="exportData()">导出 JSON</button>
                            <button onclick="exportCSV()">导出 CSV</button>
                            <button onclick="refreshTable()">刷新</button>
                        </div>
                    </div>
                `;
                
                // 表格
                html += '<div style="overflow-x: auto;"><table class="data-table"><thead><tr>';
                data.columns.forEach(col => {
                    html += `<th>${col}</th>`;
                });
                html += '</tr></thead><tbody>';
                
                data.rows.forEach(row => {
                    html += '<tr>';
                    row.forEach((cell, index) => {
                        let cellContent = cell;
                        if (cell === null) {
                            cellContent = '<span class="null-value">NULL</span>';
                        } else if (typeof cell === 'object') {
                            cellContent = `<div class="json-view">${JSON.stringify(cell, null, 2)}</div>`;
                        } else if (typeof cell === 'string' && cell.length > 100) {
                            cellContent = `<div title="${escapeHtml(cell)}">${escapeHtml(cell.substring(0, 100))}...</div>`;
                        } else {
                            cellContent = escapeHtml(String(cell));
                        }
                        html += `<td>${cellContent}</td>`;
                    });
                    html += '</tr>';
                });
                
                html += '</tbody></table></div>';
                
                contentArea.innerHTML = html;
                
            } catch (error) {
                console.error('Failed to load table data:', error);
                contentArea.innerHTML = `
                    <div class="error">
                        加载数据失败: ${error.message}
                    </div>
                `;
            }
        }
        
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
        
        function changePageSize(size) {
            pageSize = parseInt(size);
            if (currentTable) {
                loadTable(currentTable, 1);
            }
        }
        
        function previousPage() {
            if (currentPage > 1) {
                loadTable(currentTable, currentPage - 1);
            }
        }
        
        function nextPage() {
            const maxPage = Math.ceil(currentData.total / pageSize);
            if (currentPage < maxPage) {
                loadTable(currentTable, currentPage + 1);
            }
        }
        
        function goToPage(page) {
            const pageNum = parseInt(page);
            const maxPage = Math.ceil(currentData.total / pageSize);
            if (pageNum >= 1 && pageNum <= maxPage) {
                loadTable(currentTable, pageNum);
            }
        }
        
        function refreshTable() {
            if (currentTable) {
                loadTable(currentTable, currentPage);
            }
        }
        
        function searchTable(query) {
            if (!query) {
                refreshTable();
                return;
            }
            
            const table = document.querySelector('.data-table');
            if (!table) return;
            
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query.toLowerCase())) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }
        
        function exportData() {
            if (!currentData) return;
            
            const dataStr = JSON.stringify({
                table: currentTable,
                columns: currentData.columns,
                rows: currentData.rows,
                total: currentData.total,
                exported_at: new Date().toISOString()
            }, null, 2);
            
            const blob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentTable}_${new Date().getTime()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        function exportCSV() {
            if (!currentData) return;
            
            let csv = currentData.columns.map(col => `"${col}"`).join(',') + '\\n';
            
            currentData.rows.forEach(row => {
                csv += row.map(cell => {
                    if (cell === null) return '""';
                    if (typeof cell === 'object') return `"${JSON.stringify(cell).replace(/"/g, '""')}"`;
                    return `"${String(cell).replace(/"/g, '""')}"`;
                }).join(',') + '\\n';
            });
            
            const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentTable}_${new Date().getTime()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        // 初始化
        loadTables();
    </script>
</body>
</html>
    """
    return html_content


@app.get("/api/tables")
async def get_tables():
    """获取所有表的列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取所有表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = []
        
        for row in cursor.fetchall():
            table_name = row[0]
            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            # 获取列信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [
                {
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3],
                    "default": col[4],
                    "primary_key": bool(col[5])
                }
                for col in cursor.fetchall()
            ]
            
            tables.append({
                "name": table_name,
                "count": count,
                "columns": columns
            })
        
        return {
            "tables": tables,
            "db_path": str(DB_PATH),
            "total_tables": len(tables)
        }
    
    finally:
        conn.close()


@app.get("/api/table/{table_name}/schema")
async def get_table_schema(table_name: str):
    """获取表结构信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # 获取列信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [
            {
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "not_null": bool(col[3]),
                "default_value": col[4],
                "primary_key": bool(col[5])
            }
            for col in cursor.fetchall()
        ]
        
        # 获取索引信息
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = [
            {
                "name": idx[1],
                "unique": bool(idx[2]),
                "origin": idx[3],
                "partial": bool(idx[4])
            }
            for idx in cursor.fetchall()
        ]
        
        # 获取外键信息
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = [
            {
                "id": fk[0],
                "table": fk[2],
                "from": fk[3],
                "to": fk[4],
                "on_update": fk[5],
                "on_delete": fk[6]
            }
            for fk in cursor.fetchall()
        ]
        
        # 获取创建语句
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        create_sql = cursor.fetchone()[0]
        
        return {
            "table_name": table_name,
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
            "create_sql": create_sql
        }
    
    finally:
        conn.close()


@app.get("/api/table/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    order_by: Optional[str] = None,
    order_dir: str = Query("ASC", pattern="^(ASC|DESC)$")
):
    """获取表数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # 获取总行数
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        if search:
            # 简单的全文搜索（注意：这不是最优的实现）
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            where_clauses = [f"{col} LIKE ?" for col in columns]
            count_query += f" WHERE {' OR '.join(where_clauses)}"
            search_params = [f"%{search}%"] * len(columns)
            cursor.execute(count_query, search_params)
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()[0]
        
        # 构建查询
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if search:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            where_clauses = [f"{col} LIKE ?" for col in columns]
            query += f" WHERE {' OR '.join(where_clauses)}"
            params.extend([f"%{search}%"] * len(columns))
        
        if order_by:
            query += f" ORDER BY {order_by} {order_dir}"
        
        # 分页
        offset = (page - 1) * page_size
        query += f" LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        # 执行查询
        cursor.execute(query, params)
        
        # 获取列名
        columns = [description[0] for description in cursor.description]
        
        # 获取数据
        rows = []
        for row in cursor.fetchall():
            rows.append(serialize_row(row))
        
        return {
            "columns": columns,
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    finally:
        conn.close()


@app.get("/api/query")
async def execute_query(sql: str = Query(..., description="SQL query to execute")):
    """执行自定义 SQL 查询（只读）"""
    # 只允许 SELECT 查询
    if not sql.strip().upper().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql)
        
        # 获取列名
        columns = [description[0] for description in cursor.description]
        
        # 获取数据
        rows = []
        for row in cursor.fetchall():
            rows.append(serialize_row(row))
        
        return {
            "columns": columns,
            "rows": rows,
            "total": len(rows)
        }
    
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        conn.close()


@app.get("/api/stats")
async def get_database_stats():
    """获取数据库统计信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取数据库大小
        db_size = os.path.getsize(DB_PATH)
        
        # 获取表统计
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        table_stats = []
        total_rows = 0
        
        for row in cursor.fetchall():
            table_name = row[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_rows += count
            
            table_stats.append({
                "name": table_name,
                "rows": count
            })
        
        # 获取数据库版本
        cursor.execute("SELECT sqlite_version()")
        sqlite_version = cursor.fetchone()[0]
        
        return {
            "database_path": str(DB_PATH),
            "database_size": db_size,
            "database_size_mb": round(db_size / 1024 / 1024, 2),
            "sqlite_version": sqlite_version,
            "total_tables": len(table_stats),
            "total_rows": total_rows,
            "tables": table_stats,
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(DB_PATH)
            ).isoformat()
        }
    
    finally:
        conn.close()


def check_and_kill_port(port: int):
    """检查端口是否被占用，如果是则尝试关闭占用的进程"""
    if not HAS_PSUTIL:
        # 使用系统命令查找并关闭进程
        if platform.system() == "Windows":
            try:
                # 查找占用端口的进程
                result = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'LISTENING' in line:
                            parts = line.split()
                            pid = parts[-1]
                            print(f"[INFO] Found process using port {port} (PID: {pid})")
                            
                            # 检查是否是 Python 进程
                            try:
                                result = subprocess.run(
                                    f'wmic process where ProcessId={pid} get CommandLine',
                                    shell=True, capture_output=True, text=True
                                )
                                if 'db_audit.py' in result.stdout:
                                    print(f"[INFO] Terminating old audit server...")
                                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                                    print(f"[OK] Old process terminated")
                                    return True
                            except:
                                pass
            except Exception as e:
                print(f"[WARNING] Error checking port with netstat: {e}")
        return True
    
    # 使用 psutil（如果可用）
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    process_name = process.name()
                    process_cmdline = ' '.join(process.cmdline())
                    
                    # 只关闭 Python 运行的 db_audit.py 进程
                    if 'python' in process_name.lower() and 'db_audit.py' in process_cmdline:
                        print(f"[INFO] Found existing audit server on port {port} (PID: {conn.pid})")
                        print(f"[INFO] Terminating old process...")
                        process.terminate()
                        process.wait(timeout=3)
                        print(f"[OK] Old process terminated successfully")
                        return True
                    else:
                        print(f"[WARNING] Port {port} is used by another application: {process_name}")
                        return False
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
                    print(f"[WARNING] Could not terminate process: {e}")
                    return False
    except Exception as e:
        print(f"[WARNING] Error checking port: {e}")
    return True

def is_port_open(port: int) -> bool:
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('', port))
        sock.close()
        return True
    except:
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MC L10n Database Audit Tool")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Server port')
    parser.add_argument('--host', default=DEFAULT_HOST, help='Server host')
    parser.add_argument('--db', type=str, help='Database file path')
    
    args = parser.parse_args()
    
    global DB_PATH, PORT, HOST
    PORT = args.port
    HOST = args.host
    
    if args.db:
        DB_PATH = Path(args.db)
    
    print("="*60)
    print("         MC L10n Database Audit Tool v2.0.0")
    print("="*60)
    print(f"Database: {DB_PATH.name if DB_PATH else 'Not found'}")
    print(f"Path: {DB_PATH}")
    print(f"Web UI: http://{HOST}:{PORT}")
    print("="*60)
    print()
    
    if DB_PATH and DB_PATH.exists():
        # 获取数据库大小
        db_size = DB_PATH.stat().st_size / (1024 * 1024)  # MB
        print(f"[OK] Database found (Size: {db_size:.2f} MB)")
    else:
        print(f"[WARNING] Database file not found: {DB_PATH}")
        print("Please run MC L10n application first to generate database")
        print()
    
    # 检查并清理端口
    if not is_port_open(PORT):
        print(f"[INFO] Port {PORT} is already in use")
        if check_and_kill_port(PORT):
            import time
            time.sleep(1)  # 等待端口释放
            if is_port_open(PORT):
                print(f"[OK] Port {PORT} is now available")
            else:
                print(f"[ERROR] Port {PORT} is still in use")
                print(f"[INFO] Trying alternative port {PORT + 1}")
                PORT = PORT + 1
        else:
            print(f"[INFO] Trying alternative port {PORT + 1}")
            PORT = PORT + 1
    
    print(f"Starting server on port {PORT}...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == "__main__":
    main()