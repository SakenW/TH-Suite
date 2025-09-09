"""
MC L10n SDK 使用示例
演示如何使用客户端SDK进行各种操作
"""

import asyncio
import logging

from .client_sdk import (
    MCL10nAPIError,
    MCL10nConnectionError,
    create_async_client,
    create_client,
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def basic_example():
    """基础使用示例"""
    print("=== 基础使用示例 ===")

    # 创建客户端
    with create_client("http://localhost:18000") as client:
        try:
            # 检查服务器状态
            if not client.is_server_available():
                print("❌ 服务器不可用")
                return

            print("✅ 服务器连接正常")

            # 获取系统状态
            status = client.get_system_status()
            print(f"系统状态: {status['status']}")
            print(f"可用功能: {list(status['features'].keys())}")

        except MCL10nConnectionError as e:
            print(f"❌ 连接失败: {e}")
        except MCL10nAPIError as e:
            print(f"❌ API错误: {e}")


def scan_example():
    """扫描示例"""
    print("\n=== 扫描示例 ===")

    with create_client() as client:
        try:
            # 快速扫描
            scan_path = "/path/to/minecraft/mods"  # 替换为实际路径
            print(f"快速扫描: {scan_path}")

            quick_stats = client.quick_scan(scan_path)
            if "error" in quick_stats:
                print(f"❌ 快速扫描失败: {quick_stats['error']}")
                return

            print(f"发现 {quick_stats['total_mods']} 个模组")
            print(f"支持语言: {quick_stats['languages']}")

            # 完整扫描（如果需要）
            if quick_stats["total_mods"] > 0:
                print("\n执行完整扫描...")
                scan_result = client.scan_mods(
                    path=scan_path,
                    recursive=True,
                    auto_extract=True,
                )

                if scan_result.success:
                    print("✅ 扫描成功:")
                    print(f"   - 处理文件: {scan_result.total_files}")
                    print(f"   - 发现模组: {scan_result.mods_found}")
                    print(f"   - 找到翻译: {scan_result.translations_found}")
                    print(f"   - 耗时: {scan_result.duration:.2f}秒")
                else:
                    print("❌ 扫描失败:")
                    for error in scan_result.errors:
                        print(f"   - {error}")

        except Exception as e:
            print(f"❌ 扫描异常: {e}")


def translation_example():
    """翻译示例"""
    print("\n=== 翻译示例 ===")

    with create_client() as client:
        try:
            # 单模组翻译示例
            mod_id = "example_mod"  # 替换为实际的MOD ID
            language = "zh_cn"

            # 翻译数据
            translations = {
                "item.example.sword": "示例之剑",
                "block.example.ore": "示例矿石",
                "gui.example.title": "示例界面",
            }

            print(f"翻译模组: {mod_id} -> {language}")
            result = client.translate_mod(
                mod_id=mod_id,
                language=language,
                translations=translations,
                translator="example_user",
                auto_approve=True,
            )

            print("✅ 翻译完成:")
            print(f"   - 成功: {result.translated_count}")
            print(f"   - 失败: {result.failed_count}")
            print(f"   - 进度: {result.progress:.1f}%")

            # 检查翻译质量
            quality_report = client.check_quality(mod_id, language)
            print("\n📊 质量报告:")
            print(f"   - 总计: {quality_report.total_translations}")
            print(f"   - 通过率: {quality_report.approval_rate:.1f}%")
            print(f"   - 平均质量: {quality_report.average_quality:.2f}")
            print(f"   - 需要审核: {'是' if quality_report.needs_review else '否'}")

        except Exception as e:
            print(f"❌ 翻译异常: {e}")


def project_example():
    """项目管理示例"""
    print("\n=== 项目管理示例 ===")

    with create_client() as client:
        try:
            # 创建翻译项目
            project_name = "示例翻译项目"
            mod_ids = ["mod1", "mod2", "mod3"]  # 替换为实际的MOD ID
            target_languages = ["zh_cn", "ja_jp"]

            print(f"创建项目: {project_name}")
            project_id = client.create_project(
                name=project_name,
                mod_ids=mod_ids,
                target_languages=target_languages,
                auto_assign=True,
            )

            print(f"✅ 项目创建成功: {project_id}")

            # 获取项目状态
            project_info = client.get_project(project_id)
            print("\n📋 项目信息:")
            print(f"   - 名称: {project_info.name}")
            print(f"   - 状态: {project_info.status}")
            print(f"   - 进度: {project_info.progress}")
            print(f"   - 统计: {project_info.statistics}")

            if project_info.estimated_completion:
                print(f"   - 预计完成: {project_info.estimated_completion}")

        except Exception as e:
            print(f"❌ 项目管理异常: {e}")


def batch_operations_example():
    """批量操作示例"""
    print("\n=== 批量操作示例 ===")

    with create_client() as client:
        try:
            # 批量翻译多个模组
            mod_ids = ["mod1", "mod2", "mod3"]
            language = "zh_cn"

            print(f"批量翻译 {len(mod_ids)} 个模组...")
            results = client.batch_translate(
                mod_ids=mod_ids,
                language=language,
                quality_threshold=0.8,
            )

            print("✅ 批量翻译完成:")
            total_translated = sum(r.translated_count for r in results)
            avg_progress = sum(r.progress for r in results) / len(results)

            print(f"   - 总翻译数: {total_translated}")
            print(f"   - 平均进度: {avg_progress:.1f}%")

            # 显示每个模组的结果
            for result in results:
                print(f"   - {result.mod_id}: {result.translated_count} 条, {result.progress:.1f}%")

        except Exception as e:
            print(f"❌ 批量操作异常: {e}")


async def async_example():
    """异步操作示例"""
    print("\n=== 异步操作示例 ===")

    async with create_async_client() as client:
        try:
            # 并发扫描多个路径
            paths = [
                "/path/to/mods1",
                "/path/to/mods2",
                "/path/to/mods3",
            ]

            print("开始并发扫描...")
            tasks = [
                client.scan_mods(path, recursive=True, auto_extract=False)
                for path in paths
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            print("✅ 并发扫描完成:")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"   - 路径 {i+1}: ❌ {result}")
                else:
                    print(f"   - 路径 {i+1}: {result.mods_found} 个模组")

        except Exception as e:
            print(f"❌ 异步操作异常: {e}")


def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")

    # 测试连接错误
    try:
        with create_client("http://localhost:99999") as client:  # 错误端口
            client.get_system_status()
    except MCL10nConnectionError as e:
        print(f"✅ 正确捕获连接错误: {e}")

    # 测试API错误
    try:
        with create_client() as client:
            # 假设这个MOD不存在
            client.check_quality("nonexistent_mod", "zh_cn")
    except MCL10nAPIError as e:
        print(f"✅ 正确捕获API错误: {e.status_code} - {e}")


def complete_workflow_example():
    """完整工作流示例"""
    print("\n=== 完整工作流示例 ===")

    with create_client() as client:
        try:
            # 1. 检查系统状态
            print("1. 检查系统状态...")
            if not client.is_server_available():
                print("❌ 系统不可用")
                return

            # 2. 获取支持的语言
            print("2. 获取支持的语言...")
            languages = client.get_supported_languages()
            print(f"支持语言: {', '.join(languages)}")

            # 3. 扫描并翻译（一键操作）
            print("3. 执行一键扫描并翻译...")
            scan_path = "/path/to/mods"
            target_language = "zh_cn"

            workflow_result = client.scan_and_translate(
                path=scan_path,
                language=target_language,
                auto_approve=False,  # 需要手动审核
            )

            print(f"✅ 工作流完成: {workflow_result}")

            # 4. 同步到服务器（如果需要）
            print("4. 同步到服务器...")
            sync_result = client.sync_with_server()

            if sync_result.error_count == 0:
                print(f"✅ 同步成功: 同步了 {sync_result.synced_count} 项")
            else:
                print(f"⚠️ 同步部分失败: {sync_result.error_count} 个错误")

        except Exception as e:
            print(f"❌ 工作流异常: {e}")


def main():
    """运行所有示例"""
    print("🚀 MC L10n SDK 使用示例")
    print("=" * 50)

    # 运行同步示例
    basic_example()
    scan_example()
    translation_example()
    project_example()
    batch_operations_example()
    error_handling_example()
    complete_workflow_example()

    # 运行异步示例
    print("\n" + "=" * 50)
    asyncio.run(async_example())

    print("\n🎉 所有示例运行完成！")
    print("\n💡 提示:")
    print("- 请替换示例中的路径和ID为实际值")
    print("- 确保MC L10n服务器正在运行")
    print("- 查看client_sdk.py了解更多API")


if __name__ == "__main__":
    main()
