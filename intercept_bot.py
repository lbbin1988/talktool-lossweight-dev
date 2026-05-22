"""
截流话术机器人 — 核心模块

基于截流人设与话术.md + 截流助手Prompt.md 实现的通用截流话术生成器。
支持双 LLM 后端（OpenAI / Anthropic）+ 双语中英文互译。

使用方式：
    from intercept_bot import InterceptBot

    bot = InterceptBot(provider="openai")  # 或 "anthropic"

    # 模式1：主动截流（看评论 → 生成话术）
    result = bot.intercept(post_content="...", comment_content="...")

    # 模式2：DM 回复（对话历史 → 生成下一步回复）
    result = bot.reply_dm(chat_history=["她: ...", "我: ...", "她: ..."])
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field


SCRIPT_DIR = Path(__file__).parent.resolve()
PERSONA_FILE = SCRIPT_DIR / "截流人设与话术.md"
PROMPT_FILE = SCRIPT_DIR / "截流助手Prompt.md"


@dataclass
class BotResponse:
    """Bot 返回结果"""

    tag: str = ""                    # 识别标签 A/B/C/D
    emotion: str = ""                # 情绪真相
    backend: str = ""                # 倾向后端
    round_num: int = 0               # 当前轮次（仅 DM 模式）
    reply_text: str = ""             # 生成的回复/话术
    alternatives: List[str] = field(default_factory=list)  # 备选话术
    forbidden_check: Dict[str, bool] = field(default_factory=dict)  # 违禁词检查
    reasoning: str = ""              # 推理过程
    raw_response: str = ""           # LLM 原始返回

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "emotion": self.emotion,
            "backend": self.backend,
            "round_num": self.round_num,
            "reply_text": self.reply_text,
            "alternatives": self.alternatives,
            "forbidden_check": self.forbidden_check,
            "reasoning": self.reasoning,
        }


class InterceptBot:
    """
    截流话术机器人

    支持两种模式：
    - intercept: 主动截流（Prompt 1）— 看帖子/评论 → 生成截流话术
    - reply_dm: DM 回复（Prompt 2）— 对话历史 → 生成下一步回复

    支持双语：
    - 输入可以是中文或英文
    - 输出默认英文（Ins 截流用），可切换为中文
    """

    FORBIDDEN_WORDS = [
        "lose weight fast", "miracle", "instant result",
        "fat burner", "appetite suppressant", "detox", "diet pill",
        "slimming tea", "before/after", "weight loss product",
        "burn fat", "slim down", "guarantee", "results",
    ]

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        output_lang: Literal["en", "zh", "both"] = "en",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        Args:
            provider: LLM 提供商 ("openai" | "anthropic")
            model: 模型名称，默认自动选择
            api_key: API Key，默认从环境变量读取
            base_url: OpenAI 兼容 API 的 base_url（Anthropic 不需要）
            output_lang: 输出语言 ("en"=英文 | "zh"=中文 | "both"=双语)
            temperature: 生成温度（0-1），越高越有创意
            max_tokens: 最大生成 token 数
        """
        self.provider = provider
        self.output_lang = output_lang
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = None
        self._model_name = model or self._default_model()
        self._api_key = api_key or os.environ.get(
            "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        )
        self._base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL"
        )

        self._persona_text = self._load_file(PERSONA_FILE)
        self._prompt1_text = self._extract_prompt_block(PROMPT_FILE, "Prompt 1")
        self._prompt2_text = self._extract_prompt_block(PROMPT_FILE, "Prompt 2")

        self._init_client()

    def _default_model(self) -> str:
        if self.provider == "openai":
            return os.environ.get("OPENAI_MODEL", "gpt-4o")
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    def _init_client(self):
        if self.provider == "openai":
            try:
                from openai import OpenAI
                kwargs = {"api_key": self._api_key}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                raise ImportError(
                    "需要安装 openai 包：pip install openai\n"
                    "或改用 provider='anthropic' 并安装 anthropic 包"
                )
        else:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "需要安装 anthropic 包：pip install anthropic\n"
                    "或改用 provider='openai' 并安装 openai 包"
                )

    @staticmethod
    def _load_file(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_prompt_block(file_path: Path, prompt_name: str) -> str:
        content = InterceptBot._load_file(file_path)
        pattern = rf"## {re.escape(prompt_name)}.*?```\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        fallback_pattern = rf"## {re.escape(prompt_name)}"
        match2 = re.search(fallback_pattern, content)
        if match2:
            start = match2.end()
            next_section = re.search(r"\n## ", content[start:])
            end = next_section.start() + start if next_section else len(content)
            code_match = re.search(r"```\n(.*?)```", content[start:end], re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            return content[start:end].strip()
        raise ValueError(f"无法提取 {prompt_name} 从 {file_path}")

    def _build_system_prompt(self, mode: str, extra_instruction: str = "") -> str:
        base = f"""{self._persona_text}

你是截流话术机器人。基于以上人设和以下 Prompt 规则生成回复。
"""
        if mode == "intercept":
            base += f"\n{self._prompt1_text}\n"
        else:
            base += f"\n{self._prompt2_text}\n"

        lang_instruction = ""
        if self.output_lang == "zh":
            lang_instruction = "\n\n【语言要求】请用中文输出所有话术和推理。如果原话术是英文，请翻译成中文。保持口语化、姐妹聊天的语气。\n"
        elif self.output_lang == "both":
            lang_instruction = "\n\n【语言要求】请同时输出中文和英文版本的话术。格式：先英文原文，再中文翻译。保持两种语言的语气一致。\n"

        base += lang_instruction
        if extra_instruction:
            base += f"\n{extra_instruction}\n"

        return base

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        if self.provider == "openai":
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or ""
        else:
            response = self._client.messages.create(
                model=self._model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text

    def _check_forbidden(self, text: str) -> Dict[str, bool]:
        text_lower = text.lower()
        results = {}
        for word in self.FORBIDDEN_WORDS:
            results[word] = word.lower() in text_lower
        return results

    def _parse_response(self, raw: str, mode: str) -> BotResponse:
        resp = BotResponse(raw_response=raw)

        tag_match = re.search(r"标签[：:]\s*([ABCD])", raw)
        if tag_match:
            resp.tag = tag_match.group(1)

        emotion_keywords = ["罪恶感循环", "自我厌弃", "耗竭感", "自我否定"]
        for kw in emotion_keywords:
            if kw in raw:
                resp.emotion = kw
                break

        backend_match = re.search(r"(?:后端|倾向)[：:]\s*(产品型|训练营|规划师)", raw)
        if backend_match:
            resp.backend = backend_match.group(1)

        if mode == "reply_dm":
            round_match = re.search(r"第(\d+)轮", raw)
            if round_match:
                resp.round_num = int(round_match.group(1))

        reply_patterns = [
            r"(?:评论区话术|截流话术|DM话术|回复)[^\n]*?[：:\d]\s*\n?\s*((?:(?!\n\n)[.)\n])*?(?:[?!]|$))",
            r"((?:girl|hey|i'|omg|same|used to|the moment|your|you're|still eat|want me|no pressure)[^.!?]*[.!?])",
        ]
        for pattern in reply_patterns:
            matches = re.findall(pattern, raw, re.IGNORECASE | re.DOTALL)
            if matches:
                cleaned = [m.strip() for m in matches if len(m.strip()) > 10]
                if cleaned:
                    resp.reply_text = cleaned[0]
                    resp.alternatives = cleaned[1:]
                    break

        if not resp.reply_text:
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            for line in lines:
                if len(line) > 15 and not line.startswith("#") and not line.startswith("|"):
                    resp.reply_text = line
                    break

        reasoning_lines = []
        capture = False
        for line in raw.split("\n"):
            stripped = line.strip()
            if re.match(r"^\d+\.", stripped) or "判断" in stripped or "依据" in stripped:
                capture = True
            if capture:
                reasoning_lines.append(stripped)
                if len(reasoning_lines) > 8:
                    break
        resp.reasoning = "\n".join(reasoning_lines)

        resp.forbidden_check = self._check_forbidden(raw)

        return resp

    def intercept(
        self,
        post_content: str,
        comment_content: str,
        extra_instruction: str = "",
    ) -> BotResponse:
        """
        主动截流模式（Prompt 1）

        根据帖子内容和评论，生成截流话术。

        Args:
            post_content: 帖子内容（文字）
            comment_content: 对方评论内容
            extra_instruction: 额外指令（如指定标签、调整语气等）

        Returns:
            BotResponse: 包含标签识别、情绪判断、话术等
        """
        system = self._build_system_prompt("intercept", extra_instruction)

        user_msg = f"""帖子内容：
{post_content}

评论内容：
{comment_content}

请按 Prompt 要求执行完整的分析流程。"""

        raw = self._call_llm(system, user_msg)
        return self._parse_response(raw, "intercept")

    def reply_dm(
        self,
        chat_history: List[str],
        extra_instruction: str = "",
    ) -> BotResponse:
        """
        DM 回复模式（Prompt 2）

        根据对话历史，生成下一步私信回复。

        Args:
            chat_history: 对话历史列表 ["她: xxx", "我: xxx", "她: yyy"]
            extra_instruction: 额外指令

        Returns:
            BotResponse: 包含轮次判断、标签、情绪、回复话术
        """
        system = self._build_system_prompt("reply_dm", extra_instruction)

        history_str = "\n".join(chat_history)

        user_msg = f"""对话历史：
{history_str}

请按 Prompt 2 的 3 轮漏斗逻辑执行分析并生成回复。"""

        raw = self._call_llm(system, user_msg)
        return self._parse_response(raw, "reply_dm")

    def quick_intercept(self, comment: str, post_context: str = "") -> BotResponse:
        """快速截流：只需提供评论内容，帖子内容可选"""
        return self.intercept(
            post_content=post_context or "(未提供帖子上下文)",
            comment_content=comment,
        )

    def translate_reply(self, text: str, target_lang: Literal["zh", "en"] = "zh") -> str:
        """
        将生成的话术翻译为目标语言

        Args:
            text: 英文或中文话术
            target_lang: 目标语言 "zh" 或 "en"

        Returns:
            翻译后的文本
        """
        translate_prompt = (
            f"将以下截流话术翻译为{'中文' if target_lang == 'zh' else 'English'}。"
            f"\n要求：保持口语化、姐妹聊天语气、灵性翻转的表达风格不变。"
            f"\n不要添加解释，直接输出翻译结果。\n\n原文：\n{text}"
        )
        return self._call_llm(translate_prompt, "请翻译：")


def create_bot(
    provider: str = "openai",
    **kwargs,
) -> InterceptBot:
    """工厂函数：快速创建 Bot 实例"""
    return InterceptBot(provider=provider, **kwargs)


if __name__ == "__main__":
    print("=" * 60)
    print("  截流话术机器人 — 测试模式")
    print("=" * 60)

    print("\n检查依赖...")
    try:
        import openai
        print("  ✅ openai 已安装")
    except ImportError:
        print("  ⚠️  openai 未安装")
    try:
        import anthropic
        print("  ✅ anthropic 已安装")
    except ImportError:
        print("  ⚠️  anthropic 未安装")

    print(f"\n检查 Prompt 文件...")
    print(f"  ✅ {PERSONA_FILE.name}: {PERSONA_FILE.stat().st_size:,} bytes")
    print(f"  ✅ {PROMPT_FILE.name}: {PROMPT_FILE.stat().st_size:,} bytes")

    print("\n提示：运行 python3 intercept_cli.py 启动交互式 CLI")
    print("      或运行 python3 intercept_api.py 启动 Web API 服务")
