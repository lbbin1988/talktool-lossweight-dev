#!/usr/bin/env python3
"""
截流话术机器人 — Streamlit 网页界面

运行方式：
    streamlit run intercept_web.py

访问地址：http://localhost:8501
"""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import streamlit as st


def main():
    st.set_page_config(
        page_title="🎯 截流话术机器人",
        page_icon="🎯",
        layout="wide",
    )

    # 标题
    st.title("🎯 截流话术机器人")
    st.subheader("基于 截流人设与话术.md + 截流助手Prompt.md")

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")

        # API Key
        api_key = st.text_input("OpenAI API Key", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
        
        # 提供商选择
        provider = st.selectbox("LLM 提供商", ["openai", "anthropic"])
        
        # 输出语言
        lang = st.selectbox("输出语言", [
            ("英文", "en"),
            ("中文", "zh"),
            ("双语", "both"),
        ], format_func=lambda x: x[0])[1]

        # 模式选择
        mode = st.selectbox("工作模式", [
            ("主动截流", "intercept"),
            ("DM 回复", "reply_dm"),
        ], format_func=lambda x: x[0])[1]

    # 主内容区
    col1, col2 = st.columns(2)

    with col1:
        st.header("📝 输入")

        # 帖子内容
        post_content = st.text_area("帖子内容（可选）", height=100)

        # 评论内容
        comment_content = st.text_area("评论内容", height=150, placeholder="输入对方的评论内容...")

        # 额外指令
        extra_instruction = st.text_input("额外指令（可选）", placeholder="例如：语气更亲切一些")

        # 对话历史（仅 DM 模式）
        if mode == "reply_dm":
            st.subheader("📜 对话历史")
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            # 添加新消息
            new_msg = st.text_input("添加对话消息", placeholder="格式：她: xxx 或 我: xxx")
            if st.button("添加消息") and new_msg.strip():
                st.session_state.chat_history.append(new_msg.strip())
            
            # 显示对话历史
            if st.session_state.chat_history:
                for i, msg in enumerate(st.session_state.chat_history):
                    st.code(msg, language="text")
                    if st.button(f"删除 #{i+1}", key=f"del_{i}"):
                        st.session_state.chat_history.pop(i)
                        st.experimental_rerun()

        # 生成按钮
        generate_btn = st.button("🚀 生成话术", type="primary")

    with col2:
        st.header("💬 输出结果")

        if generate_btn:
            if not api_key.strip():
                st.error("请先输入 API Key")
                return
            
            if mode == "intercept" and not comment_content.strip():
                st.error("请输入评论内容")
                return
            
            if mode == "reply_dm" and len(st.session_state.chat_history) < 2:
                st.error("DM 模式需要至少两条对话记录")
                return

            # 加载 Bot 并生成
            with st.spinner("正在分析..."):
                try:
                    from intercept_bot import InterceptBot

                    bot = InterceptBot(
                        provider=provider,
                        api_key=api_key,
                        output_lang=lang,
                    )

                    if mode == "intercept":
                        response = bot.intercept(
                            post_content=post_content,
                            comment_content=comment_content,
                            extra_instruction=extra_instruction or None,
                        )
                    else:
                        response = bot.reply_dm(
                            chat_history=st.session_state.chat_history,
                            extra_instruction=extra_instruction or None,
                        )

                    # 显示结果
                    display_response(response)

                except Exception as e:
                    st.error(f"生成失败：{e}")
                    st.exception(e)

        else:
            st.info("请在左侧输入内容，然后点击「生成话术」按钮")

    # 页脚
    st.markdown("---")
    st.markdown("*基于 截流人设与话术.md + 截流助手Prompt.md*")


def display_response(resp):
    """格式化显示 Bot 响应"""
    # 标签和情绪
    cols = st.columns(4)
    with cols[0]:
        st.metric("🏷️ 标签", resp.tag if resp.tag else "待确认")
    with cols[1]:
        st.metric("😔 情绪", resp.emotion if resp.emotion else "待确认")
    with cols[2]:
        st.metric("🎯 后端", resp.backend if resp.backend else "待确认")
    with cols[3]:
        if resp.round_num:
            st.metric("📋 轮次", f"第{resp.round_num}轮")

    # 生成的话术
    st.subheader("生成话术")
    st.success(resp.reply_text)

    # 备选话术
    if resp.alternatives:
        st.subheader(f"备选话术 ({len(resp.alternatives)} 条)")
        for i, alt in enumerate(resp.alternatives[:3], 1):
            st.info(f"**[{i}]** {alt}")

    # 违禁词检测
    forbidden_hits = [w for w, v in resp.forbidden_check.items() if v]
    if forbidden_hits:
        st.warning(f"⚠️ 检测到 {len(forbidden_hits)} 个风险词：{', '.join(forbidden_hits)}")
    else:
        st.success("✅ 违禁词检测通过")

    # 推理过程
    if resp.reasoning:
        with st.expander("查看推理过程"):
            st.text(resp.reasoning)


if __name__ == "__main__":
    main()
