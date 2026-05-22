#!/usr/bin/env python3
"""
截流话术机器人 — CLI 交互界面

用法：
    # 交互模式（推荐）
    python3 intercept_cli.py

    # 单次截流模式
    python3 intercept_cli.py --intercept "I can't stop eating sweets, help" --post "Weight loss journey..."

    # DM 回复模式
    python3 intercept_cli.py --dm --history "她: hey! what helped you?" "我: ..."

    # 指定 LLM 和语言
    python3 intercept_cli.py --provider anthropic --lang zh --intercept "评论内容"

    # 从文件读取对话历史
    python3 intercept_cli.py --dm --file chat_history.txt
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from intercept_bot import InterceptBot, BotResponse


BANNER = """
╔════════════════════════════════════════════════════╗
║        🎯 截流话术机器人 — Intercept Bot v1.0       ║
║   基于 截流人设与话术.md + 截流助手Prompt.md         ║
╚════════════════════════════════════════════════════╝
"""


def print_response(resp: BotResponse, verbose: bool = True):
    """格式化输出 Bot 响应"""
    print("\n" + "=" * 50)
    if resp.tag:
        print(f"  🏷️  标签: {resp.tag}", end="")
        if resp.emotion:
            print(f"  |  😔 情绪: {resp.emotion}", end="")
        if resp.backend:
            print(f"  |  🎯 后端: {resp.backend}", end="")
        print()
    if resp.round_num:
        print(f"  📋 当前轮次: 第{resp.round_num}轮")

    if verbose and resp.reasoning:
        print(f"\n  📝 推理过程:")
        for line in resp.reasoning.split("\n")[:6]:
            if line.strip():
                print(f"     {line}")

    print(f"\n  💬 生成话术:")
    print(f"  ─────────────────────────────")
    print(f"  {resp.reply_text}")
    print(f"  ─────────────────────────────")

    if resp.alternatives:
        print(f"\n  🔄 备选话术 ({len(resp.alternatives)} 条):")
        for i, alt in enumerate(resp.alternatives[:3], 1):
            print(f"     [{i}] {alt}")

    forbidden_hits = [w for w, v in resp.forbidden_check.items() if v]
    if forbidden_hits:
        print(f"\n  ⚠️  违禁词检测: 发现 {len(forbidden_hits)} 个风险词 → {forbidden_hits}")
    else:
        print(f"\n  ✅ 违禁词检测: 通过")

    print()


def interactive_mode(bot: InterceptBot):
    """交互式 CLI 模式"""
    print(BANNER)

    while True:
        print("\n" + "-" * 50)
        print("  [1] 主动截流 (看评论 → 生成话术)")
        print("  [2] DM 回复 (对话历史 → 下一步)")
        print("  [3] 翻译话术 (中英互译)")
        print("  [4] 切换语言 (当前: {})".format(
            {"en": "英文", "zh": "中文", "both": "双语"}.get(bot.output_lang, bot.output_lang)
        ))
        print("  [q] 退出")
        print("-" * 50)

        choice = input("\n  选择模式 > ").strip().lower()

        if choice == "q":
            print("\n  再见! 👋\n")
            break

        elif choice == "1":
            print("\n--- 主动截流模式 ---")
            post = input("  帖子内容 (可直接回车跳过) > ").strip()
            comment = input("  对方评论 > ").strip()
            extra = input("  额外指令 (可选) > ").strip()

            if not comment:
                print("  ⚠️  评论内容不能为空")
                continue

            print("\n  🤖 正在分析...")
            try:
                resp = bot.intercept(post_content=post, comment_content=comment, extra_instruction=extra or None)
                print_response(resp)
            except Exception as e:
                print(f"  ❌ 错误: {e}")

        elif choice == "2":
            print("\n--- DM 回复模式 ---")
            print("  输入对话历史 (每行一条，空行结束):")
            history = []
            while True:
                line = input(f"    [{len(history)+1}] > ").strip()
                if not line:
                    break
                history.append(line)

            if len(history) < 2:
                print("  ⚠️  至少需要 2 条对话记录")
                continue

            extra = input("  额外指令 (可选) > ").strip()

            print("\n  🤖 正在分析...")
            try:
                resp = bot.reply_dm(chat_history=history, extra_instruction=extra or None)
                print_response(resp)
            except Exception as e:
                print(f"  ❌ 错误: {e}")

        elif choice == "3":
            print("\n--- 翻译模式 ---")
            text = input("  待翻译文本 > ").strip()
            target = input("  目标语言 (zh/en) > ").strip() or ("zh" if bot.output_lang == "en" else "en")
            if not text:
                print("  ⚠️  文本不能为空")
                continue
            try:
                result = bot.translate_reply(text, target)
                print(f"\n  🌐 翻译结果:\n  {result}\n")
            except Exception as e:
                print(f"  ❌ 错误: {e}")

        elif choice == "4":
            lang_map = {"en": "zh", "zh": "en", "both": "en"}
            current = bot.output_lang
            bot.output_lang = lang_map.get(current, "both")
            print(f"  ✅ 已切换为: {bot.output_lang}")


def single_intercept_mode(args, bot: InterceptBot):
    """单次截流命令行模式"""
    post = args.post or ""
    comment = args.intercept

    print(f"\n🤖 分析评论: {comment[:60]}{'...' if len(comment) > 60 else ''}")
    resp = bot.quick_intercept(comment, post)
    print_response(resp, verbose=not args.quiet)

    if args.json_output:
        print(json.dumps(resp.to_dict(), ensure_ascii=False, indent=2))


def dm_mode(args, bot: InterceptBot):
    """DM 回复命令行模式"""
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ 文件不存在: {filepath}")
            return
        history = filepath.read_text(encoding="utf-8").strip().split("\n")
        history = [l.strip() for l in history if l.strip()]
    else:
        history = args.history

    if not history:
        print("❌ 对话历史为空")
        return

    print(f"\n🤖 分析对话 ({len(history)} 条消息)")
    resp = bot.reply_dm(history)
    print_response(resp, verbose=not args.quiet)

    if args.json_output:
        print(json.dumps(resp.to_dict(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="截流话术机器人 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 intercept_cli.py                              # 交互模式
  python3 intercept_cli.py -i "can't stop sweets"       # 快速截流
  python3 intercept_cli.py -i "can't stop sweets" -p "post content"
  python3 intercept_cli.py --dm --history "她:hey" "我:hi" "她:help"
  python3 intercept_cli.py --dm --file chat.txt          # 从文件读对话
  python3 intercept_cli.py --provider anthropic --lang zh -i "评论"
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--intercept", metavar="COMMENT", help="单次截流模式：提供评论内容")
    group.add_argument("--dm", action="store_true", help="DM 回复模式")
    group.add_argument("-t", "--translate", metavar="TEXT", help="翻译模式：翻译指定文本")

    parser.add_argument("-p", "--post", metavar="CONTENT", default="", help="帖子内容 (配合 -i 使用)")
    parser.add_argument("--history", nargs="+", metavar="MSG", help="对话历史 (配合 --dm 使用)")
    parser.add_argument("--file", metavar="PATH", help="从文件读取对话历史 (配合 --dm 使用)")

    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai",
                        help="LLM 提供商 (默认: openai)")
    parser.add_argument("--model", metavar="NAME", help="模型名称 (默认自动选择)")
    parser.add_argument("--lang", choices=["en", "zh", "both"], default="en",
                        help="输出语言: en=英文 zh=中文 both=双语 (默认: en)")
    parser.add_argument("--api-key", metavar="KEY", help="API Key (默认从环境变量读取)")
    parser.add_argument("--base-url", metavar="URL", help="OpenAI 兼容 API 地址")
    parser.add_argument("-q", "--quiet", action="store_true", help="静默模式：只输出话术")
    parser.add_argument("--json", dest="json_output", action="store_true", help="JSON 格式输出")
    parser.add_argument("--temp", type=float, default=0.7, help="温度 0-1 (默认: 0.7)")

    args = parser.parse_args()

    try:
        bot = InterceptBot(
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            output_lang=args.lang,
            temperature=args.temp,
        )
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        print("   安装: pip install openai  或  pip install anthropic")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

    if args.intercept:
        single_intercept_mode(args, bot)
    elif args.dm:
        dm_mode(args, bot)
    elif args.translate:
        target = "zh" if args.lang == "en" else "en"
        result = bot.translate_reply(args.translate, target)
        print(result)
    else:
        interactive_mode(bot)


if __name__ == "__main__":
    main()
