import csv
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import modules  # noqa: F401
from core.base import ModuleContext, get_modules


# ==================== 配色常量 ====================
CLR_BG         = "#EEF5FC"
CLR_CARD       = "#FFFFFF"
CLR_BORDER     = "#CFE0F0"
CLR_PRIMARY    = "#4A90D9"
CLR_PRIMARY_H  = "#3A7BC0"
CLR_PRIMARY_L  = "#E3EFFB"
CLR_TEXT       = "#2C3E50"
CLR_TEXT_SUB   = "#7F8C9A"
CLR_INPUT_BG   = "#FBFDFF"
CLR_SELECT_BG  = "#DCEBFA"

TAG_COLORS = {
    "info":   "#2C3E50",
    "ok":     "#27AE60",
    "warn":   "#E67E22",
    "error":  "#E74C3C",
    "result": "#2980B9",
    "time":   "#95A5A6",
}


class ToolboxApp:
    AUTHOR = "sdveen"
    VERSION = "v0.1"

    def __init__(self, root):
        self.root = root
        self.root.title(f"work for you  {self.VERSION} - by {self.AUTHOR}")
        self.root.geometry("1060x700")
        self.root.configure(bg=CLR_BG)

        self.msg_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.modules = get_modules()
        self.current_module = None
        self.field_vars = {}
        self.rows = []                # 结构化结果
        self.active_columns = []      # 本次运行模块的 CSV 列头

        self._setup_style()
        self._build_ui()
        if self.modules:
            self.module_list.selection_set(0)
            self._on_module_select()
        self.root.after(100, self._poll_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- 样式 ----------------
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=CLR_BG)
        style.configure("Card.TFrame", background=CLR_CARD)

        style.configure("TLabel", background=CLR_BG, foreground=CLR_TEXT,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Card.TLabel", background=CLR_CARD, foreground=CLR_TEXT,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Sub.TLabel", background=CLR_CARD,
                        foreground=CLR_TEXT_SUB,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", background=CLR_BG,
                        foreground=CLR_PRIMARY,
                        font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Sign.TLabel", background=CLR_BG,
                        foreground=CLR_TEXT_SUB,
                        font=("Microsoft YaHei UI", 8, "italic"))

        style.configure("TLabelframe",
                        background=CLR_BG,
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_BORDER,
                        darkcolor=CLR_BORDER,
                        relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label",
                        background=CLR_BG, foreground=CLR_PRIMARY,
                        font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Card.TLabelframe",
                        background=CLR_CARD,
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_BORDER,
                        darkcolor=CLR_BORDER,
                        relief="solid", borderwidth=1)
        style.configure("Card.TLabelframe.Label",
                        background=CLR_CARD, foreground=CLR_PRIMARY,
                        font=("Microsoft YaHei UI", 9, "bold"))

        style.configure("TButton",
                        background=CLR_CARD,
                        foreground=CLR_TEXT,
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_CARD,
                        darkcolor=CLR_CARD,
                        focuscolor=CLR_CARD,
                        relief="flat",
                        padding=(10, 5),
                        font=("Microsoft YaHei UI", 9))
        style.map("TButton",
                  background=[("active", CLR_PRIMARY_L),
                              ("pressed", CLR_PRIMARY_L),
                              ("disabled", CLR_BG)],
                  foreground=[("disabled", CLR_TEXT_SUB)],
                  bordercolor=[("active", CLR_PRIMARY)],
                  lightcolor=[("active", CLR_PRIMARY_L)],
                  darkcolor=[("active", CLR_PRIMARY_L)])

        style.configure("Accent.TButton",
                        background=CLR_PRIMARY,
                        foreground="#FFFFFF",
                        bordercolor=CLR_PRIMARY,
                        lightcolor=CLR_PRIMARY,
                        darkcolor=CLR_PRIMARY,
                        focuscolor=CLR_PRIMARY,
                        relief="flat",
                        padding=(14, 5),
                        font=("Microsoft YaHei UI", 9, "bold"))
        style.map("Accent.TButton",
                  background=[("active", CLR_PRIMARY_H),
                              ("pressed", CLR_PRIMARY_H),
                              ("disabled", "#A9C7E6")],
                  foreground=[("disabled", "#F0F6FC")],
                  bordercolor=[("active", CLR_PRIMARY_H)],
                  lightcolor=[("active", CLR_PRIMARY_H)],
                  darkcolor=[("active", CLR_PRIMARY_H)])

        style.configure("Stop.TButton",
                        background=CLR_CARD,
                        foreground="#C0392B",
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_CARD,
                        darkcolor=CLR_CARD,
                        focuscolor=CLR_CARD,
                        relief="flat",
                        padding=(10, 5),
                        font=("Microsoft YaHei UI", 9))
        style.map("Stop.TButton",
                  background=[("active", "#FDECEA"), ("pressed", "#FDECEA")],
                  bordercolor=[("active", "#E74C3C")],
                  lightcolor=[("active", "#FDECEA")],
                  darkcolor=[("active", "#FDECEA")])

        style.configure("TEntry",
                        fieldbackground=CLR_INPUT_BG,
                        foreground=CLR_TEXT,
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_BORDER,
                        darkcolor=CLR_BORDER,
                        insertcolor=CLR_PRIMARY,
                        padding=6,
                        relief="flat")
        style.map("TEntry",
                  bordercolor=[("focus", CLR_PRIMARY)],
                  lightcolor=[("focus", CLR_PRIMARY)],
                  darkcolor=[("focus", CLR_PRIMARY)])

        style.configure("TCombobox",
                        fieldbackground=CLR_INPUT_BG,
                        background=CLR_CARD,
                        foreground=CLR_TEXT,
                        bordercolor=CLR_BORDER,
                        lightcolor=CLR_BORDER,
                        darkcolor=CLR_BORDER,
                        arrowcolor=CLR_PRIMARY,
                        padding=5,
                        relief="flat")
        style.map("TCombobox",
                  fieldbackground=[("readonly", CLR_INPUT_BG)],
                  bordercolor=[("focus", CLR_PRIMARY)],
                  lightcolor=[("focus", CLR_PRIMARY)],
                  darkcolor=[("focus", CLR_PRIMARY)])

        self.root.option_add("*TCombobox*Listbox.background", CLR_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", CLR_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", CLR_PRIMARY)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
        self.root.option_add("*TCombobox*Listbox.font", ("Microsoft YaHei UI", 9))

        style.configure("TCheckbutton",
                        background=CLR_CARD,
                        foreground=CLR_TEXT,
                        focuscolor=CLR_CARD,
                        font=("Microsoft YaHei UI", 9))
        style.map("TCheckbutton",
                  indicatorcolor=[("selected", CLR_PRIMARY),
                                  ("!selected", CLR_CARD)],
                  background=[("active", CLR_CARD)])

        style.configure("TSeparator", background=CLR_BORDER)

        style.configure("TScrollbar",
                        background=CLR_CARD,
                        troughcolor=CLR_BG,
                        bordercolor=CLR_BG,
                        arrowcolor=CLR_PRIMARY,
                        lightcolor=CLR_CARD,
                        darkcolor=CLR_CARD,
                        relief="flat")
        style.map("TScrollbar",
                  background=[("active", CLR_PRIMARY_L)],
                  arrowcolor=[("active", CLR_PRIMARY_H)])

    # ---------------- UI ----------------
    def _build_ui(self):
        header = tk.Frame(self.root, bg=CLR_BG)
        header.pack(fill=tk.X, padx=14, pady=(12, 6))
        ttk.Label(header, text="信息收集Table",
                  style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"{self.VERSION}  ·  by {self.AUTHOR}",
                  style="Sign.TLabel").pack(side=tk.RIGHT)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        left = tk.Frame(paned, bg=CLR_CARD, highlightthickness=1,
                        highlightbackground=CLR_BORDER,
                        highlightcolor=CLR_BORDER)
        paned.add(left, weight=0)

        tk.Label(left, text="模块列表", bg=CLR_CARD, fg=CLR_PRIMARY,
                 font=("Microsoft YaHei UI", 10, "bold"),
                 anchor="w").pack(fill=tk.X, padx=12, pady=(10, 6))
        tk.Frame(left, height=1, bg=CLR_BORDER).pack(fill=tk.X, padx=10)

        list_wrap = tk.Frame(left, bg=CLR_CARD)
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.module_list = tk.Listbox(
            list_wrap,
            exportselection=False,
            activestyle="none",
            bg=CLR_CARD,
            fg=CLR_TEXT,
            selectbackground=CLR_SELECT_BG,
            selectforeground=CLR_PRIMARY,
            highlightthickness=0,
            borderwidth=0,
            font=("Microsoft YaHei UI", 10),
            width=18)
        self.module_list.pack(fill=tk.BOTH, expand=True)
        self.module_list.bind("<<ListboxSelect>>", self._on_module_select)

        for m in self.modules:
            self.module_list.insert(tk.END, "  " + m.display_name)

        right = tk.Frame(paned, bg=CLR_BG)
        paned.add(right, weight=1)

        self.desc_var = tk.StringVar(value="请选择左侧模块")
        desc = tk.Label(right, textvariable=self.desc_var,
                        bg=CLR_BG, fg=CLR_TEXT_SUB,
                        anchor="w", font=("Microsoft YaHei UI", 9))
        desc.pack(fill=tk.X, pady=(0, 8))

        self.form_card = tk.Frame(right, bg=CLR_CARD,
                                  highlightthickness=1,
                                  highlightbackground=CLR_BORDER,
                                  highlightcolor=CLR_BORDER)
        self.form_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(self.form_card, text="参数配置", bg=CLR_CARD,
                 fg=CLR_PRIMARY,
                 font=("Microsoft YaHei UI", 10, "bold"),
                 anchor="w").pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Frame(self.form_card, height=1, bg=CLR_BORDER).pack(fill=tk.X, padx=10)

        self.form_frame = tk.Frame(self.form_card, bg=CLR_CARD)
        self.form_frame.pack(fill=tk.X, padx=12, pady=10)
        self.form_frame.columnconfigure(1, weight=1)

        bar = tk.Frame(right, bg=CLR_BG)
        bar.pack(fill=tk.X, pady=(0, 8))
        self.run_btn = ttk.Button(bar, text="▶  开始",
                                  style="Accent.TButton",
                                  command=self.on_run)
        self.run_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(bar, text="■  停止",
                                   style="Stop.TButton",
                                   command=self.on_stop,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="清空", command=self.on_clear).pack(side=tk.LEFT)
        ttk.Button(bar, text="导出 CSV",
                   command=self.on_export).pack(side=tk.LEFT, padx=8)

        out_card = tk.Frame(right, bg=CLR_CARD,
                            highlightthickness=1,
                            highlightbackground=CLR_BORDER,
                            highlightcolor=CLR_BORDER)
        out_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(out_card, text="输出", bg=CLR_CARD, fg=CLR_PRIMARY,
                 font=("Microsoft YaHei UI", 10, "bold"),
                 anchor="w").pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Frame(out_card, height=1, bg=CLR_BORDER).pack(fill=tk.X, padx=10)

        out_wrap = tk.Frame(out_card, bg=CLR_CARD)
        out_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.output = tk.Text(
            out_wrap,
            wrap=tk.NONE,
            bg=CLR_INPUT_BG,
            fg=CLR_TEXT,
            insertbackground=CLR_PRIMARY,
            selectbackground=CLR_SELECT_BG,
            selectforeground=CLR_TEXT,
            highlightthickness=1,
            highlightbackground=CLR_BORDER,
            highlightcolor=CLR_PRIMARY,
            relief="flat",
            borderwidth=0,
            padx=8, pady=6,
            font=("Consolas", 10))
        self.output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ys = ttk.Scrollbar(out_wrap, orient=tk.VERTICAL, command=self.output.yview)
        ys.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        xs = ttk.Scrollbar(out_card, orient=tk.HORIZONTAL, command=self.output.xview)
        xs.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))
        self.output.config(yscrollcommand=ys.set, xscrollcommand=xs.set)

        for tag, color in TAG_COLORS.items():
            self.output.tag_config(tag, foreground=color)

    # ---------------- 模块切换 ----------------
    def _on_module_select(self, event=None):
        sel = self.module_list.curselection()
        if not sel:
            return
        self.current_module = self.modules[sel[0]]
        self.desc_var.set(
            f"{self.current_module.display_name} — {self.current_module.description}")
        self._build_form(self.current_module)

    def _build_form(self, module):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.field_vars.clear()

        for i, f in enumerate(module.fields):
            tk.Label(self.form_frame, text=f.label + "：",
                     bg=CLR_CARD, fg=CLR_TEXT,
                     font=("Microsoft YaHei UI", 9)).grid(
                row=i, column=0, sticky="e", padx=(0, 6), pady=5)

            if f.type == "bool":
                var = tk.BooleanVar(value=bool(f.default))
                ttk.Checkbutton(self.form_frame, variable=var).grid(
                    row=i, column=1, sticky="w", padx=6)
            elif f.type == "choice":
                var = tk.StringVar(value=str(f.default))
                ttk.Combobox(self.form_frame, textvariable=var,
                             values=f.choices, state="readonly",
                             width=20).grid(
                    row=i, column=1, sticky="w", padx=6, pady=4)
            else:
                var = tk.StringVar(value=str(f.default))
                show = "*" if f.type == "password" else ""
                ttk.Entry(self.form_frame, textvariable=var,
                          show=show).grid(
                    row=i, column=1, sticky="we", padx=6, pady=4)
                if f.type == "file":
                    ttk.Button(self.form_frame, text="浏览", width=8,
                               command=lambda v=var: self._choose_file(v)).grid(
                        row=i, column=2, padx=4)

            self.field_vars[f.key] = var

            if f.hint:
                tk.Label(self.form_frame, text=f.hint,
                         bg=CLR_CARD, fg=CLR_TEXT_SUB,
                         font=("Microsoft YaHei UI", 8)).grid(
                    row=i, column=3, sticky="w", padx=(6, 0))

    def _choose_file(self, var):
        path = filedialog.askopenfilename(
            title="选择字典文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if path:
            var.set(path)

    # ---------------- 运行控制 ----------------
    def _collect_params(self):
        params = {}
        for f in self.current_module.fields:
            var = self.field_vars[f.key]
            if f.type == "bool":
                params[f.key] = bool(var.get())
            elif f.type == "int":
                try:
                    params[f.key] = int(str(var.get()).strip())
                except ValueError:
                    params[f.key] = 0
            else:
                params[f.key] = str(var.get()).strip()
        return params

    def on_run(self):
        if not self.current_module:
            messagebox.showwarning("提示", "请先选择模块")
            return
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "当前有任务正在运行")
            return

        params = self._collect_params()
        self.stop_event.clear()
        self.rows.clear()
        # 记录本次运行模块的 CSV 列头，切换模块后再导出也不会错位
        self.active_columns = list(self.current_module.csv_columns)

        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._append(f"=== 开始执行 [{self.current_module.display_name}] ===", "ok")

        self.worker = threading.Thread(
            target=self._run_worker,
            args=(self.current_module, params), daemon=True)
        self.worker.start()

    def _run_worker(self, module_cls, params):
        ctx = ModuleContext(
            log_fn=lambda m, lv="info": self.msg_queue.put(("log", m, lv)),
            result_fn=lambda m: self.msg_queue.put(("result", m, "result")),
            stop_fn=self.stop_event.is_set,
            row_fn=lambda d: self.msg_queue.put(("row", d, "")),
        )
        try:
            module_cls(ctx).run(params)
        except Exception as e:
            self.msg_queue.put(("log", f"运行异常: {e}", "error"))
            self.msg_queue.put(("log", traceback.format_exc(), "error"))
        finally:
            self.msg_queue.put(("done", "", ""))

    def on_stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self._append("[!] 已发送停止信号，等待当前任务收尾…", "warn")

    def on_clear(self):
        self.output.delete("1.0", tk.END)
        self.rows.clear()
        self.active_columns = []

    # ---------------- 导出 ----------------
    def on_export(self):
        if self.rows and self.active_columns:
            self._export_csv()
        else:
            self._export_text()

    def _export_csv(self):
        cols = self.active_columns
        default = f"result_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=default,
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for rec in self.rows:
                    writer.writerow([rec.get(c, "") for c in cols])
            messagebox.showinfo("提示", f"已导出 {len(self.rows)} 条到:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _export_text(self):
        content = self.output.get("1.0", tk.END)
        if not content.strip():
            return
        default = f"result_{datetime.now():%Y%m%d_%H%M%S}.txt"
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile=default)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("提示", f"已保存到:\n{path}")

    def _on_close(self):
        self.stop_event.set()
        self.root.destroy()

    # ---------------- 队列轮询 ----------------
    def _poll_queue(self):
        try:
            while True:
                kind, msg, level = self.msg_queue.get_nowait()
                if kind == "done":
                    self.run_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    self._append("=== 执行结束 ===\n", "ok")
                elif kind == "row":
                    self.rows.append(msg)
                else:
                    self._append(msg, level)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _append(self, msg, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.output.insert(tk.END, f"[{ts}] ", "time")
        self.output.insert(tk.END, str(msg) + "\n", level)
        self.output.see(tk.END)


def main():
    root = tk.Tk()
    ToolboxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()