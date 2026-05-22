#!/usr/bin/env python3
"""
截流话术机器人 — Flask 网页界面

运行方式：
    python3 intercept_flask.py

访问地址：http://localhost:5001
"""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)


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
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2rem; margin-bottom: 10px; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 10px;
            font-size: 1rem;
            cursor: pointer;
            width: 100%;
        }
        .btn:hover { opacity: 0.9; }
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
        .result { background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 15px; }
        .success { background: #d4edda; color: #155724; }
        .warning { background: #fff3cd; color: #856404; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px; }
        .metric { background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; }
        .tab {
            padding: 10px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            margin-right: 10px;
        }
        .tab.active { background: #667eea; color: white; border-color: #667eea; }
        #dm_mode { display: none; }
        .loading { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 截流话术机器人</h1>
            <p>基于 截流人设与话术.md + 截流助手Prompt.md</p>
        </div>

        <div class="card">
            <h3>⚙️ 配置</h3>
            <label>OpenAI API Key</label>
            <input type="password" id="api_key" placeholder="sk-xxx...">
            
            <label>输出语言</label>
            <select id="lang">
                <option value="en">英文</option>
                <option value="zh">中文</option>
            </select>

            <h3>📝 选择模式</h3>
            <div class="tabs">
                <span class="tab active" onclick="showIntercept()">主动截流</span>
                <span class="tab" onclick="showDM()">DM 回复</span>
            </div>

            <div id="intercept_mode">
                <label>帖子内容（可选）</label>
                <textarea id="post" placeholder="输入帖子内容..."></textarea>
                
                <label>评论内容</label>
                <textarea id="comment" placeholder="输入对方的评论..."></textarea>
            </div>

            <div id="dm_mode">
                <label>对话历史（每行一条）</label>
                <textarea id="history" placeholder="她: hey!&#10;我: hi!&#10;她: tell me more..."></textarea>
            </div>

            <button class="btn" onclick="generate()">
                <span id="btn_text">🚀 生成话术</span>
                <span id="btn_loading" class="loading">正在生成...</span>
            </button>
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
        function showIntercept() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('intercept_mode').style.display = 'block';
            document.getElementById('dm_mode').style.display = 'none';
        }
        function showDM() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('intercept_mode').style.display = 'none';
            document.getElementById('dm_mode').style.display = 'block';
        }
        async function generate() {
            var api_key = document.getElementById('api_key').value.trim();
            var lang = document.getElementById('lang').value;
            
            var is_intercept = document.querySelector('.tab.active').textContent === '主动截流';
            var post = is_intercept ? document.getElementById('post').value.trim() : '';
            var comment = is_intercept ? document.getElementById('comment').value.trim() : '';
            var history = !is_intercept ? document.getElementById('history').value.trim().split('\\n').filter(function(l){return l.trim()}) : [];

            if (!api_key) { alert('请输入 API Key'); return; }
            if (is_intercept && !comment) { alert('请输入评论内容'); return; }
            if (!is_intercept && history.length < 2) { alert('DM模式需要至少两条对话'); return; }

            document.getElementById('btn_text').style.display = 'none';
            document.getElementById('btn_loading').style.display = 'inline';

            try {
                var response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: api_key,
                        lang: lang,
                        mode: is_intercept ? 'intercept' : 'reply_dm',
                        post: post,
                        comment: comment,
                        history: history
                    })
                });
                var data = await response.json();
                
                document.getElementById('result_card').style.display = 'block';
                document.getElementById('metrics').innerHTML = 
                    '<div class=\"metric\">标签: ' + (data.tag || '待确认') + '</div>' +
                    '<div class=\"metric\">情绪: ' + (data.emotion || '待确认') + '</div>' +
                    '<div class=\"metric\">后端: ' + (data.backend || '待确认') + '</div>' +
                    (data.round_num ? '<div class=\"metric\">轮次: 第' + data.round_num + '轮</div>' : '<div class=\"metric\">轮次: -</div>');
                
                document.getElementById('reply').innerHTML = '<p><strong>生成话术:</strong></p><div class=\"result success\">' + data.reply_text + '</div>';
                
                if (data.alternatives && data.alternatives.length > 0) {
                    var alt_html = '<p><strong>备选话术:</strong></p>';
                    for (var i = 0; i < Math.min(data.alternatives.length, 3); i++) {
                        alt_html += '<div class=\"result\">[' + (i+1) + '] ' + data.alternatives[i] + '</div>';
                    }
                    document.getElementById('alternatives').innerHTML = alt_html;
                } else {
                    document.getElementById('alternatives').innerHTML = '';
                }
                
                if (data.forbidden_hits && data.forbidden_hits.length > 0) {
                    document.getElementById('forbidden').innerHTML = '<div class=\"result warning\">⚠️ 检测到风险词: ' + data.forbidden_hits.join(', ') + '</div>';
                } else {
                    document.getElementById('forbidden').innerHTML = '<div class=\"result\" style=\"background:#d4edda;color:#155724\">✅ 违禁词检测通过</div>';
                }
            } catch (e) {
                alert('生成失败: ' + e.message);
            } finally {
                document.getElementById('btn_text').style.display = 'inline';
                document.getElementById('btn_loading').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""


@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json
        
        from intercept_bot import InterceptBot
        bot = InterceptBot(
            provider=data.get('provider', 'openai'),
            api_key=data.get('api_key'),
            output_lang=data.get('lang', 'en'),
        )

        mode = data.get('mode', 'intercept')

        if mode == 'intercept':
            response = bot.intercept(
                post_content=data.get('post', ''),
                comment_content=data.get('comment', ''),
            )
        else:
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
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
