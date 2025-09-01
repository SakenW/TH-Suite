# tests/conftest.py
"""
pytest配置文件

提供测试所需的公共fixture和配置
"""

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

# 添加src目录到Python路径
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def sample_fabric_mod():
    """创建示例Fabric MOD文件"""
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "sample_fabric_mod.jar"

        with zipfile.ZipFile(mod_path, "w") as zip_file:
            # fabric.mod.json
            mod_info = {
                "schemaVersion": 1,
                "id": "sample_fabric_mod",
                "name": "Sample Fabric Mod",
                "version": "1.0.0",
                "description": "A sample Fabric mod for testing",
                "authors": ["TestAuthor"],
                "contact": {
                    "homepage": "https://example.com",
                    "sources": "https://github.com/example/sample",
                },
                "license": "MIT",
                "environment": "*",
                "depends": {"fabricloader": ">=0.14.0", "minecraft": "~1.19.2"},
            }
            zip_file.writestr("fabric.mod.json", json.dumps(mod_info, indent=2))

            # 语言文件
            en_us_lang = {
                "item.sample_fabric_mod.magic_wand": "Magic Wand",
                "item.sample_fabric_mod.fire_sword": "Fire Sword",
                "block.sample_fabric_mod.magic_ore": "Magic Ore",
                "block.sample_fabric_mod.enchanted_stone": "Enchanted Stone",
                "itemGroup.sample_fabric_mod.items": "Sample Mod Items",
                "gui.sample_fabric_mod.config.title": "Sample Mod Configuration",
                "tooltip.sample_fabric_mod.magic_wand": "A powerful magic wand",
                "message.sample_fabric_mod.spell_cast": "Spell cast successfully!",
            }

            zh_cn_lang = {
                "item.sample_fabric_mod.magic_wand": "魔法棒",
                "item.sample_fabric_mod.fire_sword": "火焰剑",
                "block.sample_fabric_mod.magic_ore": "魔法矿石",
                "block.sample_fabric_mod.enchanted_stone": "附魔石头",
                "itemGroup.sample_fabric_mod.items": "示例模组物品",
                "gui.sample_fabric_mod.config.title": "示例模组配置",
                "tooltip.sample_fabric_mod.magic_wand": "强大的魔法棒",
                "message.sample_fabric_mod.spell_cast": "法术施放成功！",
            }

            zip_file.writestr(
                "assets/sample_fabric_mod/lang/en_us.json",
                json.dumps(en_us_lang, indent=2),
            )
            zip_file.writestr(
                "assets/sample_fabric_mod/lang/zh_cn.json",
                json.dumps(zh_cn_lang, indent=2, ensure_ascii=False),
            )

            # 其他资源文件
            zip_file.writestr(
                "assets/sample_fabric_mod/models/item/magic_wand.json", "{}"
            )
            zip_file.writestr(
                "assets/sample_fabric_mod/textures/item/magic_wand.png",
                b"fake_png_data",
            )

        yield mod_path


@pytest.fixture
def sample_forge_mod():
    """创建示例Forge MOD文件"""
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "sample_forge_mod.jar"

        with zipfile.ZipFile(mod_path, "w") as zip_file:
            # mcmod.info
            mod_info = [
                {
                    "modid": "sample_forge_mod",
                    "name": "Sample Forge Mod",
                    "description": "A sample Forge mod for testing",
                    "version": "2.1.0",
                    "mcversion": "1.19.2",
                    "authorList": ["ForgeAuthor"],
                    "credits": "Thanks to the Forge team",
                    "logoFile": "",
                    "screenshots": [],
                    "dependencies": [],
                }
            ]
            zip_file.writestr("mcmod.info", json.dumps(mod_info, indent=2))

            # .lang语言文件
            en_us_lang = """item.sample_forge_mod.steel_sword.name=Steel Sword
item.sample_forge_mod.diamond_pickaxe.name=Enhanced Diamond Pickaxe
block.sample_forge_mod.steel_ore.name=Steel Ore
block.sample_forge_mod.compressed_cobblestone.name=Compressed Cobblestone
itemGroup.sample_forge_mod.items=Forge Sample Items
gui.sample_forge_mod.config.title=Forge Sample Configuration"""

            zh_cn_lang = """item.sample_forge_mod.steel_sword.name=钢铁剑
item.sample_forge_mod.diamond_pickaxe.name=强化钻石镐
block.sample_forge_mod.steel_ore.name=钢铁矿石
block.sample_forge_mod.compressed_cobblestone.name=压缩圆石
itemGroup.sample_forge_mod.items=Forge示例物品
gui.sample_forge_mod.config.title=Forge示例配置"""

            zip_file.writestr("assets/sample_forge_mod/lang/en_us.lang", en_us_lang)
            zip_file.writestr("assets/sample_forge_mod/lang/zh_cn.lang", zh_cn_lang)

        yield mod_path


@pytest.fixture
def sample_modpack_dir():
    """创建示例整合包目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        modpack_path = Path(temp_dir) / "sample_modpack"
        modpack_path.mkdir()

        # 创建manifest.json
        manifest = {
            "minecraft": {
                "version": "1.19.2",
                "modLoaders": [{"id": "fabric-0.14.21", "primary": True}],
            },
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "Sample Test Modpack",
            "version": "1.0.0",
            "author": "Test Author",
            "files": [],
        }

        manifest_file = modpack_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))

        # 创建mods目录
        mods_dir = modpack_path / "mods"
        mods_dir.mkdir()

        # 创建配置目录
        config_dir = modpack_path / "config"
        config_dir.mkdir()

        # 创建一些配置文件
        config_file = config_dir / "sample-config.json"
        config_file.write_text('{"enabled": true}')

        # 创建overrides目录
        overrides_dir = modpack_path / "overrides"
        overrides_dir.mkdir()

        yield modpack_path


@pytest.fixture
def mock_task_manager():
    """模拟任务管理器"""

    class MockTaskManager:
        def __init__(self):
            self.tasks = {}
            self.task_counter = 0

        async def submit_task(self, task_type: str, payload: dict):
            from uuid import uuid4

            task_id = uuid4()
            self.tasks[task_id] = {
                "type": task_type,
                "payload": payload,
                "status": "pending",
            }
            return task_id

        async def get_task_status(self, task_id):
            if task_id not in self.tasks:
                return None

            task = self.tasks[task_id]
            return type(
                "TaskStatus",
                (),
                {
                    "status": type("Status", (), {"value": task["status"]})(),
                    "progress": 0.5,
                    "current_step": "Processing",
                    "error_message": None,
                },
            )()

    return MockTaskManager()


@pytest.fixture
def clean_temp_files():
    """清理测试后的临时文件"""
    yield
    # 在测试后执行清理
    import gc

    gc.collect()
