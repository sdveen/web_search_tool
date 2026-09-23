import os
import queue
import random
import string
import threading
from urllib.parse import urlparse

import requests
import urllib3

from core.base import BaseModule, Field, register

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# 判定"这是文件而非目录"的常见后缀，避免把 admin.php 当目录去递归
COMMON_FILE_EXTS = {
    "html", "htm", "php", "asp", "aspx", "jsp", "jspx", "do", "action",
    "txt", "js", "css", "json", "xml", "yaml", "yml",
    "png", "jpg", "jpeg", "gif", "svg", "ico", "bmp", "webp",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "zip", "tar", "gz", "rar", "7z", "bz2",
    "exe", "dll", "so", "bin", "apk", "jar", "war",
    "map", "lock", "log", "conf", "ini", "bak", "sql",
}


@register
class DirectoryModule(BaseModule):
    name = "directory"
    display_name = "目录爆破"
    description = "对目标 URL 进行目录/文件探测，自动过滤软 404，支持递归扫描子目录"
    fields = [
        Field("target", "目标 URL", "str", "http://example.com", hint="需带协议"),
        Field("dict_path", "目录字典", "file", ""),
        Field("extensions", "附加后缀", "str", "", hint="如 php,html；可留空"),
        Field("codes", "关注状态码", "str", "200,301,302,403", hint="逗号分隔"),
        Field("threads", "线程数", "int", 20),
        Field("timeout", "超时(秒)", "int", 5),
        Field("follow", "跟随跳转", "bool", False),
        Field("recursive", "递归扫描子目录", "bool", True),
        Field("max_depth", "最大递归深度", "int", 2,
              hint="0=仅根目录；1=一层子目录；以此类推"),
        Field("recurse_codes", "触发递归的状态码", "str", "301,302",
              hint="逗号分隔，命中即把该路径当目录继续扫"),
    ]
    csv_columns = ["url"]           # 导出列：完整 URL

    def run(self, params):
        target = params["target"].strip().rstrip("/")
        if not target.startswith(("http://", "https://")):
            self.ctx.log("目标 URL 需包含 http:// 或 https://", "error")
            return

        try:
            with open(params["dict_path"], "r", encoding="utf-8", errors="ignore") as f:
                words = [w.strip().lstrip("/") for w in f
                         if w.strip() and not w.startswith("#")]
        except Exception as e:
            self.ctx.log(f"读取字典失败: {e}", "error")
            return

        extensions = [e.strip().lstrip(".")
                      for e in params["extensions"].split(",") if e.strip()]

        codes = self._parse_codes(params["codes"], {200, 301, 302, 403})
        recurse_codes = self._parse_codes(params["recurse_codes"], {301, 302})

        threads = max(1, int(params["threads"]))
        timeout = max(1, int(params["timeout"]))
        follow = bool(params["follow"])
        recursive = bool(params["recursive"])
        max_depth = max(0, int(params["max_depth"]))

        session = requests.Session()
        session.verify = False
        session.headers.update({"User-Agent": "Mozilla/5.0 (AssetScanner/1.0)"})

        # 组装当前层要探测的相对路径：word 和 word.ext
        base_paths = []
        for w in words:
            base_paths.append(w)
            for ext in extensions:
                base_paths.append(f"{w}.{ext}")

        self.ctx.log(
            f"目标 {target} | 字典 {len(base_paths)} 条 | 线程 {threads} | "
            f"递归 {'开' if recursive else '关'} | 最大深度 {max_depth}")

        # 任务队列：元素为 (base_url, depth)，base_url 以 / 结尾
        task_q = queue.Queue()
        task_q.put((target + "/", 0))

        visited_dirs = set()
        visited_lock = threading.Lock()

        # ---------------------------------------------------------- 工具函数
        def make_soft404_baseline(base_url):
            """为每个目录单独建立软 404 基线。"""
            rand = "".join(random.choices(
                string.ascii_lowercase + string.digits, k=12))
            try:
                r = session.get(base_url + rand, timeout=timeout,
                                allow_redirects=follow)
                return {r.status_code}, {len(r.content)}
            except Exception:
                return set(), set()

        def is_file_like(path):
            """根据路径末段是否带常见后缀，判断它更像文件而非目录。"""
            last = os.path.basename(path)
            if "." not in last:
                return False
            ext = last.rsplit(".", 1)[-1].lower()
            return ext in COMMON_FILE_EXTS or ext in extensions

        def should_recurse(url, resp):
            """判断命中的路径是否可以作为下一层的扫描起点。"""
            if resp.status_code not in recurse_codes:
                return False
            path = urlparse(url).path
            if is_file_like(path):
                return False
            # 301/302 且有 Location：只有跳转到以 / 结尾才算目录
            if resp.status_code in (301, 302, 307, 308):
                loc = resp.headers.get("Location", "")
                if loc:
                    return loc.endswith("/")
            return True

        # ---------------------------------------------------------- 处理单个目录
        def process_dir(base_url, depth):
            with visited_lock:
                if base_url in visited_dirs:
                    return
                visited_dirs.add(base_url)

            indent = "  " * depth
            self.ctx.log(f"{indent}>>> 进入目录 {base_url} (深度 {depth})")

            soft_codes, soft_lens = make_soft404_baseline(base_url)
            if soft_codes:
                self.ctx.log(
                    f"{indent}    软 404 基线: 状态码={soft_codes}, "
                    f"长度={soft_lens}", "warn")

            for path in base_paths:
                if self.ctx.stopped():
                    return
                url = base_url + path
                try:
                    r = session.get(url, timeout=timeout,
                                    allow_redirects=follow)
                except requests.RequestException:
                    continue

                # 过滤软 404
                if r.status_code in soft_codes and len(r.content) in soft_lens:
                    continue

                if r.status_code not in codes:
                    continue

                length = len(r.content)
                self.ctx.result(
                    f"{indent}[{r.status_code}] {url} (len={length})")
                self.ctx.row({"url": url})

                # 递归：把命中的目录作为新任务丢回队列
                if (recursive and depth < max_depth
                        and should_recurse(url, r)):
                    child = url if url.endswith("/") else url + "/"
                    with visited_lock:
                        if child in visited_dirs:
                            continue
                    task_q.put((child, depth + 1))

        # ---------------------------------------------------------- worker
        def worker():
            while True:
                task = task_q.get()
                try:
                    if task is None:      # 退出信号
                        return
                    process_dir(*task)
                except Exception as e:
                    self.ctx.log(f"任务异常: {e}", "error")
                finally:
                    task_q.task_done()

        # ---------------------------------------------------------- 调度
        worker_threads = []
        for _ in range(threads):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            worker_threads.append(t)

        # 等待队列清空（会包含递归产生的新任务）
        task_q.join()

        # 通知 worker 退出
        for _ in range(threads):
            task_q.put(None)
        for t in worker_threads:
            t.join(timeout=2)

        self.ctx.log(
            f"目录扫描完成，共访问 {len(visited_dirs)} 个目录", "ok")

    # ---------------------------------------------------------- 工具方法
    @staticmethod
    def _parse_codes(s, default):
        codes = set()
        for c in str(s).split(","):
            c = c.strip()
            if c.isdigit():
                codes.add(int(c))
        return codes or default



    