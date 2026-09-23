import concurrent.futures
import socket

from core.base import BaseModule, Field, register


# 常见 Top100 端口，用于 ports 填 "top100" 时的快捷扫描
TOP100_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 512, 513,
    514, 515, 873, 993, 995, 1080, 1099, 1433, 1521, 1723, 2049, 2082,
    2083, 2086, 2087, 2181, 2375, 2483, 2484, 3000, 3128, 3268, 3269,
    3306, 3389, 3690, 4444, 4848, 5000, 5001, 5060, 5222, 5432, 5601,
    5631, 5632, 5900, 5901, 5984, 6000, 6379, 6666, 6667, 7001, 7002,
    7077, 8000, 8001, 8005, 8009, 8080, 8081, 8082, 8086, 8088, 8089,
    8090, 8091, 8161, 8180, 8443, 8500, 8649, 8686, 8888, 9000, 9001,
    9042, 9090, 9092, 9100, 9200, 9300, 9418, 9999, 10000, 11211,
    15672, 27017, 27018, 27019, 28017, 32768, 49152, 50000, 50070,
    61616,
]


@register
class PortScanModule(BaseModule):
    name = "port_scan"
    display_name = "端口扫描"
    description = "对目标 IP/域名进行 TCP 端口扫描，识别开放端口、服务名与 Banner"
    fields = [
        Field("host", "目标", "str", "192.168.88.66",
              hint="IP 或域名，多个用逗号分隔"),
        Field("ports", "端口范围", "str", "top100",
              hint="如 1-1024 / 22,80,443 / top100"),
        Field("threads", "线程数", "int", 100),
        Field("timeout", "超时(秒)", "int", 3),
        Field("banner", "尝试获取 Banner", "bool", True),
        Field("show_closed", "显示关闭端口", "bool", False),
    ]
    csv_columns = ["host", "port", "service", "banner"]

    def run(self, params):
        hosts = [h.strip() for h in params["host"].split(",") if h.strip()]
        if not hosts:
            self.ctx.log("目标不能为空", "error")
            return

        ports = self._parse_ports(params["ports"])
        if not ports:
            self.ctx.log("端口范围解析失败，示例: 1-1024 / 22,80,443 / top100",
                         "error")
            return

        threads = max(1, int(params["threads"]))
        timeout = max(1, int(params["timeout"]))
        grab_banner = bool(params["banner"])
        show_closed = bool(params["show_closed"])

        tasks = [(h, p) for h in hosts for p in ports]
        self.ctx.log(
            f"目标 {len(hosts)} 个 | 端口 {len(ports)} 个 | "
            f"共 {len(tasks)} 条任务 | 线程 {threads}")

        open_count = 0
        scanned = 0

        def probe(task):
            nonlocal open_count, scanned
            if self.ctx.stopped():
                return
            host, port = task
            try:
                with socket.create_connection((host, port), timeout=timeout) as s:
                    service = self._guess_service(port)
                    banner = self._grab_banner(s) if grab_banner else ""
            except (OSError, socket.timeout):
                scanned += 1
                if show_closed:
                    self.ctx.log(f"[-] {host}:{port} closed", "warn")
                return

            scanned += 1
            open_count += 1
            text = f"[+] {host}:{port} open"
            if service:
                text += f" ({service})"
            if banner:
                text += f" | {banner}"
            self.ctx.result(text)
            self.ctx.row({"host": host, "port": port,
                          "service": service, "banner": banner})

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as pool:
            list(pool.map(probe, tasks))

        if self.ctx.stopped():
            self.ctx.log("已收到停止信号，扫描中断", "warn")
        self.ctx.log(
            f"扫描完成，探测 {scanned}/{len(tasks)}，开放 {open_count} 个端口",
            "ok")

    # ---------------------------------------------------------- 工具方法
    @staticmethod
    def _parse_ports(spec):
        """解析端口表达式：1-1024 / 22,80,443 / top100。"""
        spec = str(spec).strip().lower()
        if spec == "top100":
            return list(TOP100_PORTS)

        ports = set()
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    start, end = int(start), int(end)
                except ValueError:
                    return None
                if not (1 <= start <= end <= 65535):
                    return None
                ports.update(range(start, end + 1))
            elif part.isdigit():
                p = int(part)
                if not 1 <= p <= 65535:
                    return None
                ports.add(p)
            else:
                return None
        return sorted(ports)

    @staticmethod
    def _guess_service(port):
        try:
            return socket.getservbyport(port, "tcp")
        except OSError:
            return ""

    @staticmethod
    def _grab_banner(sock):
        try:
            sock.settimeout(2)
            try:
                sock.sendall(b"\r\n")
            except OSError:
                pass
            data = sock.recv(128)
            return data.decode("utf-8", errors="ignore").strip()
        except (OSError, socket.timeout):
            return ""