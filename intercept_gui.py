#!/usr/bin/env python3
"""
截流话术机器人 — Tkinter 图形界面

无需安装任何依赖，使用 Python 自带的 Tkinter 创建友好的聊天窗口。

运行方式：
    python3 intercept_gui.py
"""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
except ImportError:
    print("❌ Tkinter 不可用，请使用 Python 3.x")
    sys.exit(1)


class InterceptBotGUI:
    """截流话术机器人图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎯 截流话术机器人")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # 初始化 Bot（延迟加载，避免启动时出错）
        self.bot = None
        self.bot_loaded = False

        # 对话历史
        self.chat_history = []

        # 语言选项
        self.lang_options = [
            ("英文", "en"),
            ("中文", "zh"),
            ("双语", "both"),
        ]
        self.current_lang = tk.StringVar(value="en")

        # 模式选项
        self.mode_options = [
            ("主动截流", "intercept"),
            ("DM 回复", "reply_dm"),
        ]
        self.current_mode = tk.StringVar(value="intercept")

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        # 顶部工具栏
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # 模式选择
        ttk.Label(toolbar, text="模式：").pack(side=tk.LEFT, padx=2)
        for text, value in self.mode_options:
            ttk.Radiobutton(
                toolbar, text=text, variable=self.current_mode, value=value
            ).pack(side=tk.LEFT, padx=5)

        # 语言选择
        ttk.Label(toolbar, text="语言：").pack(side=tk.LEFT, padx=2)
        for text, value in self.lang_options:
            ttk.Radiobutton(
                toolbar, text=text, variable=self.current_lang, value=value
            ).pack(side=tk.LEFT, padx=5)

        # API Key 输入
        api_frame = ttk.Frame(self.root, padding=5)
        api_frame.pack(fill=tk.X, padx=5)

        ttk.Label(api_frame, text="OpenAI API Key：").pack(side=tk.LEFT)
        self.api_key_entry = ttk.Entry(api_frame, width=60, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.api_key_entry.insert(0, os.environ.get("OPENAI_API_KEY", ""))

        # 主内容区域
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左栏：输入区
        left_frame = ttk.Frame(main_frame, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 帖子内容输入
        post_label = ttk.Label(left_frame, text="帖子内容（可选）：")
        post_label.pack(anchor=tk.W)
        self.post_text = scrolledtext.ScrolledText(left_frame, height=6, wrap=tk.WORD)
        self.post_text.pack(fill=tk.X, pady=2)

        # 评论/消息输入
        comment_label = ttk.Label(left_frame, text="评论内容：")
        comment_label.pack(anchor=tk.W)
        self.comment_text = scrolledtext.ScrolledText(left_frame, height=8, wrap=tk.WORD)
        self.comment_text.pack(fill=tk.X, pady=2)

        # 额外指令
        extra_label = ttk.Label(left_frame, text="额外指令（可选）：")
        extra_label.pack(anchor=tk.W)
        self.extra_entry = ttk.Entry(left_frame, width=50)
        self.extra_entry.pack(fill=tk.X, pady=2)

        # 发送按钮
        send_btn = ttk.Button(left_frame, text="生成话术", command=self._generate_response)
        send_btn.pack(fill=tk.X, pady=5)

        # 清空按钮
        clear_btn = ttk.Button(left_frame, text="清空", command=self._clear_all)
        clear_btn.pack(fill=tk.X)

        # 右栏：输出区
        right_frame = ttk.Frame(main_frame, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # 输出标签
        output_label = ttk.Label(right_frame, text="生成结果：")
        output_label.pack(anchor=tk.W)

        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(right_frame, height=20, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=2)
        self.output_text.config(state=tk.DISABLED)

        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _load_bot(self):
        """延迟加载 Bot"""
        if self.bot_loaded:
            return True

        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("错误", "请先输入 OpenAI API Key")
            return False

        try:
            from intercept_bot import InterceptBot

            self.bot = InterceptBot(
                provider="openai",
                api_key=api_key,
                output_lang=self.current_lang.get(),
            )
            self.bot_loaded = True
            self.status_var.set("Bot 已就绪")
            return True
        except ImportError as e:
            messagebox.showerror("错误", f"依赖缺失：{e}\n请安装：pip install openai")
            return False
        except Exception as e:
            messagebox.showerror("错误", f"初始化失败：{e}")
            return False

    def _generate_response(self):
        """生成截流话术"""
        if not self._load_bot():
            return

        # 更新语言设置
        if self.bot:
            self.bot.output_lang = self.current_lang.get()

        mode = self.current_mode.get()
        post = self.post_text.get("1.0", tk.END).strip()
        comment = self.comment_text.get("1.0", tk.END).strip()
        extra = self.extra_entry.get().strip()

        if not comment:
            messagebox.showwarning("警告", "请输入评论内容")
            return

        self.status_var.set("正在分析...")
        self.root.update_idletasks()

        try:
            if mode == "intercept":
                # 主动截流模式
                response = self.bot.intercept(
                    post_content=post,
                    comment_content=comment,
                    extra_instruction=extra or None,
                )
            else:
                # DM 回复模式
                # 将评论作为对话历史处理
                self.chat_history.append(f"她: {comment}")
                if len(self.chat_history) < 2:
                    messagebox.showwarning("警告", "DM 模式需要至少两条对话记录")
                    return
                response = self.bot.reply_dm(
                    chat_history=self.chat_history,
                    extra_instruction=extra or None,
                )
                self.chat_history.append(f"我: {response.reply_text}")

            # 格式化输出
            output = self._format_response(response)
            self._display_output(output)

            # 更新状态
            forbidden_hits = [w for w, v in response.forbidden_check.items() if v]
            if forbidden_hits:
                self.status_var.set(f"完成 - 发现 {len(forbidden_hits)} 个风险词")
            else:
                self.status_var.set("完成")

        except Exception as e:
            messagebox.showerror("错误", f"生成失败：{e}")
            self.status_var.set("生成失败")

    def _format_response(self, resp):
        """格式化 Bot 响应"""
        lines = []
        lines.append("=" * 50)
        if resp.tag:
            lines.append(f"🏷️  标签: {resp.tag}")
        if resp.emotion:
            lines.append(f"😔 情绪: {resp.emotion}")
        if resp.backend:
            lines.append(f"🎯 后端: {resp.backend}")
        if resp.round_num:
            lines.append(f"📋 轮次: 第{resp.round_num}轮")
        lines.append("-" * 50)
        lines.append("💬 生成话术:")
        lines.append(resp.reply_text)
        if resp.alternatives:
            lines.append("\n🔄 备选话术:")
            for i, alt in enumerate(resp.alternatives[:3], 1):
                lines.append(f"  [{i}] {alt}")
        lines.append("\n✅ 违禁词检测: 通过")
        lines.append("=" * 50)
        return "\n".join(lines)

    def _display_output(self, text):
        """显示输出结果"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.config(state=tk.DISABLED)

    def _clear_all(self):
        """清空所有输入"""
        self.post_text.delete("1.0", tk.END)
        self.comment_text.delete("1.0", tk.END)
        self.extra_entry.delete(0, tk.END)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.chat_history = []
        self.status_var.set("已清空")


def main():
    root = tk.Tk()
    app = InterceptBotGUI(root)

    # 添加窗口图标（如果可用）
    try:
        root.iconbitmap(default="")
    except:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
