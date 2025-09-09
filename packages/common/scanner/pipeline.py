"""
扫描管道
提供扫描流水线处理能力
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """管道上下文"""

    file_path: Path
    data: dict[str, Any]
    metadata: dict[str, Any]
    errors: list[str]

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data = {}
        self.metadata = {}
        self.errors = []

    def set_data(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)

    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0


class PipelineStage(ABC):
    """管道阶段基类"""

    def __init__(self, name: str):
        self.name = name
        self.next_stage: PipelineStage | None = None

    def set_next(self, stage: "PipelineStage") -> "PipelineStage":
        """设置下一个阶段"""
        self.next_stage = stage
        return stage

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext | None:
        """处理上下文"""
        pass

    def execute(self, context: PipelineContext) -> PipelineContext | None:
        """执行阶段处理"""
        try:
            # 处理当前阶段
            result = self.process(context)

            # 如果处理成功且有下一阶段，继续处理
            if result and self.next_stage:
                return self.next_stage.execute(result)

            return result

        except Exception as e:
            logger.error(f"Stage {self.name} failed: {e}")
            context.add_error(f"Stage {self.name} error: {str(e)}")
            return None


class FileReaderStage(PipelineStage):
    """文件读取阶段"""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__("FileReader")
        self.encoding = encoding

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """读取文件内容"""
        try:
            if context.file_path.suffix in [".jar", ".zip"]:
                # 二进制文件
                with open(context.file_path, "rb") as f:
                    context.set_data("content", f.read())
                    context.set_data("is_binary", True)
            else:
                # 文本文件
                with open(context.file_path, encoding=self.encoding) as f:
                    context.set_data("content", f.read())
                    context.set_data("is_binary", False)

            return context

        except Exception as e:
            context.add_error(f"Failed to read file: {e}")
            return context


class ContentParserStage(PipelineStage):
    """内容解析阶段"""

    def __init__(self, parsers: dict[str, Callable[[str], Any]]):
        super().__init__("ContentParser")
        self.parsers = parsers

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """解析文件内容"""
        file_ext = context.file_path.suffix.lower()

        if file_ext not in self.parsers:
            logger.debug(f"No parser for extension: {file_ext}")
            return context

        parser = self.parsers[file_ext]
        content = context.get_data("content")

        if content and not context.get_data("is_binary"):
            try:
                parsed = parser(content)
                context.set_data("parsed_content", parsed)
            except Exception as e:
                context.add_error(f"Parse error: {e}")

        return context


class ValidationStage(PipelineStage):
    """验证阶段"""

    def __init__(self, validators: list[Callable[[PipelineContext], bool]]):
        super().__init__("Validation")
        self.validators = validators

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """验证上下文"""
        for validator in self.validators:
            try:
                if not validator(context):
                    context.add_error(f"Validation failed: {validator.__name__}")
            except Exception as e:
                context.add_error(f"Validator error: {e}")

        return context


class TransformStage(PipelineStage):
    """转换阶段"""

    def __init__(self, transformer: Callable[[Any], Any]):
        super().__init__("Transform")
        self.transformer = transformer

    def process(self, context: PipelineContext) -> PipelineContext | None:
        """转换数据"""
        data = context.get_data("parsed_content")

        if data:
            try:
                transformed = self.transformer(data)
                context.set_data("transformed_content", transformed)
            except Exception as e:
                context.add_error(f"Transform error: {e}")

        return context


class ScanPipeline:
    """扫描管道"""

    def __init__(self, stages: list[PipelineStage] | None = None):
        self.stages = stages or []
        self._build_pipeline()

    def _build_pipeline(self):
        """构建管道链"""
        if len(self.stages) > 1:
            for i in range(len(self.stages) - 1):
                self.stages[i].set_next(self.stages[i + 1])

    def add_stage(self, stage: PipelineStage) -> "ScanPipeline":
        """添加阶段"""
        if self.stages:
            self.stages[-1].set_next(stage)
        self.stages.append(stage)
        return self

    def process(self, file_path: Path) -> PipelineContext | None:
        """处理文件"""
        if not self.stages:
            logger.warning("Pipeline has no stages")
            return None

        context = PipelineContext(file_path)
        return self.stages[0].execute(context)

    def process_batch(
        self, file_paths: list[Path], max_workers: int = 4
    ) -> list[PipelineContext]:
        """批量处理"""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.process, path): path for path in file_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {path}: {e}")

        return results


class AsyncPipeline:
    """异步管道（生产者-消费者模式）"""

    def __init__(self, stages: list[PipelineStage], queue_size: int = 100):
        self.stages = stages
        self.queue_size = queue_size
        self.queues: list[Queue] = []
        self.workers: list[Thread] = []
        self.stop_event = Event()

        # 为每个阶段创建队列
        for _ in range(len(stages) + 1):
            self.queues.append(Queue(maxsize=queue_size))

    def _worker(self, stage_index: int):
        """工作线程"""
        stage = self.stages[stage_index]
        input_queue = self.queues[stage_index]
        output_queue = self.queues[stage_index + 1]

        while not self.stop_event.is_set():
            try:
                # 从输入队列获取上下文
                context = input_queue.get(timeout=0.1)

                if context is None:  # 毒丸信号
                    output_queue.put(None)
                    break

                # 处理上下文
                result = stage.process(context)

                if result:
                    output_queue.put(result)

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error in stage {stage.name}: {e}")

    def start(self):
        """启动管道"""
        for i in range(len(self.stages)):
            worker = Thread(target=self._worker, args=(i,))
            worker.start()
            self.workers.append(worker)

    def stop(self):
        """停止管道"""
        self.stop_event.set()

        # 发送毒丸信号
        if self.queues:
            self.queues[0].put(None)

        # 等待所有工作线程结束
        for worker in self.workers:
            worker.join()

    def submit(self, file_path: Path):
        """提交文件到管道"""
        context = PipelineContext(file_path)
        self.queues[0].put(context)

    def get_result(self, timeout: float | None = None) -> PipelineContext | None:
        """获取处理结果"""
        try:
            return self.queues[-1].get(timeout=timeout)
        except Empty:
            return None


class PipelineBuilder:
    """管道构建器"""

    def __init__(self):
        self.stages: list[PipelineStage] = []

    def add_reader(self, encoding: str = "utf-8") -> "PipelineBuilder":
        """添加文件读取阶段"""
        self.stages.append(FileReaderStage(encoding))
        return self

    def add_parser(self, parsers: dict[str, Callable]) -> "PipelineBuilder":
        """添加解析阶段"""
        self.stages.append(ContentParserStage(parsers))
        return self

    def add_validator(self, validators: list[Callable]) -> "PipelineBuilder":
        """添加验证阶段"""
        self.stages.append(ValidationStage(validators))
        return self

    def add_transformer(self, transformer: Callable) -> "PipelineBuilder":
        """添加转换阶段"""
        self.stages.append(TransformStage(transformer))
        return self

    def add_custom(self, stage: PipelineStage) -> "PipelineBuilder":
        """添加自定义阶段"""
        self.stages.append(stage)
        return self

    def build(self) -> ScanPipeline:
        """构建管道"""
        return ScanPipeline(self.stages)

    def build_async(self, queue_size: int = 100) -> AsyncPipeline:
        """构建异步管道"""
        return AsyncPipeline(self.stages, queue_size)
