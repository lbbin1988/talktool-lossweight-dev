#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主动截流工具 - Web 界面
使用 Flask 提供网页服务
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

# 简单的 HTML 模板
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
        .content {
            padding: 30px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Instagram 主动截流工具</h1>
            <p>输入帖子内容或评论，自动生成截流话术</p>
        </div>
        <div class="content">
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
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在生成中，请稍候...</p>
            </div>
            
            <div class="result" id="result" style="display: none;">
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
    </div>
    
    <script>
        document.getElementById('interceptForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const postContent = document.getElementById('post_content').value;
            const commentContent = document.getElementById('comment_content').value;
            
            if (!commentContent.trim()) {
                alert('请输入评论内容！');
                return;
            }
            
            // 显示加载状态
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            document.getElementById('submitBtn').disabled = true;
            
            try {
                const response = await fetch('/api/intercept', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        post_content: postContent,
                        comment_content: commentContent
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('错误：' + data.error);
                    return;
                }
                
                // 显示结果
                document.getElementById('tag').textContent = '标签：' + data.tag;
                document.getElementById('emotion').textContent = '情绪：' + data.emotion;
                document.getElementById('guidance').textContent = data.guidance;
                document.getElementById('reply_text').textContent = data.reply_text;
                document.getElementById('reply_zh').textContent = data.reply_zh || '无需翻译';
                
                // 显示备选话术
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
                
                document.getElementById('result').style.display = 'block';
                
            } catch (error) {
                alert('请求失败：' + error.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
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

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Instagram 主动截流工具 - Web 服务")
    print("=" * 60)
    print("\n正在启动服务...")
    print("\n📱 使用方法：")
    print("1. 在浏览器中打开：http://localhost:5005")
    print("2. 输入帖子内容和评论")
    print("3. 点击生成按钮获取截流话术")
    print("\n⏹️  停止服务：按 Ctrl + C")
    print("=" * 60)
    print("\n正在加载模型，请稍候...")
    app.run(host='0.0.0.0', port=5005, debug=False)