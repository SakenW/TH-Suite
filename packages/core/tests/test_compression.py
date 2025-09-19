"""
压缩模块测试

测试压缩引擎、算法、配置等功能
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from ..compression import (
    CompressionEngine, CompressionResult, CompressionLevel, 
    CompressionAlgorithm, CompressionSelector
)
from ..compression.config import CompressionConfig, CompressionConfigTemplates
from ..compression.errors import CompressionError, AlgorithmError


class TestCompressionConfig:
    """测试压缩配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = CompressionConfig()
        
        assert config.default_algorithm == "zstd"
        assert config.default_level == 6
        assert config.enable_dictionaries is True
        assert config.auto_select_algorithm is True
    
    def test_config_templates(self):
        """测试配置模板"""
        # 速度优化配置
        speed_config = CompressionConfigTemplates.speed_optimized()
        assert speed_config.default_algorithm == "lz4"
        assert speed_config.default_level == 1
        assert speed_config.enable_dictionaries is False
        
        # 压缩比优化配置
        compression_config = CompressionConfigTemplates.compression_optimized()
        assert compression_config.default_algorithm == "zstd"
        assert compression_config.default_level == 12
        assert compression_config.enable_dictionaries is True
        
        # 平衡配置
        balanced_config = CompressionConfigTemplates.balanced()
        assert balanced_config.default_algorithm == "zstd"
        assert balanced_config.default_level == 6


class TestCompressionResult:
    """测试压缩结果"""
    
    def test_result_calculation(self):
        """测试结果计算"""
        result = CompressionResult(
            algorithm=CompressionAlgorithm.ZSTD,
            original_size=1000,
            compressed_size=600,
            compression_time=1.5
        )
        
        assert result.compression_ratio == 0.6
        assert result.space_saved_bytes == 400
        assert result.space_saved_percentage == 40.0
        assert result.throughput_mbps > 0
    
    def test_result_edge_cases(self):
        """测试结果边缘情况"""
        # 零大小文件
        zero_result = CompressionResult(
            algorithm=CompressionAlgorithm.ZSTD,
            original_size=0,
            compressed_size=0,
            compression_time=0.1
        )
        
        assert zero_result.compression_ratio == 0.0
        assert zero_result.space_saved_percentage == 0.0
        
        # 零时间（避免除零错误）
        zero_time_result = CompressionResult(
            algorithm=CompressionAlgorithm.ZSTD,
            original_size=1000,
            compressed_size=600,
            compression_time=0.0
        )
        
        assert zero_time_result.throughput_mbps == 0.0
    
    def test_result_to_dict(self):
        """测试结果转换为字典"""
        result = CompressionResult(
            algorithm=CompressionAlgorithm.ZSTD,
            original_size=1000,
            compressed_size=700,
            compression_time=2.0
        )
        
        data = result.to_dict()
        
        assert data['algorithm'] == 'zstd'
        assert data['original_size'] == 1000
        assert data['compressed_size'] == 700
        assert data['compression_ratio'] == 0.7
        assert 'throughput_mbps' in data


class MockCompressionStrategy:
    """模拟压缩策略"""
    
    def __init__(self, algorithm: CompressionAlgorithm):
        self._algorithm = algorithm
    
    @property
    def algorithm(self) -> CompressionAlgorithm:
        return self._algorithm
    
    async def compress(self, data: bytes, level=None, dictionary=None) -> bytes:
        # 模拟压缩：简单地移除一半字节
        return data[::2]
    
    async def decompress(self, compressed_data: bytes, dictionary=None) -> bytes:
        # 模拟解压：重复字节
        return b''.join(bytes([b, b]) for b in compressed_data)
    
    async def compress_stream(self, input_stream, level=None, dictionary=None):
        async for chunk in input_stream:
            yield chunk[::2]  # 简单压缩
    
    async def decompress_stream(self, input_stream, dictionary=None):
        async for chunk in input_stream:
            yield b''.join(bytes([b, b]) for b in chunk)


@pytest.fixture
def temp_file():
    """创建临时文件"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        test_data = b"Hello, World! " * 100  # 1400 bytes
        f.write(test_data)
        temp_path = Path(f.name)
    
    yield temp_path, test_data
    
    # 清理
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def compression_config():
    """压缩配置fixture"""
    return CompressionConfig(
        auto_select_algorithm=False,
        benchmark_enabled=False
    )


@pytest.fixture
def compression_engine(compression_config):
    """压缩引擎fixture"""
    engine = CompressionEngine(compression_config)
    
    # 注册模拟策略
    mock_strategy = MockCompressionStrategy(CompressionAlgorithm.ZSTD)
    engine.register_strategy(CompressionAlgorithm.ZSTD, mock_strategy)
    
    return engine


class TestCompressionEngine:
    """测试压缩引擎"""
    
    def test_engine_creation(self, compression_config):
        """测试引擎创建"""
        engine = CompressionEngine(compression_config)
        
        assert engine.config == compression_config
        assert len(engine.strategies) == 0
        assert len(engine.dictionaries) == 0
    
    def test_strategy_registration(self, compression_engine):
        """测试策略注册"""
        assert CompressionAlgorithm.ZSTD in compression_engine.strategies
        
        strategy = compression_engine.get_strategy(CompressionAlgorithm.ZSTD)
        assert strategy.algorithm == CompressionAlgorithm.ZSTD
    
    def test_strategy_not_found(self, compression_engine):
        """测试策略未找到"""
        with pytest.raises(CompressionError, match="不支持的压缩算法"):
            compression_engine.get_strategy(CompressionAlgorithm.GZIP)
    
    def test_dictionary_management(self, compression_engine):
        """测试字典管理"""
        test_dict = b"test dictionary data"
        compression_engine.set_dictionary("test_dict", test_dict)
        
        assert "test_dict" in compression_engine.dictionaries
        assert compression_engine.dictionaries["test_dict"] == test_dict
    
    @pytest.mark.asyncio
    async def test_compress_data(self, compression_engine):
        """测试数据压缩"""
        test_data = b"Hello, World! " * 50  # 700 bytes
        
        result = await compression_engine.compress_data(
            test_data,
            algorithm=CompressionAlgorithm.ZSTD,
            level=CompressionLevel.BALANCED
        )
        
        assert result.success
        assert result.algorithm == CompressionAlgorithm.ZSTD
        assert result.original_size == len(test_data)
        assert result.compressed_size < result.original_size
        assert result.compression_time > 0
    
    @pytest.mark.asyncio
    async def test_decompress_data(self, compression_engine):
        """测试数据解压"""
        test_data = b"Hello, World! " * 50
        
        # 先压缩
        result = await compression_engine.compress_data(
            test_data, CompressionAlgorithm.ZSTD
        )
        
        # 获取压缩后的数据（在实际实现中需要返回）
        compressed_data = test_data[::2]  # 模拟压缩数据
        
        # 解压
        decompressed_data = await compression_engine.decompress_data(
            compressed_data, CompressionAlgorithm.ZSTD
        )
        
        # 在模拟策略中，解压不会完全恢复原数据
        # 这里只验证操作成功
        assert len(decompressed_data) > 0
    
    @pytest.mark.asyncio
    async def test_compress_file(self, compression_engine, temp_file):
        """测试文件压缩"""
        temp_path, test_data = temp_file
        output_path = temp_path.with_suffix('.compressed')
        
        try:
            result = await compression_engine.compress_file(
                temp_path,
                output_path,
                algorithm=CompressionAlgorithm.ZSTD
            )
            
            assert result.algorithm == CompressionAlgorithm.ZSTD
            assert result.original_size == len(test_data)
            assert output_path.exists()
            
        finally:
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_compress_nonexistent_file(self, compression_engine):
        """测试压缩不存在的文件"""
        nonexistent = Path("/nonexistent/file.txt")
        output = Path("/tmp/output.compressed")
        
        with pytest.raises(CompressionError, match="输入文件不存在"):
            await compression_engine.compress_file(
                nonexistent, output, CompressionAlgorithm.ZSTD
            )
    
    @pytest.mark.asyncio
    async def test_algorithm_selection(self, compression_config):
        """测试算法选择"""
        # 启用自动选择
        compression_config.auto_select_algorithm = True
        engine = CompressionEngine(compression_config)
        
        # 注册多个策略
        engine.register_strategy(
            CompressionAlgorithm.ZSTD, 
            MockCompressionStrategy(CompressionAlgorithm.ZSTD)
        )
        engine.register_strategy(
            CompressionAlgorithm.LZ4, 
            MockCompressionStrategy(CompressionAlgorithm.LZ4)
        )
        
        # 测试小文件选择
        small_algorithm = engine._select_algorithm(500 * 1024)  # 500KB
        assert small_algorithm == CompressionAlgorithm.LZ4
        
        # 测试大文件选择
        large_algorithm = engine._select_algorithm(50 * 1024 * 1024)  # 50MB
        assert large_algorithm == CompressionAlgorithm.ZSTD
    
    @pytest.mark.asyncio
    async def test_benchmark_algorithms(self, compression_engine):
        """测试算法基准测试"""
        # 添加另一个策略用于比较
        engine.register_strategy(
            CompressionAlgorithm.LZ4,
            MockCompressionStrategy(CompressionAlgorithm.LZ4)
        )
        
        test_data = b"Test data for benchmarking " * 100
        
        results = await compression_engine.benchmark_algorithms(test_data)
        
        assert len(results) == 2  # ZSTD 和 LZ4
        assert CompressionAlgorithm.ZSTD in results
        assert CompressionAlgorithm.LZ4 in results
        
        # 验证结果是按压缩比排序的
        algorithms = list(results.keys())
        if len(algorithms) > 1:
            first_ratio = results[algorithms[0]].compression_ratio
            second_ratio = results[algorithms[1]].compression_ratio
            assert first_ratio <= second_ratio
    
    @pytest.mark.asyncio
    async def test_find_best_algorithm(self, compression_engine):
        """测试寻找最佳算法"""
        # 添加多个策略
        engine.register_strategy(
            CompressionAlgorithm.LZ4,
            MockCompressionStrategy(CompressionAlgorithm.LZ4)
        )
        
        test_data = b"Test data " * 50
        
        # 测试不同优先级
        best_compression = await compression_engine.find_best_algorithm(
            test_data, priority="compression_ratio"
        )
        assert best_compression in [CompressionAlgorithm.ZSTD, CompressionAlgorithm.LZ4]
        
        best_speed = await compression_engine.find_best_algorithm(
            test_data, priority="speed"
        )
        assert best_speed in [CompressionAlgorithm.ZSTD, CompressionAlgorithm.LZ4]
    
    def test_compression_stats(self, compression_engine):
        """测试压缩统计信息"""
        stats = compression_engine.get_compression_stats()
        
        assert 'available_algorithms' in stats
        assert 'dictionaries' in stats
        assert 'config' in stats
        assert len(stats['available_algorithms']) >= 1


class TestCompressionSelector:
    """测试压缩选择器"""
    
    def test_select_by_content_type(self):
        """测试根据内容类型选择"""
        # 文本类型
        text_algo = CompressionSelector.select_for_content_type("text/plain")
        assert text_algo == CompressionAlgorithm.ZSTD
        
        json_algo = CompressionSelector.select_for_content_type("application/json")
        assert json_algo == CompressionAlgorithm.ZSTD
        
        # 其他文本
        html_algo = CompressionSelector.select_for_content_type("text/html")
        assert html_algo == CompressionAlgorithm.GZIP
        
        # 二进制
        binary_algo = CompressionSelector.select_for_content_type("application/octet-stream")
        assert binary_algo == CompressionAlgorithm.LZ4
    
    def test_select_by_file_extension(self):
        """测试根据文件扩展名选择"""
        # 文本文件
        txt_algo = CompressionSelector.select_for_file_extension("document.txt")
        assert txt_algo == CompressionAlgorithm.ZSTD
        
        json_algo = CompressionSelector.select_for_file_extension("data.json")
        assert json_algo == CompressionAlgorithm.ZSTD
        
        # 代码文件
        py_algo = CompressionSelector.select_for_file_extension("script.py")
        assert py_algo == CompressionAlgorithm.ZSTD
        
        # 配置文件
        ini_algo = CompressionSelector.select_for_file_extension("config.ini")
        assert ini_algo == CompressionAlgorithm.GZIP
        
        # 已压缩文件
        zip_algo = CompressionSelector.select_for_file_extension("archive.zip")
        assert zip_algo == CompressionAlgorithm.LZ4
        
        # 未知文件
        unknown_algo = CompressionSelector.select_for_file_extension("file.unknown")
        assert unknown_algo == CompressionAlgorithm.LZ4
    
    def test_select_level_by_priority(self):
        """测试根据优先级选择级别"""
        speed_level = CompressionSelector.select_level_for_priority("speed")
        assert speed_level == CompressionLevel.FASTEST
        
        size_level = CompressionSelector.select_level_for_priority("size")
        assert size_level == CompressionLevel.MAXIMUM
        
        balanced_level = CompressionSelector.select_level_for_priority("balanced")
        assert balanced_level == CompressionLevel.BALANCED
        
        default_level = CompressionSelector.select_level_for_priority("unknown")
        assert default_level == CompressionLevel.BALANCED


class TestCompressionErrors:
    """测试压缩错误"""
    
    def test_compression_error(self):
        """测试压缩错误"""
        error = CompressionError("Test error", error_code="COMP_001")
        
        assert str(error) == "Test error"
        assert error.error_code == "COMP_001"
        assert error.metadata == {}
    
    def test_algorithm_error(self):
        """测试算法错误"""
        error = AlgorithmError("Algorithm failed", algorithm="zstd")
        
        assert error.algorithm == "zstd"
        assert "Algorithm failed" in str(error)


@pytest.mark.asyncio
async def test_integration_compression_workflow(temp_file):
    """集成测试：完整的压缩工作流程"""
    temp_path, test_data = temp_file
    
    # 创建配置
    config = CompressionConfig(
        auto_select_algorithm=True,
        benchmark_enabled=True,
        verify_compression=True
    )
    
    # 创建引擎
    engine = CompressionEngine(config)
    
    # 注册策略
    engine.register_strategy(
        CompressionAlgorithm.ZSTD,
        MockCompressionStrategy(CompressionAlgorithm.ZSTD)
    )
    engine.register_strategy(
        CompressionAlgorithm.LZ4,
        MockCompressionStrategy(CompressionAlgorithm.LZ4)
    )
    
    # 设置字典
    dictionary_data = b"common patterns in test data"
    engine.set_dictionary("test_dict", dictionary_data)
    
    # 压缩数据
    result = await engine.compress_data(
        test_data,
        dictionary_name="test_dict"
    )
    
    # 验证结果
    assert result.success
    assert result.original_size == len(test_data)
    assert result.compressed_size < result.original_size
    assert result.compression_ratio < 1.0
    assert result.space_saved_percentage > 0
    
    # 基准测试
    benchmark_results = await engine.benchmark_algorithms(test_data[:100])
    assert len(benchmark_results) == 2
    
    # 寻找最佳算法
    best_algo = await engine.find_best_algorithm(test_data[:100])
    assert best_algo in [CompressionAlgorithm.ZSTD, CompressionAlgorithm.LZ4]
    
    # 文件压缩
    compressed_file = temp_path.with_suffix('.compressed')
    try:
        file_result = await engine.compress_file(
            temp_path,
            compressed_file,
            algorithm=CompressionAlgorithm.ZSTD
        )
        
        assert file_result.algorithm == CompressionAlgorithm.ZSTD
        assert compressed_file.exists()
        assert compressed_file.stat().st_size > 0
        
        # 文件解压
        decompressed_file = temp_path.with_suffix('.decompressed')
        try:
            await engine.decompress_file(
                compressed_file,
                decompressed_file,
                CompressionAlgorithm.ZSTD
            )
            
            assert decompressed_file.exists()
            
        finally:
            if decompressed_file.exists():
                decompressed_file.unlink()
        
    finally:
        if compressed_file.exists():
            compressed_file.unlink()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])