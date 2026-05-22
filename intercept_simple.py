#!/usr/bin/env python3
"""
截流话术机器人 — 简化版

运行方式：
    python3 intercept_simple.py

首次运行会下载 Qwen2-1.5B-Chat 模型（约 3GB）
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

print("🎯 截流话术机器人 - 启动中...")
print("正在加载模型，请耐心等待（首次运行会下载约 3GB 模型）...")

# 先同步加载模型
from intercept_bot_local import LocalInterceptBot
bot = LocalInterceptBot(output_lang='auto')
print("✅ 模型加载完成！")

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

from flask_cors import CORS
CORS(app)


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
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
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
            padding: 14px 32px;
            border-radius: 10px;
            font-size: 1rem;
            cursor: pointer;
            width: 100%;
            transition: opacity 0.3s;
        }
        .btn:hover:not(:disabled) { opacity: 0.9; }
        .btn:disabled { 
            background: #ccc; 
            cursor: not-allowed;
        }
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
            margin-bottom: 15px;
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
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
        }
        .chat-input {
            display: flex;
            gap: 10px;
        }
        .chat-input textarea {
            flex: 1;
            min-height: 80px;
            margin-bottom: 0;
            font-size: 1rem;
        }
        .chat-input .btn {
            width: auto;
            padding: 12px 20px;
            min-width: 80px;
        }
        .result { background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 15px; }
        .success { background: #d4edda; color: #155724; }
        .warning { background: #fff3cd; color: #856404; }
        .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px; }
        .metric { background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; }
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
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .model-status {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.875rem;
            background: #d4edda;
            color: #155724;
            margin-bottom: 15px;
        }
        .analysis-section {
            background: #e8f4f8;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .reply-section {
            background: #f0f0f0;
            padding: 12px;
            margin: 10px 0;
            border-radius: 8px;
        }
        .reply-en {
            font-size: 1.1rem;
            color: #333;
            margin-bottom: 8px;
        }
        .reply-zh {
            color: #666;
            font-style: italic;
        }
        .raw-output {
            background: #f8f9fa;
            padding: 16px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.875rem;
            max-height: 300px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 截流话术机器人</h1>
            <p>本地开源模型 · 无需 API Key</p>
        </div>

        <div class="card">
            <div class="model-status">✅ 模型已就绪</div>

            <span class="tab active" onclick="switchMode('intercept')">🎯 主动截流</span>
            <span class="tab" onclick="switchMode('chat')">💬 DM 对话</span>

            <!-- 主动截流 -->
            <div id="intercept_panel" class="mode-panel active">
                <label>帖子内容（可选）</label>
                <div style="position:relative;">
                    <textarea id="post" placeholder="输入帖子内容..." style="min-height:80px;"></textarea>
                    <button onclick="document.getElementById('post').value=''" style="position:absolute;right:10px;top:10px;background:#ddd;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px;">清除</button>
                </div>
                
                <label>评论内容</label>
                <div style="position:relative;">
                    <textarea id="comment" placeholder="输入对方的评论..." style="min-height:80px;"></textarea>
                    <button onclick="document.getElementById('comment').value=''" style="position:absolute;right:10px;top:10px;background:#ddd;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px;">清除</button>
                </div>

                <button class="btn" onclick="generateIntercept()">
                    <span class="loading-spinner" id="spin1" style="display:none"></span>
                    🚀 生成话术
                </button>
            </div>

            <!-- DM 对话 -->
            <div id="chat_panel" class="mode-panel">
                <div style="background:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:15px;font-size:0.9rem;color:#666;">
                    <strong>💡 DM对话模式</strong>：输入客户发来的消息，AI会生成你应该回复的内容。不同于主动截流，DM是你和客户的私聊对话。
                </div>
                <div class="chat-messages" id="chat_messages">
                </div>
                <div class="chat-input">
                    <div style="position:relative;">
                        <textarea id="chat_input" placeholder="输入客户发来的消息..." style="min-height:80px;"></textarea>
                        <button onclick="document.getElementById('chat_input').value=''" style="position:absolute;right:10px;top:10px;background:#ddd;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px;">清除</button>
                    </div>
                    <button class="btn" onclick="sendChat()" style="margin-top:10px;">发送</button>
                </div>
                <button class="btn btn-sm" onclick="clearChat()" style="width:auto;margin-top:10px;background:#666;">清空对话</button>
            </div>
        </div>

        <div id="result_card" class="card" style="display: none;">
            <h3>💬 生成结果</h3>
            <div class="metrics" id="metrics"></div>
            
            <div id="analysis_section"></div>
            <div id="reply_section"></div>
            
            <div id="alternatives_section"></div>
            <div id="forbidden_section"></div>
        </div>
    </div>

    <script>
        var chat_history = ["她: 嗨！你是怎么瘦下来的？", "我: 哈哈，其实我也爱吃甜！后来改变了和食物的关系～"];

        function switchMode(mode) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('intercept_panel').classList.remove('active');
            document.getElementById('chat_panel').classList.remove('active');
            document.getElementById(mode + '_panel').classList.add('active');
        }

        async function generateIntercept() {
            var post = document.getElementById('post').value.trim();
            var comment = document.getElementById('comment').value.trim();

            if (!comment) { alert('请输入评论内容'); return; }

            document.getElementById('spin1').style.display = 'inline-block';
            document.getElementById('result_card').style.display = 'none';

            try {
                var response = await fetch('/api/intercept', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ post: post, comment: comment })
                });
                var data = await response.json();
                showResult(data);
            } catch (e) {
                alert('生成失败: ' + e.message);
            } finally {
                document.getElementById('spin1').style.display = 'none';
            }
        }

        async function sendChat() {
            var input = document.getElementById('chat_input').value.trim();
            if (!input) return;

            chat_history.push('她: ' + input);
            document.getElementById('chat_messages').innerHTML += 
                '<div class="chat-message her">她: ' + input + '</div>';
            document.getElementById('chat_input').value = '';

            try {
                var response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ history: chat_history })
                });
                var data = await response.json();
                
                // 构建回复显示（双语）
                var reply_display = data.reply_text;
                if (data.detected_language === 'en' && data.reply_zh) {
                    reply_display = data.reply_text + '\\n' + data.reply_zh;
                }
                
                chat_history.push('我: ' + reply_display);
                document.getElementById('chat_messages').innerHTML += 
                    '<div class="chat-message me" style="white-space: pre-wrap;">我: ' + reply_display + '</div>';
                showResult(data);
            } catch (e) {
                alert('生成失败: ' + e.message);
            }
        }

        function clearChat() {
            chat_history = [];
            document.getElementById('chat_messages').innerHTML = '';
            document.getElementById('result_card').style.display = 'none';
        }

        function showResult(data) {
            document.getElementById('result_card').style.display = 'block';
            
            // 显示分析结果
            var guidance_display = data.guidance || '自然互动';
            var guidance_icon = guidance_display === '引导关注主页' ? '👀' : (guidance_display === '引导私信' ? '💬' : '✨');
            var tagMeaning = {'A': '甜品上瘾', 'B': '情绪暴食', 'C': '懒人摆烂', 'D': '反复失败'};
            document.getElementById('metrics').innerHTML = 
                '<div class="metric">标签: ' + (data.tag || '-') + '（' + (tagMeaning[data.tag] || '未知') + '）</div>' +
                '<div class="metric">情绪: ' + (data.emotion || '-') + '</div>' +
                '<div class="metric">' + guidance_icon + ' ' + guidance_display + '</div>';
            
            // 显示分析
            document.getElementById('analysis_section').innerHTML = 
                '<div class="analysis-section"><strong>📊 客户分析</strong><br>' +
                '标签: <strong>' + (data.tag || '待确认') + '（' + (tagMeaning[data.tag] || '未知') + '）</strong><br>' +
                '情绪: ' + (data.emotion || '待确认') + '<br>' +
                '引导方向: <span style="color:#667eea;font-weight:bold;">' + guidance_icon + ' ' + guidance_display + '</span></div>';
            
            // 显示话术 - 分开显示英文和中文
            var reply_html = '<div class="reply-section"><strong>💬 推荐话术</strong><br><br>';
            if (data.reply_text) {
                if (data.detected_language === 'en') {
                    reply_html += '<div style="margin-bottom:8px;"><span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:4px;font-size:12px;">🇺🇸 英文</span></div>';
                    reply_html += '<div style="background:#f8f9fa;padding:12px;border-radius:8px;margin-bottom:10px;">' + data.reply_text + '</div>';
                    if (data.reply_zh) {
                        reply_html += '<div style="margin-bottom:8px;"><span style="background:#fff3e0;color:#e65100;padding:2px 8px;border-radius:4px;font-size:12px;">🇨🇳 中文</span></div>';
                        reply_html += '<div style="background:#fff8e1;padding:12px;border-radius:8px;">' + data.reply_zh + '</div>';
                    }
                } else {
                    reply_html += '<div style="margin-bottom:8px;"><span style="background:#e3f2fd;color:#1565c0;padding:2px 8px;border-radius:4px;font-size:12px;">🇨🇳 中文</span></div>';
                    reply_html += '<div style="background:#e3f2fd;padding:12px;border-radius:8px;">' + data.reply_text + '</div>';
                }
            }
            reply_html += '</div>';
            document.getElementById('reply_section').innerHTML = reply_html;
            
            // 显示备选话术（两条，都要显示双语）
            var alt1 = data.alternatives && data.alternatives[0] ? data.alternatives[0] : null;
            var alt2 = data.alternatives && data.alternatives[1] ? data.alternatives[1] : null;
            if (alt1 || alt2) {
                var alt_html = '<div style="margin-top:15px;"><strong>📝 备选话术</strong>';
                if (alt1) {
                    alt_html += '<div style="margin-top:10px;padding:12px;background:#f8f9fa;border-radius:8px;">';
                    alt_html += '<div style="font-weight:bold;color:#667eea;margin-bottom:8px;">[备选1]</div>';
                    if (alt1.text) {
                        alt_html += '<div style="margin-bottom:8px;">' + alt1.text + '</div>';
                    }
                    if (alt1.text_zh) {
                        alt_html += '<div style="color:#666;font-size:0.9rem;">' + alt1.text_zh + '</div>';
                    }
                    alt_html += '</div>';
                }
                if (alt2) {
                    alt_html += '<div style="margin-top:10px;padding:12px;background:#f8f9fa;border-radius:8px;">';
                    alt_html += '<div style="font-weight:bold;color:#667eea;margin-bottom:8px;">[备选2]</div>';
                    if (alt2.text) {
                        alt_html += '<div style="margin-bottom:8px;">' + alt2.text + '</div>';
                    }
                    if (alt2.text_zh) {
                        alt_html += '<div style="color:#666;font-size:0.9rem;">' + alt2.text_zh + '</div>';
                    }
                    alt_html += '</div>';
                }
                alt_html += '</div>';
                document.getElementById('alternatives_section').innerHTML = alt_html;
            } else {
                document.getElementById('alternatives_section').innerHTML = '';
            }
            
            // 显示违禁词检测
            if (data.forbidden_hits && data.forbidden_hits.length > 0) {
                document.getElementById('forbidden_section').innerHTML = 
                    '<div class="result warning">⚠️ 风险词: ' + data.forbidden_hits.join(', ') + '</div>';
            } else {
                document.getElementById('forbidden_section').innerHTML = 
                    '<div class="result" style="background:#d4edda;color:#155724">✅ 检测通过</div>';
            }
        }
    </script>
</body>
</html>
"""


@app.route('/api/intercept', methods=['POST'])
def api_intercept():
    try:
        data = request.json
        
        response = bot.intercept(
            post_content=data.get('post', ''),
            comment_content=data.get('comment', ''),
        )

        forbidden_hits = [w for w, v in response.forbidden_check.items() if v]

        return jsonify({
            'tag': response.tag,
            'emotion': response.emotion,
            'guidance': response.guidance,
            'reply_text': response.reply_text,
            'reply_zh': response.reply_zh,
            'alternatives': response.alternatives,
            'forbidden_hits': forbidden_hits,
            'detected_language': response.detected_language,
            'raw_response': response.raw_response,
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.json
        
        response = bot.reply_dm(chat_history=data.get('history', []))

        forbidden_hits = [w for w, v in response.forbidden_check.items() if v]

        return jsonify({
            'tag': response.tag,
            'emotion': response.emotion,
            'guidance': response.guidance,
            'reply_text': response.reply_text,
            'reply_zh': response.reply_zh,
            'alternatives': response.alternatives,
            'forbidden_hits': forbidden_hits,
            'detected_language': response.detected_language,
            'raw_response': response.raw_response,
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


if __name__ == '__main__':
    print("🌐 服务启动于 http://127.0.0.1:5003")
    app.run(host='0.0.0.0', port=5003, debug=False)
