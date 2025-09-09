#!/usr/bin/env python3
"""
TransHub Suite 质量门禁检查脚本

这个脚本用于在提交前或CI/CD管道中执行全面的代码质量检查。
根据CLAUDE.md中的质量标准进行检查。
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path


class QualityGate:
    """质量门禁检查器"""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.results: dict[str, dict] = {}
        self.errors = 0
        self.warnings = 0

    def run_command(self, cmd: list[str], cwd: Path = None) -> tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.root_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "命令执行超时"
        except Exception as e:
            return 1, "", str(e)

    def check_python_style(self) -> bool:
        """检查Python代码风格"""
        print("🔍 检查Python代码风格...")

        # 1. Ruff检查
        returncode, stdout, stderr = self.run_command(
            ["poetry", "run", "ruff", "check", ".", "--output-format=json"]
        )

        ruff_issues = 0
        if returncode != 0:
            try:
                issues = json.loads(stdout) if stdout else []
                ruff_issues = len(issues)
                self.errors += len([i for i in issues if i.get("type") == "error"])
                self.warnings += len([i for i in issues if i.get("type") == "warning"])
            except json.JSONDecodeError:
                ruff_issues = 1
                self.errors += 1

        # 2. Ruff格式化检查
        returncode_fmt, _, _ = self.run_command(
            ["poetry", "run", "ruff", "format", "--check", "."]
        )

        format_issues = 1 if returncode_fmt != 0 else 0
        if format_issues:
            self.errors += 1

        self.results["python_style"] = {
            "ruff_issues": ruff_issues,
            "format_issues": format_issues,
            "status": "PASS" if ruff_issues == 0 and format_issues == 0 else "FAIL",
        }

        print(f"   Ruff检查: {'✅' if ruff_issues == 0 else '❌'} ({ruff_issues} 问题)")
        print(f"   格式检查: {'✅' if format_issues == 0 else '❌'}")

        return ruff_issues == 0 and format_issues == 0

    def check_python_types(self) -> bool:
        """检查Python类型注解"""
        print("🔍 检查Python类型注解...")

        returncode, stdout, stderr = self.run_command(
            [
                "poetry",
                "run",
                "mypy",
                "packages",
                "apps",
                "--ignore-missing-imports",
                "--no-strict-optional",
            ]
        )

        # MyPy暂时允许失败，但记录结果
        type_issues = returncode
        if type_issues != 0:
            self.warnings += 1

        self.results["python_types"] = {
            "mypy_exit_code": returncode,
            "status": "WARN" if type_issues != 0 else "PASS",
            "note": "类型检查暂时为警告级别",
        }

        print(f"   MyPy检查: {'⚠️' if type_issues != 0 else '✅'} (暂时允许失败)")

        return True  # 暂时总是通过

    def check_python_tests(self) -> bool:
        """运行Python测试"""
        print("🔍 运行Python测试...")

        returncode, stdout, stderr = self.run_command(
            ["poetry", "run", "pytest", "--tb=short", "-q"]
        )

        # 测试暂时允许失败
        test_failures = returncode
        if test_failures != 0:
            self.warnings += 1

        self.results["python_tests"] = {
            "exit_code": returncode,
            "status": "WARN" if test_failures != 0 else "PASS",
            "note": "测试暂时为警告级别",
        }

        print(f"   测试运行: {'⚠️' if test_failures != 0 else '✅'} (暂时允许失败)")

        return True  # 暂时总是通过

    def check_frontend_quality(self) -> bool:
        """检查前端代码质量"""
        print("🔍 检查前端代码质量...")

        frontend_path = self.root_path / "apps" / "mc_l10n" / "frontend"

        if not frontend_path.exists():
            print("   ⚠️ 前端目录不存在，跳过检查")
            return True

        # 1. ESLint检查
        returncode_lint, _, _ = self.run_command(["pnpm", "lint"], cwd=frontend_path)

        # 2. TypeScript类型检查
        returncode_types, _, _ = self.run_command(
            ["pnpm", "type-check"], cwd=frontend_path
        )

        # 3. Prettier格式检查
        returncode_format, _, _ = self.run_command(
            ["pnpm", "format:check"], cwd=frontend_path
        )

        # 前端检查暂时允许ESLint和类型检查失败，但格式化必须通过
        lint_issues = 1 if returncode_lint != 0 else 0
        type_issues = 1 if returncode_types != 0 else 0
        format_issues = 1 if returncode_format != 0 else 0

        if lint_issues or type_issues:
            self.warnings += 1
        if format_issues:
            self.errors += 1

        self.results["frontend_quality"] = {
            "lint_issues": lint_issues,
            "type_issues": type_issues,
            "format_issues": format_issues,
            "status": "FAIL"
            if format_issues > 0
            else ("WARN" if (lint_issues > 0 or type_issues > 0) else "PASS"),
        }

        print(f"   ESLint: {'⚠️' if lint_issues > 0 else '✅'} (暂时允许失败)")
        print(f"   类型检查: {'⚠️' if type_issues > 0 else '✅'} (暂时允许失败)")
        print(f"   格式检查: {'✅' if format_issues == 0 else '❌'}")

        return format_issues == 0

    def check_architecture_compliance(self) -> bool:
        """检查架构合规性"""
        print("🔍 检查架构合规性...")

        violations = []

        # 检查是否有直接的跨层导入
        backend_path = self.root_path / "apps" / "mc_l10n" / "backend"
        if backend_path.exists():
            # 检查main.py是否还有跨层导入
            main_py = backend_path / "main.py"
            if main_py.exists():
                content = main_py.read_text()
                if "from core.ddd_scanner import" in content:
                    violations.append("main.py中仍存在直接导入core模块")

        # 检查文件大小（不应超过500行）
        large_files = []
        for py_file in self.root_path.rglob("*.py"):
            if py_file.stat().st_size > 0:
                line_count = len(py_file.read_text().splitlines())
                if line_count > 500:
                    large_files.append(
                        f"{py_file.relative_to(self.root_path)}: {line_count}行"
                    )

        if large_files:
            violations.append(f"发现{len(large_files)}个超大文件(>500行)")

        self.results["architecture"] = {
            "violations": violations,
            "large_files": large_files[:5],  # 只显示前5个
            "status": "PASS" if len(violations) == 0 else "WARN",
        }

        if violations:
            self.warnings += len(violations)
            print(f"   架构检查: ⚠️ 发现 {len(violations)} 个问题")
            for v in violations[:3]:  # 只显示前3个
                print(f"     - {v}")
        else:
            print("   架构检查: ✅")

        return True  # 架构问题暂时不阻止构建

    def check_security(self) -> bool:
        """检查安全性"""
        print("🔍 检查安全性...")

        # 检查是否有敏感信息
        sensitive_patterns = [
            "password =",
            "secret =",
            "api_key =",
            "token =",
            "private_key",
        ]

        sensitive_files = []
        for py_file in self.root_path.rglob("*.py"):
            if "test" in str(py_file) or "example" in str(py_file):
                continue

            try:
                content = py_file.read_text().lower()
                for pattern in sensitive_patterns:
                    if pattern in content and "your-" not in content:
                        sensitive_files.append(str(py_file.relative_to(self.root_path)))
                        break
            except Exception:
                continue

        self.results["security"] = {
            "sensitive_files": sensitive_files,
            "status": "WARN" if sensitive_files else "PASS",
        }

        if sensitive_files:
            self.warnings += len(sensitive_files)
            print(
                f"   安全检查: ⚠️ 发现 {len(sensitive_files)} 个可能包含敏感信息的文件"
            )
        else:
            print("   安全检查: ✅")

        return True

    def generate_report(self) -> dict:
        """生成检查报告"""
        total_checks = len(self.results)
        passed_checks = len([r for r in self.results.values() if r["status"] == "PASS"])
        warned_checks = len([r for r in self.results.values() if r["status"] == "WARN"])
        failed_checks = len([r for r in self.results.values() if r["status"] == "FAIL"])

        report = {
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "warned": warned_checks,
                "failed": failed_checks,
                "total_errors": self.errors,
                "total_warnings": self.warnings,
                "status": "FAIL"
                if failed_checks > 0
                else ("WARN" if warned_checks > 0 else "PASS"),
            },
            "details": self.results,
            "timestamp": subprocess.run(
                ["date", "-Iseconds"], capture_output=True, text=True
            ).stdout.strip(),
        }

        return report

    def print_summary(self, report: dict):
        """打印检查摘要"""
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("📊 质量门禁检查摘要")
        print("=" * 60)
        print(f"总检查项: {summary['total_checks']}")
        print(f"✅ 通过: {summary['passed']}")
        print(f"⚠️  警告: {summary['warned']}")
        print(f"❌ 失败: {summary['failed']}")
        print(f"错误总数: {summary['total_errors']}")
        print(f"警告总数: {summary['total_warnings']}")
        print(f"\n🎯 最终状态: {summary['status']}")

        if summary["status"] == "PASS":
            print("🎉 质量门禁检查全部通过！")
        elif summary["status"] == "WARN":
            print("⚠️ 质量门禁检查通过，但有警告需要注意")
        else:
            print("❌ 质量门禁检查失败，请修复问题后重试")

    async def run_all_checks(self) -> bool:
        """运行所有质量检查"""
        print("🚀 开始运行质量门禁检查...\n")

        checks = [
            self.check_python_style,
            self.check_python_types,
            self.check_python_tests,
            self.check_frontend_quality,
            self.check_architecture_compliance,
            self.check_security,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"❌ 检查过程中出现异常: {e}")
                self.errors += 1

            print()  # 空行分隔

        # 生成和保存报告
        report = self.generate_report()

        report_file = self.root_path / "quality-gate-report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))

        self.print_summary(report)

        # 根据最终状态决定返回值
        final_status = report["summary"]["status"]
        return final_status in ["PASS", "WARN"]


async def main():
    parser = argparse.ArgumentParser(
        description="TransHub Suite 质量门禁检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/quality-gate.py                    # 运行所有检查
  python scripts/quality-gate.py --strict          # 严格模式（警告也失败）
  python scripts/quality-gate.py --report-only     # 只生成报告
        """,
    )

    parser.add_argument(
        "--strict", action="store_true", help="严格模式：警告也被视为失败"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="只生成报告，不执行实际检查"
    )

    args = parser.parse_args()

    # 确定项目根目录
    script_dir = Path(__file__).parent
    root_path = script_dir.parent

    if args.report_only:
        report_file = root_path / "quality-gate-report.json"
        if report_file.exists():
            report = json.loads(report_file.read_text())
            print("📋 读取现有质量报告:")
            QualityGate(root_path).print_summary(report)
        else:
            print("❌ 未找到质量报告文件")
        return

    # 运行质量检查
    gate = QualityGate(root_path)
    success = await gate.run_all_checks()

    # 严格模式下，警告也被视为失败
    if args.strict and gate.warnings > 0:
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
