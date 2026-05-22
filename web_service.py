#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主动截流工具 - Web 界面
使用 Flask 提供网页服务
支持：截流模式 + DM 对话模式
"""

from flask import Flask, render_template_string, request, jsonify
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入我们的机器人
from intercept_bot_local import LocalInterceptBot

app = Flask(__name__)
bot = None
dm_history = []  # 保存 DM 对话历史

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram 主动截流工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        .tabs {
            display: flex;
            background: #f3f4f6;
            border-bottom: 1px solid #e5e7eb;
        }
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            font-weight: 600;
            color: #666;
            transition: all 0.3s;
            border: none;
            background: none;
            font-size: 16px;
        }
        .tab:hover {
            background: #e5e7eb;
        }
        .tab.active {
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }
        .tab-content {
            display: none;
            padding: 30px;
        }
        .tab-content.active {
            display: block;
        }
        .input-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        textarea, input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        textarea:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .result {
            margin-top: 30px;
            padding: 25px;
            background: #f9fafb;
            border-radius: 15px;
            border: 1px solid #e5e7eb;
        }
        .result h3 {
            margin-bottom: 20px;
            color: #667eea;
            font-size: 18px;
        }
        .tag {
            display: inline-block;
            padding: 4px 12px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        .reply-box {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .reply-box h4 {
            margin-bottom: 8px;
            color: #555;
            font-size: 14px;
        }
        .reply-box p {
            color: #333;
            line-height: 1.6;
        }
        .alternatives {
            margin-top: 20px;
        }
        .alternatives h4 {
            margin-bottom: 12px;
            color: #555;
        }
        .alt-item {
            padding: 12px;
            background: white;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid #e5e7eb;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        /* DM 对话样式 */
        .chat-container {
            border: 2px solid #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .chat-messages {
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
        }
        .message.user {
            align-items: flex-start;
        }
        .message.bot {
            align-items: flex-end;
        }
        .message-bubble {
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.5;
        }
        .message.user .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.bot .message-bubble {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            border: 1px solid #e5e7eb;
        }
        .message-label {
            font-size: 11px;
            color: #999;
            margin-bottom: 4px;
        }
        .chat-input {
            display: flex;
            border-top: 1px solid #e5e7eb;
            padding: 15px;
            background: white;
        }
        .chat-input textarea {
            flex: 1;
            margin-right: 10px;
            min-height: 50px;
            max-height: 150px;
        }
        .chat-input button {
            width: auto;
            padding: 12px 30px;
        }
        .chat-actions {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
        }
        .chat-actions button {
            flex: 1;
            padding: 10px;
            font-size: 14px;
        }
        .btn-secondary {
            background: #6b7280;
        }
        .btn-secondary:hover {
            background: #4b5563;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Instagram 主动截流工具</h1>
            <p>评论截流 + DM 对话，一站式搞定</p>
        </div>
        
        <!-- Tab 切换 -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('intercept')">💬 评论截流</button>
            <button class="tab" onclick="switchTab('dm')">💌 DM 对话</button>
        </div>
        
        <!-- 截流模式 -->
        <div id="intercept-tab" class="tab-content active">
            <form id="interceptForm">
                <div class="input-group">
                    <label>📝 帖子内容（可选）</label>
                    <textarea name="post_content" id="post_content" placeholder="输入帖子内容..."></textarea>
                </div>
                <div class="input-group">
                    <label>💬 评论内容（必填）</label>
                    <textarea name="comment_content" id="comment_content" placeholder="输入评论内容..."></textarea>
                </div>
                <button type="submit" id="submitBtn">✨ 生成截流话术</button>
            </form>
            
            <div class="loading" id="intercept-loading">
                <div class="spinner"></div>
                <p>正在生成中，请稍候...</p>
            </div>
            
            <div class="result" id="intercept-result" style="display: none;">
                <h3>🎯 生成结果</h3>
                <div>
                    <span class="tag" id="tag">标签</span>
                    <span class="tag" id="emotion">情绪</span>
                    <span class="tag" id="guidance">引导方向</span>
                </div>
                
                <div class="reply-box">
                    <h4>🇺🇸 英文话术</h4>
                    <p id="reply_text"></p>
                </div>
                
                <div class="reply-box">
                    <h4>🇨🇳 中文翻译</h4>
                    <p id="reply_zh"></p>
                </div>
                
                <div class="alternatives" id="alternatives">
                    <h4>🔄 备选话术</h4>
                </div>
            </div>
        </div>
        
        <!-- DM 模式 -->
        <div id="dm-tab" class="tab-content">
            <div class="chat-actions">
                <button type="button" class="btn-secondary" onclick="clearDmHistory()">🗑️ 清空对话</button>
            </div>
            
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages">
                    <!-- 消息会在这里显示 -->
                </div>
                
                <div class="chat-input">
                    <textarea id="dm-input" placeholder="输入用户的消息..."></textarea>
                    <button type="button" onclick="sendDmMessage()" id="dm-btn">💌 发送</button>
                </div>
            </div>
            
            <div class="loading" id="dm-loading">
                <div class="spinner"></div>
                <p>正在生成回复中，请稍候...</p>
            </div>
            
            <div class="result" id="dm-result" style="display: none;">
                <h3>💬 生成的 DM 回复</h3>
                <div class="reply-box">
                    <h4>🇺🇸 英文话术</h4>
                    <p id="dm-reply_text"></p>
                </div>
                <div class="reply-box">
                    <h4>🇨🇳 中文翻译</h4>
                    <p id="dm-reply_zh"></p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let dmHistory = []; // 每个元素是对象 { role: 'user' | 'bot', text: string }
        
        // 切换 Tab
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            if (tab === 'intercept') {
                document.querySelector('.tab:nth-child(1)').classList.add('active');
                document.getElementById('intercept-tab').classList.add('active');
            } else {
                document.querySelector('.tab:nth-child(2)').classList.add('active');
                document.getElementById('dm-tab').classList.add('active');
            }
        }
        
        // 截流模式提交
        document.getElementById('interceptForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const postContent = document.getElementById('post_content').value;
            const commentContent = document.getElementById('comment_content').value;
            
            if (!commentContent.trim()) {
                alert('请输入评论内容！');
                return;
            }
            
            document.getElementById('intercept-loading').style.display = 'block';
            document.getElementById('intercept-result').style.display = 'none';
            document.getElementById('submitBtn').disabled = true;
            
            try {
                const response = await fetch('/api/intercept', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ post_content: postContent, comment_content: commentContent })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('错误：' + data.error);
                    return;
                }
                
                document.getElementById('tag').textContent = '标签：' + data.tag;
                document.getElementById('emotion').textContent = '情绪：' + data.emotion;
                document.getElementById('guidance').textContent = data.guidance;
                document.getElementById('reply_text').textContent = data.reply_text;
                document.getElementById('reply_zh').textContent = data.reply_zh || '无需翻译';
                
                const alternativesDiv = document.getElementById('alternatives');
                alternativesDiv.innerHTML = '<h4>🔄 备选话术</h4>';
                (data.alternatives || []).forEach((alt, index) => {
                    alternativesDiv.innerHTML += `
                        <div class="alt-item">
                            <p style="margin-bottom: 5px;"><strong>${index + 1}.</strong> ${alt.text}</p>
                            ${alt.text_zh ? `<p style="color: #666; font-size: 13px;">${alt.text_zh}</p>` : ''}
                        </div>
                    `;
                });
                
                document.getElementById('intercept-result').style.display = 'block';
                
            } catch (error) {
                alert('请求失败：' + error.message);
            } finally {
                document.getElementById('intercept-loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
            }
        });
        
        // DM 发送消息
        async function sendDmMessage() {
            const input = document.getElementById('dm-input');
            const message = input.value.trim();
            
            if (!message) {
                alert('请输入消息！');
                return;
            }
            
            // 获取用户消息的翻译
            let userTextZh = '';
            try {
                const translateResponse = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: message })
                });
                const translateData = await translateResponse.json();
                userTextZh = translateData.translation || '';
            } catch (e) {
                console.log('Translation error:', e);
            }
            
            // 用户消息（带翻译）
            dmHistory.push({ role: 'user', text: message, text_zh: userTextZh });
            renderChatMessages();
            input.value = '';
            
            document.getElementById('dm-loading').style.display = 'block';
            document.getElementById('dm-result').style.display = 'none';
            document.getElementById('dm-btn').disabled = true;
            
            try {
                // 为了兼容后端，还是用字符串格式发送历史
                const historyStrings = dmHistory.map(m => (m.role === 'user' ? '她: ' : '我: ') + m.text);
                
                const response = await fetch('/api/dm', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ history: historyStrings })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('错误：' + data.error);
                    return;
                }
                
                // 我的回复（有英文和中文）
                dmHistory.push({ role: 'bot', text: data.reply_text, text_zh: data.reply_zh || '' });
                renderChatMessages();
                
                document.getElementById('dm-reply_text').textContent = data.reply_text;
                document.getElementById('dm-reply_zh').textContent = data.reply_zh || '无需翻译';
                document.getElementById('dm-result').style.display = 'block';
                
            } catch (error) {
                alert('请求失败：' + error.message);
            } finally {
                document.getElementById('dm-loading').style.display = 'none';
                document.getElementById('dm-btn').disabled = false;
            }
        }
        
        // 渲染聊天历史
        function renderChatMessages() {
            const container = document.getElementById('chat-messages');
            container.innerHTML = '';
            
            dmHistory.forEach(msg => {
                const isUser = msg.role === 'user';
                const div = document.createElement('div');
                div.className = 'message ' + (isUser ? 'user' : 'bot');
                div.innerHTML = `
                    <div class="message-label">${isUser ? '用户' : '我'}</div>
                    <div class="message-bubble">
                        <div style="margin-bottom: 5px;">${msg.text}</div>
                        ${msg.text_zh ? `<div style="color: #666; font-size: 13px; border-top: 1px dashed #ddd; padding-top: 5px; margin-top: 5px;">${msg.text_zh}</div>` : ''}
                    </div>
                `;
                container.appendChild(div);
            });
            
            container.scrollTop = container.scrollHeight;
        }
        
        // 清空对话历史
        function clearDmHistory() {
            if (confirm('确定要清空对话历史吗？')) {
                dmHistory = [];
                renderChatMessages();
                document.getElementById('dm-result').style.display = 'none';
            }
        }
        
        // 回车发送 DM
        document.getElementById('dm-input').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendDmMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/intercept', methods=['POST'])
def api_intercept():
    try:
        data = request.json
        post_content = data.get('post_content', '')
        comment_content = data.get('comment_content', '')
        
        global bot
        if bot is None:
            bot = LocalInterceptBot()
        
        result = bot.intercept(post_content=post_content, comment_content=comment_content)
        
        return jsonify({
            'tag': result.tag,
            'emotion': result.emotion,
            'guidance': result.guidance,
            'reply_text': result.reply_text,
            'reply_zh': result.reply_zh,
            'alternatives': result.alternatives,
            'detected_language': result.detected_language
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dm', methods=['POST'])
def api_dm():
    try:
        data = request.json
        history = data.get('history', [])
        
        global bot
        if bot is None:
            bot = LocalInterceptBot()
        
        result = bot.reply_dm(history)
        
        return jsonify({
            'tag': result.tag,
            'emotion': result.emotion,
            'guidance': result.guidance,
            'reply_text': result.reply_text,
            'reply_zh': result.reply_zh,
            'alternatives': result.alternatives,
            'detected_language': result.detected_language
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/translate', methods=['POST'])
def api_translate():
    try:
        data = request.json
        text = data.get('text', '')
        
        global bot
        if bot is None:
            bot = LocalInterceptBot()
        
        translation = bot._simple_translate(text)
        
        return jsonify({
            'translation': translation
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Instagram 主动截流工具 - Web 服务")
    print("=" * 60)
    print("\n正在启动服务...")
    print("\n📱 使用方法：")
    print("1. 在浏览器中打开：http://localhost:5005")
    print("2. 💬 评论截流：输入评论生成话术")
    print("3. 💌 DM 对话：模拟私信聊天")
    print("\n⏹️  停止服务：按 Ctrl + C")
    print("=" * 60)
    print("\n正在加载模型，请稍候...")
    app.run(host='0.0.0.0', port=5005, debug=False)
