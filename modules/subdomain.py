import concurrent.futures

import requests
import urllib3

from core.base import BaseModule, Field, register

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@register
class SubdomainModule(BaseModule):
    name = "subdomain"
    display_name = "子域名爆破"
    description = "读取根域名 + 子域名字典，批量探测存活子域名"
    fields = [
        Field("domain", "根域名", "str", "example.com", hint="例如 example.com"),
        Field("dict_path", "子域名字典", "file", "", hint="每行一个子域名词"),
        Field("scheme", "协议", "choice", "http", choices=["http", "https"]),
        Field("threads", "线程数", "int", 20),
        Field("timeout", "超时(秒)", "int", 5),
        Field("show_fail", "显示失败项", "bool", False),
    ]
    csv_columns = ["域名"]        # 导出只有一列：完整域名

    def run(self, params):
        domain = params["domain"].strip()
        if not domain:
            self.ctx.log("根域名不能为空", "error")
            return

        try:
            with open(params["dict_path"], "r", encoding="utf-8", errors="ignore") as f:
                words = [w.strip() for w in f if w.strip() and not w.startswith("#")]
        except Exception as e:
            self.ctx.log(f"读取字典失败: {e}", "error")
            return

        scheme = params["scheme"]
        threads = max(1, int(params["threads"]))
        timeout = max(1, int(params["timeout"]))
        show_fail = bool(params["show_fail"])

        self.ctx.log(f"载入字典 {len(words)} 条，目标 {domain}，线程 {threads}")

        def probe(word):
            if self.ctx.stopped():
                return
            host = f"{word}.{domain}"
            url = f"{scheme}://{host}"
            try:
                r = requests.get(url, timeout=timeout, verify=False,
                                 allow_redirects=False)
            except requests.RequestException as e:
                if show_fail:
                    self.ctx.log(f"[-] {url} -> {e.__class__.__name__}", "warn")
                return

            self.ctx.result(f"[{r.status_code}] {url}")
            # 只提交完整域名
            self.ctx.row({"域名": host})

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            list(pool.map(probe, words))

        self.ctx.log("子域名爆破完成", "ok")