#!/usr/bin/env python3
"""
截流话术机器人 — 本地模型网页版（修复版）

运行方式：
    python3 intercept_local_web.py

首次运行会自动下载 Qwen2-0.5B-Chat 模型（约 1GB）
"""

import sys
import os
import threading
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# 全局状态
bot = None
is_model_loading = False
load_error = None
load_lock = threading.Lock()


def load_model_async():
    """异步加载模型"""
    global bot, is_model_loading, load_error
    
    try:
        from intercept_bot_local import LocalInterceptBot
        bot = LocalInterceptBot(output_lang='auto')
        load_error = None
    except Exception as e:
        load_error = str(e)
        print(f"模型加载失败: {e}")
    finally:
        is_model_loading = False


@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 截流话术机器人</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2rem; margin-bottom: 10px; }
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover:not(:disabled) { opacity: 0.9; }
        .btn:disabled { 
            background: #ccc; 
            cursor: not-allowed;
            opacity: 0.6;
        }
        .btn-sm { padding: 6px 12px; font-size: 0.875rem; }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        textarea { min-height: 100px; resize: vertical; }
        label { font-weight: 500; margin-bottom: 8px; display: block; }
        .tab {
            padding: 10px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            margin-right: 10px;
            display: inline-block;
        }
        .tab.active { background: #667eea; color: white; border-color: #667eea; }
        .mode-panel { display: none; }
        .mode-panel.active { display: block; }
        .chat-message {
            padding: 12px 16px;
            border-radius: 16px;
            margin-bottom: 10px;
            max-width: 80%;
        }
        .chat-message.her {
            background: #f0f0f0;
            align-self: flex-start;
        }
        .chat-message.me {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            align-self: flex-end;
        }
        .chat-messages {
            display: flex;
            flex-direction: column;
            padding: 16px;
            background: #f8f9fa;
            border-radius: 12px;
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 15px;
        }
        .chat-input {
            display: flex;
            gap: 10px;
        }
        .chat-input textarea {
            flex: 1;
            min-height: 60px;
            margin-bottom: 0;
        }
        .result { background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 15px; }
        .success { background: #d4edda; color: #155724; }
        .warning { background: #fff3cd; color: #856404; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px; }
        .metric { background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; }
        .model-status {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.875rem;
            margin-bottom: 15px;
        }
        .status-loading { 
            background: #fff3cd; 
            color: #856404;
            animation: pulse 1.5s infinite;
        }
        .status-ready { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 8px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 截流话术机器人</h1>
            <p>本地开源模型 · 无需 API Key · 完全免费</p>
        </div>

        <div class="card">
            <div id="model_status" class="model-status status-loading">
                <span class="loading-spinner"></span>
                正在下载并加载模型...
            </div>
            
            <div style="margin-bottom: 15px;">
                <span class="tab active" onclick="switchMode('intercept')">🎯 主动截流</span>
                <span class="tab" onclick="switchMode('chat')">💬 DM 对话</span>
            </div>

            <div style="margin-bottom: 15px;">
                <label style="display: inline-block; margin-right: 10px;">输出语言：</label>
                <select id="output_lang" style="display: inline-block; width: auto; padding: 8px 16px;">
                    <option value="auto">🌐 自动识别</option>
                    <option value="zh">🇨🇳 中文</option>
                    <option value="en">🇬🇧 英文</option>
                    <option value="both">🌍 双语</option>
                </select>
            </div>

            <!-- 主动截流模式 -->
            <div id="intercept_panel" class="mode-panel active">
                <label>帖子内容（可选）</label>
                <textarea id="post" placeholder="输入帖子内容..."></textarea>
                
                <label>评论内容</label>
                <textarea id="comment" placeholder="输入对方的评论..."></textarea>

                <button id="intercept_btn" class="btn" style="width:100%" onclick="generateIntercept()" disabled>
                    <span class="loading-spinner" id="intercept_spinner"></span>
                    🚀 生成话术
                </button>
            </div>

            <!-- DM 对话模式 -->
            <div id="chat_panel" class="mode-panel">
                <div class="chat-messages" id="chat_messages">
                    <div class="chat-message her">她: 嗨！你是怎么瘦下来的？</div>
                    <div class="chat-message me">我: 哈哈，其实我也爱吃甜！后来改变了和食物的关系～</div>
                </div>
                
                <div class="chat-input">
                    <textarea id="chat_input" placeholder="输入对方的回复..."></textarea>
                    <button id="chat_btn" class="btn" onclick="sendChat()" disabled>
                        <span class="loading-spinner" id="chat_spinner"></span>
                        发送
                    </button>
                </div>
                
                <button class="btn btn-sm" style="margin-top: 10px;" onclick="clearChat()">清空对话</button>
            </div>
        </div>

        <div id="result_card" class="card" style="display: none;">
            <h3>💬 生成结果</h3>
            <div class="metrics" id="metrics"></div>
            <div id="reply"></div>
            <div id="alternatives"></div>
            <div id="forbidden"></div>
        </div>
    </div>

    <script>
        var chat_history = [
            "她: 嗨！你是怎么瘦下来的？",
            "我: 哈哈，其实我也爱吃甜！后来改变了和食物的关系～"
        ];

        function switchMode(mode) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            document.getElementById('intercept_panel').classList.remove('active');
            document.getElementById('chat_panel').classList.remove('active');
            document.getElementById(mode + '_panel').classList.add('active');
        }

        async function checkModelStatus() {
            try {
                var response = await fetch('/api/model_status');
                var data = await response.json();
                
                if (data.status === 'ready') {
                    document.getElementById('model_status').innerHTML = '✅ 模型已就绪';
                    document.getElementById('model_status').className = 'model-status status-ready';
                    document.getElementById('intercept_btn').disabled = false;
                    document.getElementById('chat_btn').disabled = false;
                    document.getElementById('intercept_spinner').style.display = 'none';
                    document.getElementById('chat_spinner').style.display = 'none';
                } else if (data.status === 'loading') {
                    document.getElementById('model_status').innerHTML = 
                        '<span class="loading-spinner"></span>正在下载并加载模型...';
                    document.getElementById('model_status').className = 'model-status status-loading';
                    setTimeout(checkModelStatus, 2000);
                } else if (data.status === 'error') {
                    document.getElementById('model_status').innerHTML = '❌ 模型加载失败: ' + data.error;
                    document.getElementById('model_status').className = 'model-status status-error';
                }
            } catch (e) {
                setTimeout(checkModelStatus, 2000);
            }
        }

        async function generateIntercept() {
            var post = document.getElementById('post').value.trim();
            var comment = document.getElementById('comment').value.trim();
            var lang = document.getElementById('output_lang').value;

            if (!comment) {
                alert('请输入评论内容');
                return;
            }

            document.getElementById('result_card').style.display = 'none';
            document.getElementById('intercept_btn').disabled = true;
            document.getElementById('intercept_spinner').style.display = 'inline-block';

            try {
                var response = await fetch('/api/intercept', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ post: post, comment: comment, lang: lang })
                });
                var data = await response.json();
                
                if (data.error) {
                    alert('生成失败: ' + data.error);
                } else {
                    showResult(data);
                }
            } catch (e) {
                alert('生成失败: ' + e.message);
            } finally {
                document.getElementById('intercept_btn').disabled = false;
                document.getElementById('intercept_spinner').style.display = 'none';
            }
        }

        async function sendChat() {
            var input = document.getElementById('chat_input').value.trim();
            var lang = document.getElementById('output_lang').value;
            if (!input) return;

            chat_history.push('她: ' + input);
            addMessage('her', '她: ' + input);
            document.getElementById('chat_input').value = '';
            
            document.getElementById('chat_btn').disabled = true;
            document.getElementById('chat_spinner').style.display = 'inline-block';

            try {
                var response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ history: chat_history, lang: lang })
                });
                var data = await response.json();
                
                if (data.error) {
                    alert('生成失败: ' + data.error);
                } else {
                    chat_history.push('我: ' + data.reply_text);
                    addMessage('me', '我: ' + data.reply_text);
                    showResult(data);
                }
            } catch (e) {
                alert('生成失败: ' + e.message);
            } finally {
                document.getElementById('chat_btn').disabled = false;
                document.getElementById('chat_spinner').style.display = 'none';
            }
        }

        function addMessage(type, text) {
            var messages = document.getElementById('chat_messages');
            var msg = document.createElement('div');
            msg.className = 'chat-message ' + type;
            msg.textContent = text;
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }

        function clearChat() {
            chat_history = [];
            document.getElementById('chat_messages').innerHTML = '';
            document.getElementById('result_card').style.display = 'none';
        }

        function showResult(data) {
            document.getElementById('result_card').style.display = 'block';
            
            var lang_display = data.detected_language === 'zh' ? '中文' : data.detected_language === 'en' ? '英文' : '未知';
            document.getElementById('metrics').innerHTML = 
                '<div class="metric">标签: ' + (data.tag || '待确认') + '</div>' +
                '<div class="metric">情绪: ' + (data.emotion || '待确认') + '</div>' +
                '<div class="metric">检测语言: ' + lang_display + '</div>' +
                (data.round_num ? '<div class="metric">轮次: 第' + data.round_num + '轮</div>' : '<div class="metric">轮次: -</div>');
            
            document.getElementById('reply').innerHTML = '<p><strong>生成话术:</strong></p><div class="result success">' + data.reply_text + '</div>';
            
            if (data.alternatives && data.alternatives.length > 0) {
                var alt_html = '<p><strong>备选话术:</strong></p>';
                for (var i = 0; i < Math.min(data.alternatives.length, 3); i++) {
                    alt_html += '<div class="result">[' + (i+1) + '] ' + data.alternatives[i] + '</div>';
                }
                document.getElementById('alternatives').innerHTML = alt_html;
            } else {
                document.getElementById('alternatives').innerHTML = '';
            }
            
            if (data.forbidden_hits && data.forbidden_hits.length > 0) {
                document.getElementById('forbidden').innerHTML = '<div class="result warning">⚠️ 检测到风险词: ' + data.forbidden_hits.join(', ') + '</div>';
            } else {
                document.getElementById('forbidden').innerHTML = '<div class="result" style="background:#d4edda;color:#155724">✅ 违禁词检测通过</div>';
            }
        }

        checkModelStatus();
    </script>
</body>
</html>
"""


@app.route('/api/model_status')
def api_model_status():
    global bot, is_model_loading, load_error
    
    if load_error:
        return jsonify({'status': 'error', 'error': load_error})
    if bot is not None:
        return jsonify({'status': 'ready'})
    if is_model_loading:
        return jsonify({'status': 'loading'})
    
    # 开始加载模型
    with load_lock:
        if not is_model_loading and bot is None:
            is_model_loading = True
            threading.Thread(target=load_model_async, daemon=True).start()
    
    return jsonify({'status': 'loading'})


@app.route('/api/intercept', methods=['POST'])
def api_intercept():
    global bot
    try:
        if bot is None:
            return jsonify({'error': '模型尚未加载完成，请稍候'}), 503
        
        data = request.json
        output_lang = data.get('lang', 'auto')
        bot.output_lang = output_lang

        response = bot.intercept(
            post_content=data.get('post', ''),
            comment_content=data.get('comment', ''),
        )

        forbidden_hits = [w for w, v in response.forbidden_check.items() if v]

        return jsonify({
            'tag': response.tag,
            'emotion': response.emotion,
            'backend': response.backend,
            'round_num': response.round_num,
            'reply_text': response.reply_text,
            'alternatives': response.alternatives,
            'forbidden_hits': forbidden_hits,
            'detected_language': response.detected_language,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    global bot
    try:
        if bot is None:
            return jsonify({'error': '模型尚未加载完成，请稍候'}), 503
        
        data = request.json
        output_lang = data.get('lang', 'auto')
        bot.output_lang = output_lang

        response = bot.reply_dm(
            chat_history=data.get('history', []),
        )

        forbidden_hits = [w for w, v in response.forbidden_check.items() if v]

        return jsonify({
            'tag': response.tag,
            'emotion': response.emotion,
            'backend': response.backend,
            'round_num': response.round_num,
            'reply_text': response.reply_text,
            'alternatives': response.alternatives,
            'forbidden_hits': forbidden_hits,
            'detected_language': response.detected_language,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
