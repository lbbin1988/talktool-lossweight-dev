#!/usr/bin/env python3
"""
截流话术机器人 — Web API 服务

启动方式：
    python3 intercept_api.py                    # 默认 http://localhost:8000
    python3 intercept_api.py --port 9000        # 指定端口
    python3 intercept_api.py --provider anthropic  # 使用 Anthropic

API 端点：
    POST /api/intercept     — 主动截流（看评论 → 生成话术）
    POST /api/reply-dm      — DM 回复（对话历史 → 下一步）
    POST /api/translate     — 中英互译
    GET  /health            — 健康检查
    GET  /                  — API 文档首页

调用示例 (curl)：
    curl -X POST http://localhost:8000/api/intercept \
      -H "Content-Type: application/json" \
      -d '{"comment": "I can't stop eating sweets", "lang": "zh"}'

    curl -X POST http://localhost:8000/api/reply-dm \
      -H "Content-Type: application/json" \
      -d '{"history": ["她: hey what helped you", "我: ..."], "lang": "en"}'
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from typing import Optional, List
from intercept_bot import InterceptBot, BotResponse

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError:
    print("❌ 缺少依赖，请安装：pip install fastapi uvicorn")
    print("   或仅使用 CLI 模式：python3 intercept_cli.py")
    sys.exit(1)


app = FastAPI(
    title="截流话术机器人 API",
    description="基于截流人设与话术的通用截流话术生成服务",
    version="1.0.0",
)

_bot: Optional[InterceptBot] = None


class InterceptRequest(BaseModel):
    """主动截流请求"""

    comment: str = Field(..., description="对方评论内容")
    post: str = Field("", description="帖子内容（可选）")
    lang: str = Field("en", description="输出语言: en/zh/both")
    extra: str = Field("", description="额外指令（可选）")


class ReplyDmRequest(BaseModel):
    """DM 回复请求"""

    history: List[str] = Field(..., min_length=2, description="对话历史列表")
    lang: str = Field("en", description="输出语言: en/zh/both")
    extra: str = Field("", description="额外指令（可选）")


class TranslateRequest(BaseModel):
    """翻译请求"""

    text: str = Field(..., description="待翻译文本")
    target_lang: str = Field("zh", description="目标语言: zh/en")


class BotConfig(BaseModel):
    """Bot 配置"""

    provider: str = Field("openai", description="LLM 提供商: openai/anthropic")
    model: Optional[str] = Field(None, description="模型名称")
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="OpenAI 兼容 API 地址")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="生成温度")


def get_bot() -> InterceptBot:
    global _bot
    if _bot is None:
        _bot = InterceptBot()
    return _bot


@app.get("/")
async def root():
    return {
        "service": "截流话术机器人 API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/intercept": "主动截流 — 看评论生成话术",
            "POST /api/reply-dm": "DM 回复 — 对话历史生成下一步",
            "POST /api/translate": "中英互译",
            "GET /health": "健康检查",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    try:
        bot = get_bot()
        return {"status": "ok", "provider": bot.provider, "model": bot._model_name}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bot 未就绪: {e}")


@app.post("/api/intercept", response_model=dict)
async def api_intercept(req: InterceptRequest):
    """
    主动截流接口

    根据帖子内容和评论，自动识别标签和情绪真相，生成截流话术。
    """
    try:
        bot = get_bot()
        if req.lang != bot.output_lang:
            bot.output_lang = req.lang

        resp = bot.intercept(
            post_content=req.post,
            comment_content=req.comment,
            extra_instruction=req.extra or None,
        )
        return resp.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reply-dm", response_model=dict)
async def api_reply_dm(req: ReplyDmRequest):
    """
    DM 回复接口

    根据对话历史，按 3 轮漏斗逻辑判断当前轮次并生成下一步回复。
    """
    try:
        bot = get_bot()
        if req.lang != bot.output_lang:
            bot.output_lang = req.lang

        resp = bot.reply_dm(
            chat_history=req.history,
            extra_instruction=req.extra or None,
        )
        return resp.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate", response_model=dict)
async def api_translate(req: TranslateRequest):
    """
    翻译接口

    将截流话术在中英文之间互译，保持语气风格不变。
    """
    try:
        bot = get_bot()
        result = bot.translate_reply(req.text, req.target_lang)
        return {"original": req.text, "translated": result, "target_lang": req.target_lang}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(config: BotConfig):
    """
    更新 Bot 配置（运行时切换 LLM 后端）
    """
    global _bot
    try:
        _bot = InterceptBot(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
        )
        return {"status": "ok", "provider": config.provider, "model": _bot._model_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000, **kwargs):
    import uvicorn

    global _bot
    _bot = InterceptBot(**{k: v for k, v in kwargs.items() if v is not None})

    print("""
╔════════════════════════════════════════════════════╗
║     🎯 截流话术机器人 API 服务已启动               ║
╚════════════════════════════════════════════════════╝

  地址:  http://{}:{}
  文档:  http://{}:{}/docs
  截流:  POST /api/intercept
  DM:   POST /api/reply-dm
  翻译:  POST /api/translate

  按 Ctrl+C 停止服务
""".format(host, port, host, port))

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="截流话术机器人 Web API")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="端口号 (默认: 8000)")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--temp", type=float, default=None)

    args = parser.parse_args()

    kwargs = {}
    if args.provider:
        kwargs["provider"] = args.provider
    if args.model:
        kwargs["model"] = args.model
    if args.temp:
        kwargs["temperature"] = args.temp

    run_server(host=args.host, port=args.port, **kwargs)
