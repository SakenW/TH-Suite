#!/usr/bin/env python3
"""
数据导入脚本
用于导入JSONL格式的测试数据
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def import_metadata(file_path: str):
    """导入模组元数据"""
    db_path = Path(".artifacts/db/test_mc_l10n.db")

    if not db_path.exists():
        print("错误: 数据库不存在，请先运行setup步骤")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    imported_count = 0

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    mod_data = data["data"]

                    # 检查是否已存在
                    cursor.execute(
                        "SELECT id FROM mods WHERE id = ?", (mod_data["mod_id"],)
                    )

                    if not cursor.fetchone():
                        # 插入模组数据
                        cursor.execute(
                            """
                            INSERT INTO mods (
                                id, name, version, description, author,
                                loader, mc_version, file_path, file_size, sha256
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                mod_data["mod_id"],
                                mod_data["name"],
                                mod_data["version"],
                                mod_data["description"],
                                mod_data["author"],
                                mod_data["loader"],
                                mod_data["mc_version"],
                                mod_data["file_path"],
                                mod_data["file_size"],
                                mod_data["sha256"],
                            ),
                        )

                        imported_count += 1

        conn.commit()
        print(f"成功导入 {imported_count} 个模组元数据")
        return True

    except Exception as e:
        print(f"导入失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def import_language_entries(file_path: str):
    """导入语言条目"""
    db_path = Path(".artifacts/db/test_mc_l10n.db")

    if not db_path.exists():
        print("错误: 数据库不存在，请先运行setup步骤")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    imported_count = 0

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entry_data = data["data"]

                    # 插入语言条目
                    cursor.execute(
                        """
                        INSERT INTO language_entries (
                            mod_id, key, source_text, source_lang,
                            file_path, line_number, context, category, translatable, translated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            entry_data["mod_id"],
                            entry_data["key"],
                            entry_data["source_text"],
                            entry_data["source_lang"],
                            entry_data["file_path"],
                            entry_data["line_number"],
                            entry_data["context"],
                            entry_data["category"],
                            entry_data["translatable"],
                            entry_data["translated"],
                        ),
                    )

                    imported_count += 1

        conn.commit()
        print(f"成功导入 {imported_count} 个语言条目")
        return True

    except Exception as e:
        print(f"导入失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def import_translation_requests(file_path: str):
    """导入翻译请求"""
    db_path = Path(".artifacts/db/test_mc_l10n.db")

    if not db_path.exists():
        print("错误: 数据库不存在，请先运行setup步骤")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    imported_count = 0

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    trans_data = data["data"]

                    # 获取entry_id
                    cursor.execute(
                        "SELECT id FROM language_entries WHERE key = ? AND mod_id = ?",
                        (
                            trans_data["entry_id"].split("-")[-1],
                            trans_data["entry_id"].split("-")[1],
                        ),
                    )
                    result = cursor.fetchone()

                    if result:
                        entry_id = result[0]

                        # 插入翻译请求
                        cursor.execute(
                            """
                            INSERT INTO translation_requests (
                                entry_id, source_lang, target_lang,
                                source_text, translated_text, translator,
                                confidence, status, reviewed
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                entry_id,
                                trans_data["source_lang"],
                                trans_data["target_lang"],
                                trans_data["source_text"],
                                trans_data["translated_text"],
                                trans_data["translator"],
                                trans_data["confidence"],
                                trans_data["status"],
                                trans_data["reviewed"],
                            ),
                        )

                        imported_count += 1

        conn.commit()
        print(f"成功导入 {imported_count} 个翻译请求")
        return True

    except Exception as e:
        print(f"导入失败: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="导入测试数据")
    parser.add_argument(
        "--type",
        choices=["metadata", "language_entries", "translation_requests"],
        required=True,
    )
    parser.add_argument("--file", required=True, help="JSONL文件路径")

    args = parser.parse_args()

    if args.type == "metadata":
        success = import_metadata(args.file)
    elif args.type == "language_entries":
        success = import_language_entries(args.file)
    elif args.type == "translation_requests":
        success = import_translation_requests(args.file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
