# 只要导入各模块文件，@register 就会在导入时把类登记到全局注册表
from modules import subdomain   # noqa: F401
from modules import directory   # noqa: F401
from modules import port_scan   # noqa: F401
from modules import fofa        # noqa: F401