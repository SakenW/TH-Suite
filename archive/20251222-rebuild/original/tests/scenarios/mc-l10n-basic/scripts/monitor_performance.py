#!/usr/bin/env python3
"""
性能监控脚本
用于收集和记录TH-Suite运行时的性能指标
"""

import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, output_dir: str = ".artifacts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 性能数据
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "duration": None,
            "memory_peak": 0,
            "memory_current": 0,
            "cpu_percent": [],
            "disk_io": {"read_bytes": 0, "write_bytes": 0},
            "network_io": {"bytes_sent": 0, "bytes_recv": 0},
            "step_metrics": {},
        }

        # 监控状态
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self):
        """开始监控"""
        self.metrics["start_time"] = time.time()
        self.monitoring = True

        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        print(f"[{datetime.now().isoformat()}] 性能监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.metrics["end_time"] = time.time()
        self.metrics["duration"] = self.metrics["end_time"] - self.metrics["start_time"]

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

        print(f"[{datetime.now().isoformat()}] 性能监控已停止")

    def record_step_metric(self, step_name: str, metric_name: str, value: float):
        """记录步骤指标"""
        if step_name not in self.metrics["step_metrics"]:
            self.metrics["step_metrics"][step_name] = {}

        self.metrics["step_metrics"][step_name][metric_name] = value

    def _monitor_loop(self):
        """监控循环"""
        process = psutil.Process()

        # 获取初始IO计数
        io_before = process.io_counters()
        net_before = psutil.net_io_counters()

        while self.monitoring:
            try:
                # 内存使用
                memory_info = process.memory_info()
                self.metrics["memory_current"] = memory_info.rss / 1024 / 1024  # MB
                self.metrics["memory_peak"] = max(
                    self.metrics["memory_peak"], self.metrics["memory_current"]
                )

                # CPU使用率
                cpu_percent = process.cpu_percent(interval=0.1)
                self.metrics["cpu_percent"].append(cpu_percent)

                # 磁盘IO
                io_after = process.io_counters()
                self.metrics["disk_io"]["read_bytes"] = (
                    io_after.read_bytes - io_before.read_bytes
                )
                self.metrics["disk_io"]["write_bytes"] = (
                    io_after.write_bytes - io_before.write_bytes
                )

                # 网络IO
                net_after = psutil.net_io_counters()
                self.metrics["network_io"]["bytes_sent"] = (
                    net_after.bytes_sent - net_before.bytes_sent
                )
                self.metrics["network_io"]["bytes_recv"] = (
                    net_after.bytes_recv - net_before.bytes_recv
                )

                time.sleep(0.5)  # 每0.5秒采集一次

            except Exception as e:
                print(f"监控错误: {e}", file=sys.stderr)

    def get_summary(self) -> dict:
        """获取性能摘要"""
        avg_cpu = (
            sum(self.metrics["cpu_percent"]) / len(self.metrics["cpu_percent"])
            if self.metrics["cpu_percent"]
            else 0
        )

        return {
            "duration": {
                "total": f"{self.metrics['duration']:.2f}s"
                if self.metrics["duration"]
                else "N/A",
                "start": datetime.fromtimestamp(self.metrics["start_time"]).isoformat()
                if self.metrics["start_time"]
                else None,
                "end": datetime.fromtimestamp(self.metrics["end_time"]).isoformat()
                if self.metrics["end_time"]
                else None,
            },
            "memory": {
                "peak": f"{self.metrics['memory_peak']:.2f}MB",
                "current": f"{self.metrics['memory_current']:.2f}MB",
            },
            "cpu": {
                "average": f"{avg_cpu:.1f}%",
                "samples": len(self.metrics["cpu_percent"]),
            },
            "disk_io": {
                "read": f"{self.metrics['disk_io']['read_bytes'] / 1024 / 1024:.2f}MB",
                "write": f"{self.metrics['disk_io']['write_bytes'] / 1024 / 1024:.2f}MB",
            },
            "network_io": {
                "sent": f"{self.metrics['network_io']['bytes_sent'] / 1024:.2f}KB",
                "recv": f"{self.metrics['network_io']['bytes_recv'] / 1024:.2f}KB",
            },
        }

    def save_metrics(self, format: str = "json"):
        """保存性能指标"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            # JSON格式
            output_file = self.output_dir / f"performance_{timestamp}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        elif format == "prometheus":
            # Prometheus格式
            output_file = self.output_dir / f"metrics_{timestamp}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                # 持续时间
                if self.metrics["duration"]:
                    f.write(
                        "# HELP th_suite_duration_seconds Total scenario duration\n"
                    )
                    f.write("# TYPE th_suite_duration_seconds gauge\n")
                    f.write(f"th_suite_duration_seconds {self.metrics['duration']}\n\n")

                # 内存峰值
                f.write("# HELP th_suite_memory_peak_bytes Memory peak usage\n")
                f.write("# TYPE th_suite_memory_peak_bytes gauge\n")
                f.write(
                    f"th_suite_memory_peak_bytes {int(self.metrics['memory_peak'] * 1024 * 1024)}\n\n"
                )

                # CPU平均使用率
                if self.metrics["cpu_percent"]:
                    avg_cpu = sum(self.metrics["cpu_percent"]) / len(
                        self.metrics["cpu_percent"]
                    )
                    f.write("# HELP th_suite_cpu_percent_average Average CPU usage\n")
                    f.write("# TYPE th_suite_cpu_percent_average gauge\n")
                    f.write(f"th_suite_cpu_percent_average {avg_cpu}\n\n")

        print(f"性能指标已保存到: {output_file}")

    def print_summary(self):
        """打印性能摘要"""
        summary = self.get_summary()

        print("\n" + "=" * 50)
        print("性能监控摘要")
        print("=" * 50)

        print("\n[时间]")
        print(f"  开始时间: {summary['duration']['start']}")
        print(f"  结束时间: {summary['duration']['end']}")
        print(f"  总耗时: {summary['duration']['total']}")

        print("\n[内存]")
        print(f"  峰值使用: {summary['memory']['peak']}")
        print(f"  当前使用: {summary['memory']['current']}")

        print("\n[CPU]")
        print(f"  平均使用率: {summary['cpu']['average']}")
        print(f"  采样次数: {summary['cpu']['samples']}")

        print("\n[磁盘IO]")
        print(f"  读取: {summary['disk_io']['read']}")
        print(f"  写入: {summary['disk_io']['write']}")

        print("\n[网络IO]")
        print(f"  发送: {summary['network_io']['sent']}")
        print(f"  接收: {summary['network_io']['recv']}")

        # 步骤指标
        if self.metrics["step_metrics"]:
            print("\n[步骤指标]")
            for step, metrics in self.metrics["step_metrics"].items():
                print(f"  {step}:")
                for name, value in metrics.items():
                    print(f"    {name}: {value}")

        print("\n" + "=" * 50)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="TH-Suite 性能监控工具")
    parser.add_argument("--output-dir", default=".artifacts", help="输出目录")
    parser.add_argument(
        "--format", choices=["json", "prometheus"], default="json", help="输出格式"
    )
    parser.add_argument("--duration", type=int, help="监控时长（秒）")

    args = parser.parse_args()

    # 创建监控器
    monitor = PerformanceMonitor(args.output_dir)

    try:
        # 开始监控
        monitor.start_monitoring()

        if args.duration:
            # 定时监控
            time.sleep(args.duration)
        else:
            # 交互式监控
            print("按 Ctrl+C 停止监控...")
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        # 停止监控
        monitor.stop_monitoring()

        # 输出结果
        monitor.print_summary()
        monitor.save_metrics(args.format)


if __name__ == "__main__":
    main()
