#!/usr/bin/env python3
"""
扫描管理工具
管理和监控扫描任务
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import argparse
from datetime import datetime


class ScanManager:
    """扫描管理器"""
    
    def __init__(self, api_url: str = "http://localhost:18000"):
        self.api_url = api_url
        self.session = requests.Session()
    
    def start_scan(self, directory: str, incremental: bool = True) -> Optional[str]:
        """启动扫描"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/scan-project",
                json={"directory": directory, "incremental": incremental}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    scan_id = data.get("scan_id") or data.get("job_id")
                    print(f"✅ 扫描已启动: {scan_id}")
                    print(f"   目录: {directory}")
                    print(f"   模式: {'增量' if incremental else '全量'}")
                    return scan_id
                else:
                    print(f"❌ 启动失败: {data.get('error', {}).get('message', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return None
    
    def get_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/scan-status/{scan_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data")
            
        except Exception as e:
            print(f"获取状态失败: {e}")
        
        return None
    
    def monitor_scan(self, scan_id: str, interval: int = 2):
        """监控扫描进度"""
        print(f"\n📊 监控扫描进度: {scan_id}")
        print("-" * 50)
        
        last_progress = -1
        
        while True:
            status = self.get_status(scan_id)
            
            if not status:
                print("\n❌ 无法获取扫描状态")
                break
            
            progress = status.get("progress", 0)
            scan_status = status.get("status", "unknown")
            
            # 只在进度变化时更新
            if progress != last_progress:
                processed = status.get("processed_files", 0)
                total = status.get("total_files", 0)
                current_file = status.get("current_file", "")
                
                # 显示进度条
                bar_length = 30
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                print(f"\r[{bar}] {progress:.1f}% ({processed}/{total}) {current_file[:30]}", end="")
                last_progress = progress
            
            if scan_status == "completed":
                print("\n✅ 扫描完成!")
                self._print_statistics(status.get("statistics", {}))
                break
            elif scan_status == "failed":
                print("\n❌ 扫描失败!")
                if status.get("error"):
                    print(f"   错误: {status['error']}")
                break
            elif scan_status == "cancelled":
                print("\n⚠️ 扫描已取消")
                break
            
            time.sleep(interval)
    
    def _print_statistics(self, stats: Dict[str, Any]):
        """打印统计信息"""
        print("\n📈 扫描统计:")
        print(f"   模组数量: {stats.get('total_mods', 0)}")
        print(f"   语言文件: {stats.get('total_language_files', 0)}")
        print(f"   翻译键数: {stats.get('total_keys', 0)}")
    
    def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/scan-cancel/{scan_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ 扫描已取消: {scan_id}")
                    return True
                else:
                    print(f"❌ 取消失败: {data.get('message', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return False
    
    def list_active_scans(self):
        """列出活跃的扫描"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/scans/active"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    scans = data.get("data", [])
                    
                    if scans:
                        print("\n📋 活跃的扫描任务:")
                        print("-" * 60)
                        
                        for scan in scans:
                            print(f"ID: {scan['id']}")
                            print(f"  状态: {scan['status']}")
                            print(f"  进度: {scan['progress']:.1f}%")
                            print(f"  文件: {scan['processed_files']}/{scan['total_files']}")
                            print(f"  开始时间: {scan.get('started_at', 'N/A')}")
                            print("-" * 60)
                    else:
                        print("没有活跃的扫描任务")
        
        except Exception as e:
            print(f"获取活跃扫描失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MC L10n 扫描管理工具')
    parser.add_argument('--api', default='http://localhost:18000', help='API服务地址')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 启动扫描
    start_parser = subparsers.add_parser('start', help='启动扫描')
    start_parser.add_argument('directory', help='要扫描的目录')
    start_parser.add_argument('--full', action='store_true', help='全量扫描（默认增量）')
    start_parser.add_argument('--monitor', action='store_true', help='监控进度')
    
    # 监控扫描
    monitor_parser = subparsers.add_parser('monitor', help='监控扫描进度')
    monitor_parser.add_argument('scan_id', help='扫描ID')
    
    # 取消扫描
    cancel_parser = subparsers.add_parser('cancel', help='取消扫描')
    cancel_parser.add_argument('scan_id', help='扫描ID')
    
    # 列出活跃扫描
    subparsers.add_parser('list', help='列出活跃的扫描')
    
    # 获取状态
    status_parser = subparsers.add_parser('status', help='获取扫描状态')
    status_parser.add_argument('scan_id', help='扫描ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = ScanManager(args.api)
    
    if args.command == 'start':
        scan_id = manager.start_scan(args.directory, not args.full)
        if scan_id and args.monitor:
            manager.monitor_scan(scan_id)
    
    elif args.command == 'monitor':
        manager.monitor_scan(args.scan_id)
    
    elif args.command == 'cancel':
        manager.cancel_scan(args.scan_id)
    
    elif args.command == 'list':
        manager.list_active_scans()
    
    elif args.command == 'status':
        status = manager.get_status(args.scan_id)
        if status:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print("无法获取扫描状态")


if __name__ == '__main__':
    main()