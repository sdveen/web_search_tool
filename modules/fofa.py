import base64

import requests

from core.base import BaseModule, Field, register


@register
class FofaModule(BaseModule):
    name = "fofa"
    display_name = "FOFA 信息收集"
    description = "通过 FOFA API 根据语法查询资产"
    fields = [
        Field("api_key", "API Key", "password", "",
              hint="必填，从 fofoapi.com 获取"),
        Field("query", "查询语法", "str", 'title="123"',
              hint='例如 title="123" 或 domain="example.com"'),
        Field("size", "返回条数", "int", 100),
        Field("fields", "返回字段", "str", "host,ip,port",
              hint="逗号分隔，导出时只取 host/ip/port"),
    ]
    csv_columns = ["ip", "port", "host"]     # 导出三列

    API_URL = "https://fofoapi.com/api/v1/search/all"

    def run(self, params):
        query = params["query"].strip()
        if not query:
            self.ctx.log("查询语法不能为空", "error")
            return

        api_key = params["api_key"].strip()
        if not api_key:
            self.ctx.log("API Key 不能为空", "error")
            return

        field_names = [f.strip().lower() for f in params["fields"].split(",") if f.strip()]

        qbase64 = base64.b64encode(query.encode("utf-8")).decode("utf-8")

        payload = {
            "key": api_key,
            "qbase64": qbase64,
            "size": int(params["size"]),
            "fields": ",".join(field_names),
        }

        self.ctx.log(f"查询: {query}")
        try:
            r = requests.get(self.API_URL, params=payload, timeout=20)
        except requests.RequestException as e:
            self.ctx.log(f"请求异常: {e}", "error")
            return

        self.ctx.log(f"HTTP 状态码: {r.status_code}")

        try:
            data = r.json()
        except ValueError:
            self.ctx.log(f"响应非 JSON，前 300 字符: {r.text[:300]}", "error")
            return

        if data.get("error"):
            self.ctx.log(f"FOFA 错误: {data.get('errmsg', data)}", "error")
            return

        results = data.get("results", [])
        self.ctx.log(f"共返回 {len(results)} 条结果")

        for row in results:
            if isinstance(row, list):
                rec = {field_names[i]: (row[i] if i < len(row) else "")
                       for i in range(len(field_names))}
                self.ctx.row(rec)
                self.ctx.result(" | ".join(str(x) for x in row))
            elif isinstance(row, dict):
                rec = {str(k).lower(): v for k, v in row.items()}
                self.ctx.row(rec)
                self.ctx.result(" | ".join(f"{k}={v}" for k, v in row.items()))
            else:
                self.ctx.result(str(row))

        self.ctx.log("FOFA 查询完成", "ok")