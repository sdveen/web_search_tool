from dataclasses import dataclass
from typing import Callable, List, Optional, Type


# ---------------------------------------------------------------- 字段定义
@dataclass
class Field:
    key: str
    label: str
    type: str = "str"          # str | password | int | file | bool | choice
    default: object = ""
    choices: Optional[List[str]] = None
    hint: str = ""


# ---------------------------------------------------------------- 上下文桥接
class ModuleContext:
    """模块与 GUI 之间的桥接：日志 / 结果 / 结构化行 / 停止信号。"""

    def __init__(self,
                 log_fn: Callable[[str, str], None],
                 result_fn: Callable[[str], None],
                 stop_fn: Callable[[], bool],
                 row_fn: Optional[Callable[[dict], None]] = None):
        self._log = log_fn
        self._result = result_fn
        self._stop = stop_fn
        self._row = row_fn

    def log(self, msg, level="info"):
        self._log(str(msg), level)

    def result(self, msg):
        self._result(str(msg))

    def row(self, data: dict):
        """提交一行结构化数据，供界面导出 CSV。"""
        if self._row:
            self._row(dict(data))

    def stopped(self) -> bool:
        return self._stop()


# ---------------------------------------------------------------- 模块基类
class BaseModule:
    """所有模块的基类，子类只需覆写 name / display_name / description / fields / run。"""

    name = "base"
    display_name = "基础模块"
    description = ""
    fields: List[Field] = []
    csv_columns: List[str] = []    # 导出 CSV 的列顺序；空表示不支持 CSV

    def __init__(self, ctx: ModuleContext):
        self.ctx = ctx

    def run(self, params: dict) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------- 注册表
_REGISTRY: List[Type[BaseModule]] = []


def register(cls: Type[BaseModule]) -> Type[BaseModule]:
    """类装饰器：把一个模块类登记到全局注册表。"""
    if not issubclass(cls, BaseModule):
        raise TypeError(f"{cls.__name__} 必须继承 BaseModule")
    if cls in _REGISTRY:
        return cls
    _REGISTRY.append(cls)
    return cls


def get_modules() -> List[Type[BaseModule]]:
    """返回按注册顺序排列的所有模块类。"""
    return list(_REGISTRY)