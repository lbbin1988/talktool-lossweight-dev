#!/usr/bin/env python3
"""
截流话术机器人 — 优化版（方案1+3）

方案1：使用Qwen2-1.5B-Chat模型（更强的理解能力）
方案3：添加备用话术库，确保输出质量
"""

import re
from pathlib import Path
from typing import Literal, List, Dict
from dataclasses import dataclass, field


SCRIPT_DIR = Path(__file__).parent.resolve()
PERSONA_FILE = SCRIPT_DIR / "截流人设与话术.md"
PROMPT_FILE = SCRIPT_DIR / "截流助手Prompt.md"
TAGS_FILE = SCRIPT_DIR / "目标账号与标签库.md"


# 备用话术库 - 根据标签和情绪预设（带钩子引导关注）
BACKUP_TEMPLATES = {
    'A': {  # 甜品上瘾
        '罪恶感循环': [
            ('Girl I used to feel SO guilty about sweets too! Then I just started letting myself enjoy them without shame... weirdly I eat way less now 😂 Check my profile for the simple trick that changed everything!', 
             '姐妹我以前对甜食也超级有罪恶感！后来我就干脆让自己毫无羞愧地享受...奇怪的是现在吃得反而少了😂 看我主页有个简单方法改变了一切！'),
            ('The candy was never the problem - it was the GUILT. Once I allowed myself to have it anytime, the craving went away. DM me if you want to hear more about how I did it!', 
             '糖果从来不是问题——是罪恶感才是。一旦我允许自己随时可以吃，渴望就消失了。私信我告诉你更多细节！'),
        ],
        'default': [
            ('Same here! I used to inhale desserts without even tasting them. Once I slowed down and actually enjoyed each bite, my body just... stopped wanting so much. Come check my page for more tips!', 
             '我也是！以前吃甜点都不尝味道直接咽。后来慢下来真正享受每一口，身体就...不那么想要了。来我主页看看更多技巧！'),
        ]
    },
    'B': {  # 情绪暴食
        '自我厌弃': [
            ('Omg I used to hate myself after binge eating too 😭 Turns out I was eating to avoid feeling something, not because I was hungry. DM me if you want to chat about how I broke the cycle!', 
             '天啊我以前暴食后也超恨自己😭后来发现我吃东西是为了逃避感受，不是因为饿。私信我聊聊我是怎么打破循环的！'),
            ('You are not broken - you are just trying to fill something that food can not fix. I get it. My profile has the mindset shift that helped me!', 
             '你没有问题——你只是在试图填补食物无法填补的东西。我懂。我主页有帮到我的心态转变方法！'),
        ],
        'default': [
            ('Stress eating hits different... I realized my body was not asking for snacks, it was asking me to slow down. Check my page for the simple daily practice that changed it all!', 
             '压力进食真的不一样...后来发现身体不是要零食，是要我慢下来。看我主页有个简单的日常练习改变了一切！'),
        ]
    },
    'C': {  # 懒人摆烂
        '耗竭感': [
            ('Literally the laziest person ever here 🙋♀️ All I do is say one sentence every morning + a simple daily drink. No effort at all! Come see my lazy girl method on my profile!', 
             '我真的是最懒的人了🙋♀️每天就早上说一句话+一杯简单的日常饮品。完全不费力！来我主页看看我的懒人方法！'),
            ('I refuse to do anything complicated! Just trust your body knows what to do - you do not need willpower. DM me for my 2-minute daily ritual!', 
             '我拒绝做任何复杂的事！相信身体知道该怎么做——不需要意志力。私信我要我每天2分钟的仪式！'),
        ],
        'default': [
            ('Same! Why make it hard? Just tell yourself "my body is getting lighter" every day and keep it simple. Check my page for more lazy tips!', 
             '同感！为什么要搞得那么难？每天告诉自己"我的身体正在变轻"，保持简单就好。来我主页看看更多懒人技巧！'),
        ]
    },
    'D': {  # 反复失败
        '自我否定': [
            ('I tried EVERYTHING and kept failing too 😩 Then I stopped fighting my body and started allowing it to change. Game changer! Check my profile for the approach that finally worked!', 
             '我也试过所有方法都失败了😩后来停止对抗身体，开始允许它改变。彻底改变了！看我主页有最终有效的方法！'),
            ('You are not the problem - those diets failed YOU. There is another way that does not require fighting. DM me to hear about the gentle method that worked for me!', 
             '你不是问题——那些节食方法让你失败了。还有另一条不需要对抗的路。私信我告诉你对我有效的温和方法！'),
        ],
        'default': [
            ('I get the "nothing works" feeling so hard. But what if you stopped trying so hard? That is when it clicked for me! Come see what I did on my profile!', 
             '我太懂"什么都没用"的感觉了。但如果你停止那么努力会怎么样？那就是我开窍的时候！来我主页看看我做了什么！'),
        ]
    },
}


@dataclass
class BotResponse:
    tag: str = ""
    emotion: str = ""
    guidance: str = ""  # 引导方向：引导关注主页/引导私信/自然聊天
    reply_text: str = ""
    reply_zh: str = ""
    alternatives: List[dict] = field(default_factory=list)
    forbidden_check: Dict[str, bool] = field(default_factory=dict)
    detected_language: str = ""
    reasoning: str = ""
    raw_response: str = ""


class LocalInterceptBot:
    DEFAULT_MODEL = "Qwen/Qwen2-1.5B-Chat"
    DEFAULT_MODE = "template"  # template: 仅用话术库 | local_model: 本地模型 | api: 在线API
    
    FORBIDDEN_WORDS = [
        "lose weight fast", "miracle", "instant result", "fat burner",
        "appetite suppressant", "detox", "diet pill", "slimming tea",
        "before/after", "weight loss product", "burn fat", "slim down",
        "guarantee", "results"
    ]

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        mode: str = DEFAULT_MODE,  # 新增：运行模式
        output_lang: Literal["en", "zh", "auto", "both"] = "auto",
        temperature: float = 0.7,
        max_tokens: int = 800,
    ):
        self.model_name = model_name
        self.mode = mode
        self.output_lang = output_lang
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model = None
        self._tokenizer = None
        self._load_files()
        if mode != "template":  # 只有非模板模式才加载模型
            self._load_model()

    def _load_files(self):
        """加载人设、话术和标签库文件"""
        self.persona_content = ""
        self.prompt_content = ""
        self.tags_content = ""
        
        if PERSONA_FILE.exists():
            with open(PERSONA_FILE, 'r', encoding='utf-8') as f:
                self.persona_content = f.read()
        
        if PROMPT_FILE.exists():
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                self.prompt_content = f.read()
        
        if TAGS_FILE.exists():
            with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                self.tags_content = f.read()

    def _load_model(self):
        """加载模型（仅在首次调用时）"""
        if self._model is not None:
            return
        
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        import os
        from pathlib import Path
        
        # 直接使用本地缓存路径
        home_dir = Path.home()
        local_model_path = home_dir / ".cache/huggingface/hub/models--Qwen--Qwen2-1.5B-Chat/snapshots/ba1cf1846d7df0a0591d6c00649f57e798519da8"
        
        print("="*60)
        print(f"🚀 正在准备模型: {self.model_name}")
        print("="*60)
        print(f"📥 从本地路径加载: {local_model_path}")
        print("-"*60)
        
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(local_model_path),
            trust_remote_code=True,
        )
        print("✅ Tokenizer 加载完成")
        
        # 直接使用标准模式加载（Mac上更稳定）
        print("⏳ 正在加载模型（标准模式）...")
        self._model = AutoModelForCausalLM.from_pretrained(
            str(local_model_path),
            trust_remote_code=True,
            device_map="auto",
        )
        print("✅ 模型加载完成")
        
        print("="*60)
        print("✅ 模型准备完成！")
        print("="*60)

    def _capitalize_first_letter(self, text: str) -> str:
        """修复句首大小写"""
        if not text:
            return text
        
        # 按句子分割
        sentences = re.split(r'(?<=[.!?])\s+', text)
        capitalized = []
        
        for sentence in sentences:
            if sentence:
                # 去掉开头的空格和标点
                stripped = sentence.lstrip(' \t\n\r.!?')
                if stripped:
                    # 找到第一个字母
                    for i, char in enumerate(stripped):
                        if char.isalpha():
                            # 大写第一个字母，保持其他部分不变
                            prefix = sentence[:len(sentence) - len(stripped) + i]
                            capitalized_sentence = prefix + char.upper() + stripped[i+1:]
                            capitalized.append(capitalized_sentence)
                            break
                    else:
                        capitalized.append(sentence)
                else:
                    capitalized.append(sentence)
            else:
                capitalized.append(sentence)
        
        return ' '.join(capitalized)

    def _build_system_prompt(self, mode: str, detected_lang: str = "zh") -> str:
        """构建系统提示词"""
        
        if mode == "chat":
            # DM对话模式 - 客户已经私信你，需要自然回复
            system_prompt = """你是Instagram减肥社区的贴心姐妹。

按照以下格式输出（必须严格遵守）：

标签: [A/B/C/D]
情绪: [客户情绪描述]
话术: [英文回复，2-3句，姐妹聊天语气，口语化，句首必须大写，结尾要加钩子引导关注如"Check my profile!"或"DM me!"]
中文: [上面英文话术的中文翻译]

标签含义：
A-甜品上瘾人群：爱吃甜食、甜品、糖果、巧克力
B-情绪暴食人群：压力大时吃东西、情绪性进食、暴食、健康问题
C-懒人摆烂人群：不想运动、喜欢简单方法、讨厌复杂
D-反复失败人群：尝试过很多方法都失败、自我否定

话术要求：
- 必须用英文回复
- 语气要像姐妹聊天，亲切自然
- 句首字母必须大写
- 结尾要有钩子引导关注主页或私信
- 不要用违禁词

违禁词：lose weight fast, miracle, instant result, fat burner, appetite suppressant, detox, diet pill, slimming tea, before/after, weight loss product, burn fat, slim down, guarantee, results
"""
        else:
            # 主动截流模式
            system_prompt = """你是Instagram减肥赛道截流助手。

按照以下格式输出（必须严格遵守）：

标签: [A/B/C/D]
情绪: [罪恶感循环/自我厌弃/耗竭感/自我否定]
话术: [英文回复，2-3句，姐妹聊天语气，口语化，句首必须大写，结尾要加钩子引导关注如"Check my profile!"或"DM me!"]
中文: [上面英文话术的中文翻译]

标签含义：
A-甜品上瘾人群：爱吃甜食、甜品、糖果、巧克力
B-情绪暴食人群：压力大时吃东西、情绪性进食、暴食
C-懒人摆烂人群：不想运动、喜欢简单方法、讨厌复杂
D-反复失败人群：尝试过很多方法都失败、自我否定

话术要求：
- 必须用英文回复
- 语气要像姐妹聊天，亲切自然
- 句首字母必须大写
- 结尾要有钩子引导关注主页或私信
- 不要用违禁词

违禁词：lose weight fast, miracle, instant result, fat burner, appetite suppressant, detox, diet pill, slimming tea, before/after, weight loss product, burn fat, slim down, guarantee, results
"""
        return system_prompt

    def _generate_response(self, system_prompt: str, user_message: str) -> str:
        self._load_model()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)
        outputs = self._model.generate(
            **inputs,
            temperature=self.temperature,
            max_new_tokens=self.max_tokens,
            do_sample=True,
            pad_token_id=self._tokenizer.eos_token_id,
            eos_token_id=self._tokenizer.eos_token_id,
            use_cache=True,
            num_return_sequences=1,
        )

        response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        pattern = r"assistant\n(.*)$"
        match = re.search(pattern, response, re.DOTALL)
        return match.group(1).strip() if match else response.strip()

    def _check_forbidden(self, text: str) -> Dict[str, bool]:
        text_lower = text.lower()
        return {word: word.lower() in text_lower for word in self.FORBIDDEN_WORDS}

    def _get_backup_response(self, tag: str, emotion: str) -> tuple:
        """从备用话术库获取回复"""
        templates = BACKUP_TEMPLATES.get(tag, BACKUP_TEMPLATES['A'])
        emotion_templates = templates.get(emotion, templates.get('default'))
        if emotion_templates:
            template = emotion_templates[0]
            # 根据话术内容判断引导方向
            en_text = template[0]
            if 'Check my profile' in en_text or 'Come check my page' in en_text:
                guidance = "引导关注主页"
            elif 'DM me' in en_text:
                guidance = "引导私信"
            else:
                guidance = "自然互动"
            return (en_text, template[1], guidance)
        return (BACKUP_TEMPLATES['A']['default'][0][0], BACKUP_TEMPLATES['A']['default'][0][1], "引导关注主页")

    def _get_backup_alternatives(self, tag: str, emotion: str, reply_text: str = "", user_input: str = "") -> List[dict]:
        """获取两条完全不同的备选话术（确保与推荐话术完全不同）"""
        alternatives = []
        used_texts = {reply_text} if reply_text else set()  # 记录已使用的话术
        
        # 预定义三个完全不同的回复模板库
        alternative_replies = [
            # 风格1：鼓励支持型
            {
                'en': "Hey girl! You're doing your best and that's all that matters! Progress isn't always linear, but every step counts. Keep going - you've got this! Check out my page for more support.",
                'zh': "嘿姑娘！你已经在尽力了，这就够了！进步不总是线性的，但每一步都很重要。继续加油——你可以的！来看看我的主页获取更多支持。"
            },
            # 风格2：实用建议型
            {
                'en': "Hi there! I totally relate to what you're saying. Something that really helped me was starting with tiny daily changes - like drinking more water or taking short walks. DM me if you want tips!",
                'zh': "嗨！我完全理解你说的。真正帮助我的是从微小的日常改变开始——比如多喝水或者短途散步。想要小贴士可以私信我！"
            },
            # 风格3：积极激励型
            {
                'en': "Hey! Don't be too hard on yourself! We all have off days, but the important thing is that you're trying. You're stronger than you think! Follow me for daily inspiration.",
                'zh': "嘿！别对自己太苛刻！我们都会有状态不好的时候，但重要的是你在尝试。你比你想象的更强大！关注我获取每日灵感。"
            }
        ]
        
        # 随机打乱顺序
        import random
        random.shuffle(alternative_replies)
        
        # 选择两条与回复完全不同的
        for alt in alternative_replies:
            if len(alternatives) >= 2:
                break
            if alt['en'] not in used_texts and not self._is_similar(alt['en'], reply_text):
                alternatives.append({
                    'text': alt['en'],
                    'text_zh': alt['zh']
                })
                used_texts.add(alt['en'])
        
        # 如果不足两条，补充更多
        backup_additions = [
            {
                'en': "Hey sister! I feel you! Changing habits takes time, but you're already on the right track just by caring. Keep it up! Check my profile for more.",
                'zh': "嘿姐妹！我懂你！改变习惯需要时间，但只要你在乎就已经在正确的轨道上了。继续加油！看我主页了解更多。"
            },
            {
                'en': "Hi! Don't worry, we all go through this! The secret is consistency over perfection. One day at a time - you're doing great! DM me anytime!",
                'zh': "嗨！别担心，我们都会经历这个！秘诀是坚持胜过完美。一天一天来——你做得很棒！随时私信我！"
            }
        ]
        
        for alt in backup_additions:
            if len(alternatives) >= 2:
                break
            if alt['en'] not in used_texts:
                alternatives.append({
                    'text': alt['en'],
                    'text_zh': alt['zh']
                })
                used_texts.add(alt['en'])
        
        return alternatives[:2]
    
    def _paraphrase_text_v2(self, text: str, variant: int = 1) -> str:
        """更有效的改写（支持多种变体）"""
        variant_changes = {
            1: [
                ('Hey', 'Hi'), ('there', 'girl'), ('totally', 'completely'),
                ('get', 'understand'), ('coming from', 'coming from'),
                ('small', 'tiny'), ('biggest', 'greatest'), ('Check', 'Come see'),
                ('profile', 'page'), ('tips', 'ideas')
            ],
            2: [
                ('Hey', 'Heyyy'), ('there', 'sister'), ('totally', 'honestly'),
                ('get', 'feel'), ('coming from', 'coming from'),
                ('small', 'little'), ('biggest', 'best'), ('Check', 'Check out'),
                ('profile', 'blog'), ('tips', 'hacks')
            ],
            3: [
                ('Hey', 'Oh hey'), ('there', 'friend'), ('totally', 'literally'),
                ('get', 'relate to'), ('coming from', 'coming from'),
                ('small', 'simple'), ('biggest', 'most amazing'), ('Check', 'Head over to'),
                ('profile', 'page'), ('tips', 'tricks')
            ]
        }
        
        changes = variant_changes.get(variant, variant_changes[1])
        result = text
        
        for old, new in changes:
            result = result.replace(old, new)
        
        # 添加不同的钩子
        hooks = [' DM me for more!', ' See my page for details!', ' Follow me for tips!']
        # 移除旧钩子并添加新钩子
        result = re.sub(r'\s*(Check my profile|DM me|Come see my page|Check out my page|Head over to my page)\s*[!]?\s*$', '', result)
        result = result.strip() + hooks[variant - 1]
        
        return result

    def _generate_dynamic_response(self, user_input: str, variant: int = 1) -> tuple:
        """根据用户输入动态生成回复"""
        input_lower = user_input.lower()
        
        # 分析用户输入的关键词
        has_gut = any(w in input_lower for w in ['gut', 'stomach', 'digestive', 'digestion'])
        has_food = any(w in input_lower for w in ['food', 'eat', 'diet', 'meal'])
        has_tips = any(w in input_lower for w in ['tips', 'guide', 'advice', 'help'])
        has_weight = any(w in input_lower for w in ['weight', 'lose', 'fat'])
        
        # 根据用户内容生成不同的回复
        responses = {
            1: {
                'en': "I totally get where you're coming from! For gut health, focus on adding more fiber-rich foods like leafy greens and probiotics to your diet. Consistency is key - small daily changes make a big difference! Check out my blog for more tips.",
                'zh': "我完全理解你的感受！对于肠道健康，建议多吃富含纤维的食物如绿叶蔬菜和益生菌。坚持是关键——每天一点小改变会带来大不同！来看看我的博客获取更多小贴士。"
            } if has_gut else {
                'en': "Great question! Building healthy habits takes time, but it's totally worth it. Start with one small change like drinking more water each day. You've got this! Follow my journey for more inspiration.",
                'zh': "好问题！养成健康习惯需要时间，但完全值得。从一个小改变开始，比如每天多喝水。你可以的！关注我的旅程获取更多灵感。"
            },
            2: {
                'en': "Hey there! When it comes to gut issues, I've found that incorporating fermented foods like yogurt and kefir really helped me. Plus, staying hydrated is so important! DM me if you want a personalized guide.",
                'zh': "嘿！关于肠道问题，我发现加入酸奶和开菲尔等发酵食品真的很有帮助。另外，保持水分非常重要！如果想要个性化指南可以私信我。"
            } if has_gut else {
                'en': "I totally relate! The key is to make sustainable changes that fit your lifestyle. Try swapping one unhealthy snack for something nourishing each week. You're doing amazing - keep going! 💪",
                'zh': "我完全理解！关键是做出适合你生活方式的可持续改变。尝试每周用健康的零食替代一个不健康的零食。你做得很棒——继续加油！💪"
            }
        }
        
        res = responses.get(variant, responses[1])
        return (res['en'], res['zh'])

    def _is_similar(self, text1: str, text2: str) -> bool:
        """判断两句话术是否相似（简单判断：前30个字符是否相同）"""
        if not text1 or not text2:
            return False
        return text1[:50].lower().strip() == text2[:50].lower().strip()

    def _paraphrase_text(self, text: str) -> str:
        """简单的改写（替换同义词）"""
        replacements = [
            ('Girl', 'Hey girl'),
            ('Same here', 'Honestly same'),
            ('I used to', 'I totally'),
            ('once I', 'when I'),
            ('actually', 'really'),
            ('body just', 'body literally'),
            ('stopped wanting', 'started wanting less'),
            ('Check my profile', 'Come see my page'),
            ('DM me', 'Message me'),
            ('lazy girl method', 'easy method'),
        ]
        result = text
        for old, new in replacements:
            result = result.replace(old, new)
        # 如果没有变化，添加一点结尾变化
        if result == text:
            if result.endswith('!'):
                result = result[:-1] + '! 💕'
            else:
                result = result + ' 🙌'
        return result

    def _parse_response(self, raw: str, mode: str, detected_lang: str) -> BotResponse:
        """解析模型输出"""
        resp = BotResponse(raw_response=raw)
        resp.detected_language = detected_lang

        # 提取标签（支持多种格式）
        tag_match = re.search(r'标签[：:]\s*([ABCD])|Tag:\s*\[A/B/C/D\]\s*-\s*(\w+)', raw)
        if tag_match:
            if tag_match.group(1):
                resp.tag = tag_match.group(1)
            elif tag_match.group(2):
                # 根据模型输出的描述推断标签
                desc = tag_match.group(2).lower()
                if any(w in desc for w in ['sweet', 'dessert', 'sugar']):
                    resp.tag = 'A'
                elif any(w in desc for w in ['gut', 'health', 'stress', 'binge', 'emotional']):
                    resp.tag = 'B'
                elif any(w in desc for w in ['lazy', 'easy']):
                    resp.tag = 'C'
                elif any(w in desc for w in ['fail', 'tried']):
                    resp.tag = 'D'
                else:
                    resp.tag = 'B'  # 默认B
        
        # 提取情绪（支持多种格式）
        emotion_match = re.search(r'情绪[：:]\s*([^\n]+)|Emotion:\s*\[([^\]]+)\]', raw)
        if emotion_match:
            resp.emotion = (emotion_match.group(1) or emotion_match.group(2) or '').strip()

        # 提取话术（支持多种格式）
        reply_match = re.search(r'话术[：:]\s*(.+?)(?=\n[^ ]|$)|Dialogue:\s*\n(.+?)(?=\n\n|$)', raw, re.DOTALL)
        if reply_match:
            reply_text = (reply_match.group(1) or reply_match.group(2) or '').strip().split('\n')[0]
            # 去除首尾的引号
            reply_text = reply_text.strip('\'"\"')
            resp.reply_text = self._capitalize_first_letter(reply_text)
        
        # 如果模型没有按格式输出话术，但有原始输出内容，直接使用原始内容作为话术
        if not resp.reply_text and raw:
            # 尝试从原始输出中提取有意义的句子作为话术
            lines = raw.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 跳过标签、情绪、话术等元数据行
                if len(line) > 20 and not re.match(r'^(标签|Tag|Emotion|情绪|Dialogue|话术|中文|Chinese|#)', line, re.IGNORECASE):
                    # 去除hashtag
                    clean_line = re.sub(r'#[^\s#]+', '', line).strip()
                    if clean_line and len(clean_line) > 20:
                        resp.reply_text = self._capitalize_first_letter(clean_line)
                        break

        # 提取中文翻译（只在模型按格式输出时才提取）
        zh_match = re.search(r'中文[：:]\s*(.+?)(?=\n[^ ]|$)', raw, re.DOTALL)
        if zh_match:
            zh_text = zh_match.group(1).strip().split('\n')[0]
            # 去除首尾的引号
            zh_text = zh_text.strip('\'"\"')
            resp.reply_zh = zh_text

        # 如果模型完全没有生成话术，使用备用话术库
        if not resp.reply_text:
            resp.tag = self._simple_tag_detection(raw) if not resp.tag else resp.tag
            en_text, zh_text, guidance = self._get_backup_response(resp.tag, resp.emotion)
            resp.reply_text = en_text
            resp.reply_zh = zh_text
            resp.guidance = guidance
        else:
            # 如果有话术但没有中文翻译，尝试生成翻译
            if not resp.reply_zh:
                # 使用简单翻译函数
                resp.reply_zh = self._simple_translate(resp.reply_text)
        
        # 去除reply_text和reply_zh中的hashtag
        if resp.reply_text:
            resp.reply_text = re.sub(r'#[^\s#]+', '', resp.reply_text).strip()
        if resp.reply_zh:
            resp.reply_zh = re.sub(r'#[^\s#]+', '', resp.reply_zh).strip()
        
        # 自动判断引导方向
        if not resp.guidance:
            if 'profile' in resp.reply_text.lower() or 'page' in resp.reply_text.lower():
                resp.guidance = "引导关注主页"
            elif 'dm' in resp.reply_text.lower() or 'message' in resp.reply_text.lower():
                resp.guidance = "引导私信"
            else:
                resp.guidance = "自然互动"

        resp.forbidden_check = self._check_forbidden(raw)
        resp.reasoning = raw[:500]

        return resp

    def _simple_translate(self, text: str) -> str:
        """使用Qwen模型翻译英文到中文"""
        if not text:
            return "来看看我的主页获取更多健康小贴士！"
        
        # 使用模型进行翻译
        system_prompt = """你是一个专业的英文到中文翻译助手。
请将下面的英文翻译成中文，只需要输出翻译结果，不需要其他解释。
保持原文的语气和风格。"""
        
        try:
            # 调用模型进行翻译
            response = self._generate_response(system_prompt, f"Translate to Chinese:\n{text}")
            
            # 清理结果：去除引号和多余空格
            result = response.strip().strip('\'"\"').strip()
            
            # 如果结果太短或者看起来不对，返回原文
            if len(result) < 2:
                return "来看看我的主页获取更多健康小贴士！"
            
            return result
        except Exception as e:
            print(f"Translation error: {e}")
            return "来看看我的主页获取更多健康小贴士！"

    def _simple_tag_detection(self, text: str) -> str:
        """简单规则识别标签 - 更严格"""
        text_lower = text.lower()
        
        # A类：明确与甜品相关
        a_keywords = ['sweet', 'dessert', 'candy', 'sugar', 'chocolate', 'ice cream']
        if any(w in text_lower for w in a_keywords):
            return 'A'
        
        # B类：明确与情绪、暴食、肠胃问题相关（去掉太泛的weight/body）
        b_keywords = ['stress', 'binge', 'emotional', 'guilt', 'guilty', 'feeling', 'gut', 'stomach', 'digestive']
        if any(w in text_lower for w in b_keywords):
            return 'B'
        
        # C类：明确与懒人相关
        c_keywords = ['lazy', 'no effort', 'don\'t want to', 'too tired']
        if any(w in text_lower for w in c_keywords):
            return 'C'
        
        # D类：明确与失败、反复相关
        d_keywords = ['fail', 'failed', 'nothing works', 'give up', 'always', 'never']
        if any(w in text_lower for w in d_keywords):
            return 'D'
        
        return 'unknown'  # 没有匹配到话术库的标签，用模型生成

    def _detect_language(self, text: str) -> str:
        """检测语言"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = sum(1 for c in text if c.isalpha())
        
        if chinese_chars > english_chars:
            return 'zh'
        return 'en'

    def intercept(self, post_content: str = "", comment_content: str = "") -> BotResponse:
        """生成截流话术 - 三条完全不同的话术"""
        user_input = comment_content if comment_content else post_content
        
        # 检测语言
        detected_lang = self._detect_language(user_input)
        
        # 确定标签
        tag = self._simple_tag_detection(user_input)
        
        # 定义三个完全不同的话术库（不同角度）
        all_replies = [
            # 角度1：理解共情型
            {
                'en': "Hey girl! I totally get where you're coming from - I've been there too! Changing habits isn't easy, but you're already taking the first step just by caring. Check out my page for what helped me!",
                'zh': "嘿姑娘！我完全理解你的感受——我也经历过！改变习惯不容易，但只要你在乎就已经迈出了第一步。来看看我的主页了解什么帮助了我！"
            },
            # 角度2：实用建议型
            {
                'en': "Hi there! Something that really made a difference for me was starting with super small changes - like drinking one extra glass of water a day. Small things add up! DM me for my simple tips!",
                'zh': "嗨！真正对我有帮助的是从超小的改变开始——比如每天多喝一杯水。小事积累起来！私信我获取我的简单小贴士！"
            },
            # 角度3：积极鼓励型
            {
                'en': "Hey! Don't be too hard on yourself! Progress isn't perfect, it's about consistency! You're doing better than you think. Follow me for daily motivation!",
                'zh': "嘿！别对自己太苛刻！进步不代表完美，而是关于坚持！你做得比你想象的更好。关注我获取每日动力！"
            },
            # 角度4：姐妹分享型
            {
                'en': "Hey sister! I feel you so much on this! For me, it was all about finding balance instead of restriction - that's what finally worked! Check my profile for my journey!",
                'zh': "嘿姐妹！我太懂你了！对我来说，关键是找到平衡而不是限制——这才是真正有效的！看我主页了解我的旅程！"
            },
            # 角度5：轻松幽默型
            {
                'en': "Hey! You know what? We've all been there! The good news is you don't have to figure it out alone - I've got you! Come see my page for easy ideas!",
                'zh': "嘿！你知道吗？我们都经历过！好消息是你不必独自解决——我来帮你！来看看我的主页获取简单想法！"
            }
        ]
        
        # 随机打乱，选出三条完全不同的
        import random
        random.shuffle(all_replies)
        
        # 第一条作为主回复
        main_reply = all_replies[0]
        en_text = main_reply['en']
        zh_text = main_reply['zh']
        
        # 第二条和第三条作为备选
        alternatives = []
        if len(all_replies) > 1:
            alternatives.append({
                'text': all_replies[1]['en'],
                'text_zh': all_replies[1]['zh']
            })
        if len(all_replies) > 2:
            alternatives.append({
                'text': all_replies[2]['en'],
                'text_zh': all_replies[2]['zh']
            })
        
        # 构建响应
        response = BotResponse()
        tag_names = {
            'A': 'A - 甜品上瘾',
            'B': 'B - 情绪暴食',
            'C': 'C - 懒人摆烂',
            'D': 'D - 反复失败',
            'unknown': '自定义话术'
        }
        response.tag = tag_names.get(tag, tag)
        response.emotion = "default"
        response.reply_text = en_text
        response.reply_zh = zh_text
        response.detected_language = detected_lang
        
        if 'profile' in en_text.lower() or 'page' in en_text.lower():
            response.guidance = "引导关注主页"
        elif 'dm' in en_text.lower() or 'message' in en_text.lower():
            response.guidance = "引导私信"
        else:
            response.guidance = "自然互动"
        
        if detected_lang == 'zh':
            response.reply_zh = ""
        
        response.alternatives = alternatives[:2]
        return response

    def chat(self, history: List[str]) -> BotResponse:
        """DM对话模式（别名）"""
        return self.reply_dm(history)

    def reply_dm(self, chat_history: List[str], extra_instruction: str = None) -> BotResponse:
        """DM对话模式 - 模型+话术库结合"""
        # 获取最后一条消息作为输入
        if chat_history:
            last_message = chat_history[-1]
            # 提取用户内容（去掉"她: "前缀）
            if last_message.startswith('她: '):
                user_input = last_message[3:]
            else:
                user_input = last_message
        else:
            user_input = ""
        
        # 检测语言
        detected_lang = self._detect_language(user_input)
        
        # 1. 先确定标签
        tag = self._simple_tag_detection(user_input)
        
        # 2. 检查是否用话术库：只有当tag是A/B/C/D时才用，否则用模型
        templates = BACKUP_TEMPLATES.get(tag, None)
        en_text = ""
        zh_text = ""
        use_template = False
        
        if tag != 'unknown' and templates and 'default' in templates and len(templates['default']) > 0:
            # 话术库有这个标签，优先用话术库（保证钩子和翻译对应）
            template = templates['default'][0]
            en_text = template[0]
            zh_text = template[1]
            use_template = True
        else:
            # 没有匹配到话术库，让模型生成
            user_message = "\n".join(chat_history)
            system_prompt = self._build_system_prompt("chat", detected_lang)
            raw_response = self._generate_response(system_prompt, user_message)
            response = self._parse_response(raw_response, "chat", detected_lang)
            en_text = response.reply_text
            zh_text = response.reply_zh or self._simple_translate(en_text)
            # 确保模型生成的有钩子
            if en_text and ('profile' not in en_text.lower() and 'dm' not in en_text.lower() and 'page' not in en_text.lower()):
                en_text = en_text + " Check my profile!"
                zh_text = zh_text + " 看我主页！"
        
        # 3. 构建响应
        response = BotResponse()
        tag_names = {
            'A': 'A - 甜品上瘾',
            'B': 'B - 情绪暴食',
            'C': 'C - 懒人摆烂',
            'D': 'D - 反复失败',
            'unknown': '自定义话术'
        }
        response.tag = tag_names.get(tag, tag)
        response.emotion = "default"
        response.reply_text = en_text
        response.reply_zh = zh_text
        response.detected_language = detected_lang
        
        if 'Check my profile' in en_text or 'Come check my page' in en_text:
            response.guidance = "引导关注主页"
        elif 'DM me' in en_text:
            response.guidance = "引导私信"
        else:
            response.guidance = "自然互动"
        
        if detected_lang == 'zh':
            response.reply_zh = ""
        
        # 4. 获取备选话术
        alternatives = []
        if use_template and templates:
            for emotion in ['罪恶感循环', '自我厌弃', '耗竭感', '自我否定', 'default']:
                if emotion in templates:
                    for template in templates[emotion]:
                        if template[0] != en_text and len(alternatives) < 2:
                            alternatives.append({'text': template[0], 'text_zh': template[1]})
            
            if len(alternatives) < 2 and 'default' in templates:
                for template in templates['default']:
                    if template[0] != en_text and len(alternatives) < 2 and template[0] not in [a['text'] for a in alternatives]:
                        alternatives.append({'text': template[0], 'text_zh': template[1]})
        
        if len(alternatives) < 2:
            alt1 = en_text.replace('profile', 'page') if 'profile' in en_text else en_text.replace('Check my', 'Come see my')
            alt1_zh = zh_text.replace('主页', '页面') if '主页' in zh_text else zh_text
            if alt1 != en_text:
                alternatives.append({'text': alt1, 'text_zh': alt1_zh})
            
            if len(alternatives) < 2:
                alt2 = en_text.replace('DM me', 'Message me') if 'DM me' in en_text else en_text + ' DM me!'
                alt2_zh = zh_text.replace('私信', '发消息') if '私信' in zh_text else zh_text + ' 私信我！'
                if alt2 != en_text and alt2 != alt1:
                    alternatives.append({'text': alt2, 'text_zh': alt2_zh})
        
        response.alternatives = alternatives[:2]
        return response


if __name__ == "__main__":
    bot = LocalInterceptBot(output_lang='auto')
    
    # 测试
    test_cases = [
        "I just cant stop eating sweets every night",
        "每次压力大就想吃东西，吃完又很后悔",
    ]
    
    for test in test_cases:
        print(f"\n输入: {test}")
        response = bot.intercept(comment_content=test)
        print(f"标签: {response.tag}")
        print(f"情绪: {response.emotion}")
        print(f"英文回复: {response.reply_text}")
        if response.reply_zh:
            print(f"中文翻译: {response.reply_zh}")
