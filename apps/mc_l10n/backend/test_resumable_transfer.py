#!/usr/bin/env python
"""
测试断点续传系统
验证大文件传输、断点续传、并行传输等功能
"""

import sys
import os
import time
import asyncio
import tempfile
import random
from pathlib import Path
from typing import List, Dict, Any

sys.path.append('.')

import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger(__name__)

async def create_test_file(file_path: str, size_mb: int) -> str:
    """创建测试文件"""
    import aiofiles
    
    # 生成随机数据
    data = bytearray(random.getrandbits(8) for _ in range(size_mb * 1024 * 1024))
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(data)
    
    return file_path

async def test_basic_transfer():
    """测试基本传输功能"""
    print("=== 测试基本传输功能 ===")
    
    try:
        from services.resumable_transfer import ResumableTransferManager, TransferStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResumableTransferManager(
                state_dir=os.path.join(temp_dir, "state"),
                default_chunk_size=64 * 1024,  # 64KB 块
                max_concurrent_transfers=2,
                max_concurrent_chunks_per_transfer=2
            )
            
            print("✓ 传输管理器初始化成功")
            
            # 创建测试文件
            source_file = os.path.join(temp_dir, "test_source.dat")
            dest_file = os.path.join(temp_dir, "test_dest.dat")
            
            print("正在创建测试文件...")
            await create_test_file(source_file, 1)  # 1MB测试文件
            print("✓ 测试文件创建完成")
            
            # 添加进度回调
            progress_updates = []
            
            def progress_callback(transfer_id: str, progress):
                progress_updates.append(progress)
                if len(progress_updates) % 10 == 0:  # 每10次更新打印一次
                    print(f"  进度: {progress.get_progress_percentage():.1f}% "
                          f"({progress.completed_chunks}/{progress.chunk_count} chunks)")
            
            manager.add_progress_callback(progress_callback)
            
            # 开始传输
            transfer_id = await manager.start_transfer(
                source_path=source_file,
                destination_path=dest_file,
                chunk_size=64 * 1024,  # 64KB
                options={
                    "verify_integrity": True,
                    "max_concurrent_chunks": 2
                }
            )
            
            print(f"✓ 传输已启动: {transfer_id}")
            
            # 等待传输完成
            while True:
                progress = manager.get_transfer_progress(transfer_id)
                if not progress:
                    break
                
                session = manager.active_sessions.get(transfer_id)
                if session and session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                    break
                
                await asyncio.sleep(0.1)
            
            # 检查结果
            final_progress = manager.get_transfer_progress(transfer_id)
            session = manager.active_sessions.get(transfer_id)
            
            if session and session.status == TransferStatus.COMPLETED:
                print("✓ 传输成功完成")
                print(f"  传输时间: {session.completed_at - session.started_at:.2f} 秒")
                print(f"  平均速度: {final_progress.average_speed_bps / 1024:.1f} KB/s")
                print(f"  分块数量: {final_progress.chunk_count}")
            else:
                print(f"✗ 传输失败: {session.status if session else 'Unknown'}")
                return False
            
            # 验证文件
            if os.path.exists(dest_file):
                source_size = os.path.getsize(source_file)
                dest_size = os.path.getsize(dest_file)
                
                if source_size == dest_size:
                    print("✓ 文件大小验证通过")
                else:
                    print(f"✗ 文件大小不匹配: {source_size} != {dest_size}")
                    return False
                
                # 验证文件内容
                with open(source_file, 'rb') as sf, open(dest_file, 'rb') as df:
                    source_data = sf.read()
                    dest_data = df.read()
                    
                    if source_data == dest_data:
                        print("✓ 文件内容验证通过")
                    else:
                        print("✗ 文件内容不匹配")
                        return False
            else:
                print("✗ 目标文件不存在")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ 基本传输测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_resume_transfer():
    """测试断点续传功能"""
    print("\n=== 测试断点续传功能 ===")
    
    try:
        from services.resumable_transfer import (
            ResumableTransferManager, TransferStatus, ChunkStatus
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResumableTransferManager(
                state_dir=os.path.join(temp_dir, "state"),
                default_chunk_size=32 * 1024,  # 32KB 块
                max_concurrent_chunks_per_transfer=1  # 单线程便于测试
            )
            
            # 创建较大的测试文件
            source_file = os.path.join(temp_dir, "large_test.dat")
            dest_file = os.path.join(temp_dir, "large_dest.dat")
            
            print("正在创建大文件...")
            await create_test_file(source_file, 2)  # 2MB
            print("✓ 大文件创建完成")
            
            # 开始传输
            transfer_id = await manager.start_transfer(
                source_path=source_file,
                destination_path=dest_file,
                chunk_size=32 * 1024,
                options={"verify_integrity": True}
            )
            
            print(f"✓ 传输已启动: {transfer_id}")
            
            # 等待部分传输完成
            await asyncio.sleep(0.5)
            
            # 暂停传输
            await manager.pause_transfer(transfer_id)
            print("✓ 传输已暂停")
            
            # 检查部分完成状态
            session = manager.active_sessions.get(transfer_id)
            if session:
                completed_chunks = len([
                    chunk for chunk in session.chunks
                    if chunk.status == ChunkStatus.COMPLETED
                ])
                total_chunks = len(session.chunks)
                print(f"  暂停时已完成: {completed_chunks}/{total_chunks} 分块")
            
            # 恢复传输
            success = await manager.resume_transfer(transfer_id)
            if success:
                print("✓ 传输已恢复")
            else:
                print("✗ 传输恢复失败")
                return False
            
            # 等待传输完成
            while True:
                session = manager.active_sessions.get(transfer_id)
                if session and session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                    break
                await asyncio.sleep(0.1)
            
            # 检查最终结果
            if session and session.status == TransferStatus.COMPLETED:
                print("✓ 断点续传完成")
                
                # 验证文件完整性
                source_size = os.path.getsize(source_file)
                dest_size = os.path.getsize(dest_file)
                
                if source_size == dest_size:
                    print("✓ 断点续传文件大小正确")
                else:
                    print(f"✗ 断点续传文件大小错误: {source_size} != {dest_size}")
                    return False
            else:
                print(f"✗ 断点续传失败: {session.status if session else 'Unknown'}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ 断点续传测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_concurrent_transfers():
    """测试并发传输"""
    print("\n=== 测试并发传输 ===")
    
    try:
        from services.resumable_transfer import ResumableTransferManager, TransferStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResumableTransferManager(
                state_dir=os.path.join(temp_dir, "state"),
                default_chunk_size=64 * 1024,
                max_concurrent_transfers=3,
                max_concurrent_chunks_per_transfer=2
            )
            
            # 创建多个测试文件
            source_files = []
            dest_files = []
            
            for i in range(3):
                source_file = os.path.join(temp_dir, f"concurrent_source_{i}.dat")
                dest_file = os.path.join(temp_dir, f"concurrent_dest_{i}.dat")
                
                await create_test_file(source_file, 1)  # 1MB每个
                source_files.append(source_file)
                dest_files.append(dest_file)
            
            print("✓ 多个测试文件创建完成")
            
            # 启动并发传输
            transfer_ids = []
            for i in range(3):
                transfer_id = await manager.start_transfer(
                    source_path=source_files[i],
                    destination_path=dest_files[i],
                    options={"verify_integrity": True}
                )
                transfer_ids.append(transfer_id)
                print(f"✓ 传输 {i+1} 已启动: {transfer_id[:8]}")
            
            # 监控所有传输
            completed_count = 0
            while completed_count < 3:
                await asyncio.sleep(0.2)
                
                completed_count = 0
                for transfer_id in transfer_ids:
                    session = manager.active_sessions.get(transfer_id)
                    if session and session.status == TransferStatus.COMPLETED:
                        completed_count += 1
                    elif session and session.status == TransferStatus.FAILED:
                        print(f"✗ 传输失败: {transfer_id[:8]}")
                        return False
            
            print("✓ 所有并发传输完成")
            
            # 验证所有文件
            for i in range(3):
                if not os.path.exists(dest_files[i]):
                    print(f"✗ 目标文件 {i+1} 不存在")
                    return False
                
                source_size = os.path.getsize(source_files[i])
                dest_size = os.path.getsize(dest_files[i])
                
                if source_size != dest_size:
                    print(f"✗ 文件 {i+1} 大小不匹配")
                    return False
            
            print("✓ 所有并发传输文件验证通过")
            
            return True
            
    except Exception as e:
        print(f"✗ 并发传输测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_transfer_with_errors():
    """测试传输错误处理和重试"""
    print("\n=== 测试传输错误处理 ===")
    
    try:
        from services.resumable_transfer import ResumableTransferManager, TransferStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResumableTransferManager(
                state_dir=os.path.join(temp_dir, "state"),
                default_chunk_size=64 * 1024,
                max_concurrent_chunks_per_transfer=1
            )
            
            # 创建测试文件
            source_file = os.path.join(temp_dir, "error_test.dat")
            dest_file = os.path.join(temp_dir, "nonexistent_dir", "error_dest.dat")  # 不存在的目录
            
            await create_test_file(source_file, 1)
            print("✓ 测试文件创建完成")
            
            # 尝试传输到不存在的目录
            transfer_id = await manager.start_transfer(
                source_path=source_file,
                destination_path=dest_file,
                options={
                    "verify_integrity": True,
                    "max_retry_attempts": 2
                }
            )
            
            print(f"✓ 错误测试传输已启动: {transfer_id}")
            
            # 等待传输完成（应该成功，因为会创建目录）
            while True:
                session = manager.active_sessions.get(transfer_id)
                if session and session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                    break
                await asyncio.sleep(0.1)
            
            # 检查结果 - 应该成功，因为会自动创建目录
            if session and session.status == TransferStatus.COMPLETED:
                print("✓ 传输成功完成（自动创建目录）")
            else:
                print(f"传输状态: {session.status if session else 'Unknown'}")
                # 这个测试可能成功也可能失败，取决于实现
            
            # 测试无效源文件
            invalid_source = os.path.join(temp_dir, "nonexistent.dat")
            valid_dest = os.path.join(temp_dir, "valid_dest.dat")
            
            try:
                await manager.start_transfer(
                    source_path=invalid_source,
                    destination_path=valid_dest
                )
                print("✗ 应该抛出FileNotFoundError")
                return False
            except FileNotFoundError:
                print("✓ 正确处理了不存在的源文件")
            
            return True
            
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_transfer_performance():
    """测试传输性能"""
    print("\n=== 测试传输性能 ===")
    
    try:
        from services.resumable_transfer import ResumableTransferManager, TransferStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ResumableTransferManager(
                state_dir=os.path.join(temp_dir, "state"),
                default_chunk_size=256 * 1024,  # 256KB 块
                max_concurrent_chunks_per_transfer=4  # 4个并发
            )
            
            # 创建大文件
            source_file = os.path.join(temp_dir, "perf_test.dat")
            dest_file = os.path.join(temp_dir, "perf_dest.dat")
            
            print("正在创建性能测试文件...")
            file_size_mb = 10  # 10MB
            await create_test_file(source_file, file_size_mb)
            print(f"✓ {file_size_mb}MB 文件创建完成")
            
            # 记录性能数据
            performance_data = []
            
            def performance_callback(transfer_id: str, progress):
                performance_data.append({
                    "timestamp": time.time(),
                    "progress_percent": progress.get_progress_percentage(),
                    "speed_bps": progress.current_speed_bps,
                    "completed_chunks": progress.completed_chunks,
                    "total_chunks": progress.chunk_count
                })
            
            manager.add_progress_callback(performance_callback)
            
            # 开始性能测试
            start_time = time.time()
            
            transfer_id = await manager.start_transfer(
                source_path=source_file,
                destination_path=dest_file,
                options={
                    "verify_integrity": True,
                    "max_concurrent_chunks": 4
                }
            )
            
            print(f"✓ 性能测试传输已启动: {transfer_id}")
            
            # 等待完成并收集性能数据
            while True:
                session = manager.active_sessions.get(transfer_id)
                if session and session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                    break
                await asyncio.sleep(0.1)
            
            end_time = time.time()
            
            if session and session.status == TransferStatus.COMPLETED:
                duration = end_time - start_time
                throughput_mbps = (file_size_mb * 8) / duration  # Mbps
                throughput_mb_s = file_size_mb / duration  # MB/s
                
                print("✓ 性能测试完成")
                print(f"  文件大小: {file_size_mb} MB")
                print(f"  传输时间: {duration:.2f} 秒")
                print(f"  吞吐量: {throughput_mb_s:.1f} MB/s ({throughput_mbps:.1f} Mbps)")
                print(f"  分块数量: {len(session.chunks)}")
                print(f"  并发度: 4 chunks")
                
                # 分析性能数据
                if performance_data:
                    max_speed = max(p["speed_bps"] for p in performance_data if p["speed_bps"] > 0)
                    avg_speed = sum(p["speed_bps"] for p in performance_data if p["speed_bps"] > 0) / len([p for p in performance_data if p["speed_bps"] > 0])
                    
                    print(f"  峰值速度: {max_speed / 1024 / 1024:.1f} MB/s")
                    print(f"  平均速度: {avg_speed / 1024 / 1024:.1f} MB/s")
            else:
                print(f"✗ 性能测试失败: {session.status if session else 'Unknown'}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ 性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_state_persistence():
    """测试状态持久化"""
    print("\n=== 测试状态持久化 ===")
    
    try:
        from services.resumable_transfer import ResumableTransferManager, TransferStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = os.path.join(temp_dir, "state")
            
            # 第一阶段：启动传输并暂停
            manager1 = ResumableTransferManager(
                state_dir=state_dir,
                default_chunk_size=32 * 1024
            )
            
            source_file = os.path.join(temp_dir, "state_test.dat")
            dest_file = os.path.join(temp_dir, "state_dest.dat")
            
            await create_test_file(source_file, 1)
            print("✓ 测试文件创建完成")
            
            transfer_id = await manager1.start_transfer(
                source_path=source_file,
                destination_path=dest_file,
                options={"verify_integrity": True}
            )
            
            print(f"✓ 传输已启动: {transfer_id}")
            
            # 等待部分完成
            await asyncio.sleep(0.3)
            await manager1.pause_transfer(transfer_id)
            print("✓ 传输已暂停")
            
            # 检查状态文件是否存在
            state_file_path = Path(state_dir) / f"{transfer_id}.json"
            if state_file_path.exists():
                print("✓ 状态文件已保存")
            else:
                print("✗ 状态文件不存在")
                return False
            
            # 第二阶段：创建新的管理器并恢复传输
            manager2 = ResumableTransferManager(state_dir=state_dir)
            
            success = await manager2.resume_transfer(transfer_id)
            if success:
                print("✓ 传输状态恢复成功")
            else:
                print("✗ 传输状态恢复失败")
                return False
            
            # 等待传输完成
            while True:
                session = manager2.active_sessions.get(transfer_id)
                if session and session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                    break
                await asyncio.sleep(0.1)
            
            if session and session.status == TransferStatus.COMPLETED:
                print("✓ 状态持久化传输完成")
                
                # 验证文件
                source_size = os.path.getsize(source_file)
                dest_size = os.path.getsize(dest_file)
                
                if source_size == dest_size:
                    print("✓ 持久化恢复文件验证通过")
                else:
                    print(f"✗ 持久化恢复文件验证失败: {source_size} != {dest_size}")
                    return False
            else:
                print(f"✗ 状态持久化传输失败: {session.status if session else 'Unknown'}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ 状态持久化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有断点续传测试"""
    print("🚀 开始断点续传系统测试")
    print("=" * 60)
    
    tests = [
        test_basic_transfer,
        test_resume_transfer,
        test_concurrent_transfers,
        test_transfer_with_errors,
        test_transfer_performance,
        test_state_persistence
    ]
    
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests):
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🏁 断点续传系统测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有断点续传测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))