# 资产收集工具箱

一个基于 Python + Tkinter 的轻量级资产收集工具，集成子域名爆破、目录扫描与 FOFA 信息收集，支持通过 `@register` 装饰器热插拔扩展新模块。界面风格为清新的淡蓝 + 白配色。

> 仅用于**已获授权的安全测试与资产梳理**。请勿对未授权目标使用。

---

## 功能概览

| 模块 | 说明 |
|---|---|
| 子域名爆破 | 读取根域名 + 字典，批量探测存活子域名，输出状态码 |
| 目录爆破 | 对目标 URL 进行目录/文件探测，自动过滤软 404，支持附加后缀 |
| FOFA 信息收集 | 通过 FOFA API（含自建代理）按语法查询资产，可导出 CSV |

界面特性：

- 左侧模块列表，点击即切换到对应参数表单
- 参数表单按 `Field` 描述自动生成，无需手写布局
- 后台线程执行，界面不卡顿；支持中途停止
- 输出区分 info / ok / warn / error / result 五种颜色
- 结构化结果一键导出 CSV（ip、port、host）

---

## 目录结构

toolbox/
├── main.py # 入口，Tkinter 界面
├── core/
│ ├── **init**.py
│ └── base.py # Field / ModuleContext / BaseModule / 注册表
└── modules/
├── **init**.py # 导入各模块，触发 @register
├── subdomain.py # 子域名爆破
├── directory.py # 目录爆破
└── fofa.py # FOFA 信息收集

---

## 环境要求

- Python 3.8+
- 依赖：`requests`、`urllib3`（Tkinter 为 Python 标准库自带）

安装：

```bash
pip install requests urllib3
```

## 快速开始

bash

```
cd toolbox
python main.py
```



启动后：

1. 左侧选择模块（子域名爆破 / 目录爆破 / FOFA 信息收集）
2. 右侧填写参数，字典类字段点「浏览…」选择文件
3. 点「▶ 开始」运行，日志实时滚动
4. 需要保存时点「导出 CSV」（有结构化结果时）或导出文本

------

## 模块说明

### 1. 子域名爆破

| 参数       | 说明                                |
| :--------- | :---------------------------------- |
| 根域名     | 例如 `example.com`                  |
| 子域名字典 | 每行一个词，如 `www`、`mail`、`api` |
| 协议       | `http` 或 `https`                   |
| 线程数     | 并发数，默认 20                     |
| 超时(秒)   | 单请求超时，默认 5                  |
| 显示失败项 | 勾选后打印 DNS 解析失败/超时的条目  |

输出示例：

text

```
[200] https://www.example.com
[403] https://admin.example.com
```



### 2. 目录爆破

| 参数          | 说明                                                  |
| :------------ | :---------------------------------------------------- |
| 目标 URL      | 需带协议，如 `http://example.com`                     |
| 目录字典      | 每行一个路径，如 `admin`、`login.php`                 |
| 附加后缀      | 逗号分隔，如 `php,html`，会生成 `xxx.php`、`xxx.html` |
| 关注状态码    | 逗号分隔，默认 `200,301,302,403`                      |
| 线程数 / 超时 | 同子域名模块                                          |
| 跟随跳转      | 是否跟随 30x 跳转                                     |

内置**软 404 过滤**：先请求一个随机路径，记录其状态码与响应长度，探测时命中相同特征即忽略。

输出示例：

text

```
[200] http://example.com/admin (len=1234)
[403] http://example.com/.git (len=289)
```



### 3. FOFA 信息收集

| 参数     | 说明                                         |
| :------- | :------------------------------------------- |
| API Key  | 从 FOFA 服务商获取                           |
| 查询语法 | 例如 `title="123"` 或 `domain="example.com"` |
| 返回条数 | 默认 100                                     |
| 返回字段 | 逗号分隔，默认 `host,ip,port`                |

结果同时写入文本框和结构化缓存。导出 CSV 时固定输出三列：`ip`、`port`、`host`。

------

## 扩展新模块

只需三步，界面无需改动。

**1. 在 `modules/` 下新建文件，例如 `whois.py`：**

python

```
from core.base import BaseModule, Field, register


@register
class WhoisModule(BaseModule):
    name = "whois"
    display_name = "WHOIS 查询"
    description = "查询域名注册信息"
    fields = [
        Field("domain", "域名", "str", "example.com"),
        Field("save", "保存结果", "bool", False),
    ]

    def run(self, params):
        domain = params["domain"].strip()
        if not domain:
            self.ctx.log("域名不能为空", "error")
            return
        self.ctx.log(f"查询 {domain} ...")
        # ... 你的逻辑
        self.ctx.result(f"example.com -> 注册商 XXX")
        self.ctx.log("完成", "ok")
```



**2. 在 `modules/__init__.py` 里加一行导入：**

python

```
from modules import whois   # noqa: F401
```



**3. 重启程序**，左侧列表会自动出现新模块。

### Field 支持的类型

| type       | 渲染控件          | 说明                      |
| :--------- | :---------------- | :------------------------ |
| `str`      | 单行输入框        | 默认                      |
| `password` | 密码框（掩码）    | 敏感信息                  |
| `int`      | 单行输入框        | 自动转 int                |
| `file`     | 输入框 + 浏览按钮 | 选择文件路径              |
| `bool`     | 复选框            | 布尔值                    |
| `choice`   | 下拉框            | 配合 `choices=[...]` 使用 |

### 模块可用的回调

通过 `self.ctx` 访问：

| 方法                         | 用途                                          |
| :--------------------------- | :-------------------------------------------- |
| `ctx.log(msg, level="info")` | 写日志，level 可取 `info`/`ok`/`warn`/`error` |
| `ctx.result(msg)`            | 写结果行（蓝色高亮）                          |
| `ctx.row(dict)`              | 提交结构化数据，供导出 CSV                    |
| `ctx.stopped()`              | 返回是否收到停止信号，长循环里定期检查        |

------

## 免责声明

本工具仅供**合法授权**范围内的安全测试、资产梳理与研究学习使用。使用者需自行承担因使用本工具产生的一切法律责任。作者不对任何滥用行为负责。