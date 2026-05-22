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
        
        print("="*60)
        print(f"🚀 正在准备模型: {self.model_name}")
        print("="*60)
        print("📥 如果是第一次使用，模型将自动从 Hugging Face 下载")
        print("⏱️  模型大小约 1-3GB，下载需要几分钟，请耐心等待...")
        print("💡 下载完成后，后续使用会直接从本地加载，无需重新下载")
        print("-"*60)
        
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        print("✅ Tokenizer 加载完成")
        
        # 尝试使用4-bit量化加速
        try:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            print("⏳ 正在加载模型（使用4-bit量化加速）...")
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                device_map="auto",
                quantization_config=bnb_config,
                attn_implementation="flash_attention_2",
            )
            print("✅ 使用4-bit量化加载完成")
        except ImportError:
            # 如果没有bitsandbytes，尝试使用GPTQ量化或常规加载
            try:
                print("⏳ 正在加载模型（使用4-bit量化）...")
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    device_map="auto",
                    load_in_4bit=True,
                )
                print("✅ 使用4-bit量化加载完成")
            except Exception:
                print("⏳ 正在加载模型（标准模式）...")
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    device_map="auto",
                )
                print("✅ 模型加载完成（未使用量化）")

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
        """获取三条完全不同的备选话术（确保与推荐话术不同，并基于用户输入动态生成）"""
        alternatives = []
        used_texts = {reply_text} if reply_text else set()  # 记录已使用的话术
        
        # 生成三条完全不同的备选话术
        variant_prompts = [
            "Generate a friendly, supportive Instagram comment reply about healthy living. Use a warm, conversational tone like a sister chatting. End with a hook like 'Check my profile!' or 'DM me!'",
            "Create an encouraging Instagram reply for someone on a health journey. Keep it positive and relatable. Include a call to action to visit profile.",
            "Write a supportive sisterly message for someone struggling with health habits. Make it feel genuine and caring. Add a hook to check your profile."
        ]
        
        # 使用模型生成三条不同的备选话术
        for i, prompt in enumerate(variant_prompts):
            if self.mode != "template" and user_input:
                try:
                    system_prompt = """You are an Instagram health and wellness influencer.
                    Write a friendly, supportive reply in English. Keep it conversational like chatting with a sister.
                    End with a hook like 'Check my profile!' or 'DM me!'
                    
                    Do NOT use these forbidden words: lose weight fast, miracle, instant result, fat burner, appetite suppressant, detox, diet pill, slimming tea, before/after, weight loss product, burn fat, slim down, guarantee, results"""
                    
                    full_prompt = f"{system_prompt}\n\nUser message: {user_input}\n\nReply:"
                    response = self._generate_response(system_prompt, full_prompt)
                    
                    # 提取回复内容
                    lines = response.strip().split('\n')
                    alt_text = ""
                    for line in lines:
                        line = line.strip()
                        if line and not re.match(r'^(标签|Tag|Emotion|情绪|Dialogue|话术|中文|Chinese|#)', line, re.IGNORECASE):
                            # 去除引号
                            line = line.strip('\'"\"')
                            if len(line) > 20:
                                alt_text = line
                                break
                    
                    if alt_text and alt_text not in used_texts and not self._is_similar(alt_text, reply_text):
                        alt_zh = self._simple_translate(alt_text)
                        alternatives.append({'text': alt_text, 'text_zh': alt_zh})
                        used_texts.add(alt_text)
                except Exception as e:
                    print(f"Error generating alternative {i+1}: {e}")
        
        # 如果模型生成不够，使用备用话术库补充（确保不同）
        if len(alternatives) < 3:
            templates = BACKUP_TEMPLATES.get(tag, BACKUP_TEMPLATES.get('B', {}))
            emotion_templates = templates.get(emotion, templates.get('default', []))
            
            # 收集所有可用的模板
            all_templates = []
            if emotion_templates:
                all_templates.extend(emotion_templates)
            
            # 添加其他标签的模板
            for other_tag in BACKUP_TEMPLATES.keys():
                if other_tag != tag:
                    other_templates = BACKUP_TEMPLATES[other_tag].get(emotion, BACKUP_TEMPLATES[other_tag].get('default', []))
                    all_templates.extend(other_templates)
            
            # 随机打乱并选择不同的
            import random
            random.shuffle(all_templates)
            
            for t in all_templates:
                if len(alternatives) >= 3:
                    break
                if t[0] not in used_texts and not self._is_similar(t[0], reply_text):
                    alternatives.append({
                        'text': t[0],
                        'text_zh': t[1]
                    })
                    used_texts.add(t[0])
        
        # 如果仍然不够三条，使用改写版本
        while len(alternatives) < 3:
            # 找到一个基础文本进行改写
            base_text = ""
            if 'A' in BACKUP_TEMPLATES and BACKUP_TEMPLATES['A'].get('default'):
                base_text = BACKUP_TEMPLATES['A']['default'][0][0]
            elif 'B' in BACKUP_TEMPLATES and BACKUP_TEMPLATES['B'].get('default'):
                base_text = BACKUP_TEMPLATES['B']['default'][0][0]
            else:
                base_text = "Hey there! I totally get where you're coming from. Sometimes small changes make the biggest difference! Check my profile for more tips."
            
            # 生成不同的改写版本
            alt_en = self._paraphrase_text_v2(base_text, len(alternatives) + 1)
            alt_zh = self._simple_translate(alt_en)
            
            if alt_en not in used_texts:
                alternatives.append({
                    'text': alt_en,
                    'text_zh': alt_zh
                })
                used_texts.add(alt_en)
        
        return alternatives[:3]  # 确保最多三条
    
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
        """简单英文到中文翻译（用于备用）"""
        if not text:
            return "来看看我的主页获取更多健康小贴士！"
        
        # 单词级翻译字典
        word_translations = {
            'i': '我', 'you': '你', 'we': '我们', 'they': '他们', 'he': '他', 'she': '她', 'it': '它',
            'am': '是', 'is': '是', 'are': '是', 'was': '是', 'were': '是', 'be': '是',
            'can': '能', 'could': '能', 'will': '会', 'would': '会', 'should': '应该', 'may': '可能',
            'have': '有', 'has': '有', 'had': '有', 'do': '做', 'does': '做', 'did': '做',
            'and': '和', 'but': '但是', 'or': '或者', 'so': '所以', 'because': '因为', 'if': '如果',
            'the': '', 'a': '一个', 'an': '一个',
            'to': '到', 'for': '为了', 'in': '在', 'on': '在', 'at': '在', 'by': '通过', 'with': '和', 'from': '从',
            'not': '不', 'no': '不', 'yes': '是',
            'eat': '吃', 'ate': '吃了', 'eating': '正在吃', 'food': '食物', 'drink': '喝', 'water': '水', 'tea': '茶',
            'sweet': '甜食', 'cake': '蛋糕', 'chocolate': '巧克力', 'candy': '糖果', 'sugar': '糖',
            'weight': '体重', 'lose': '失去', 'lost': '失去了', 'losing': '正在失去', 'loss': '损失',
            'diet': '饮食', 'healthy': '健康的', 'health': '健康', 'exercise': '运动', 'gym': '健身房', 'workout': '锻炼',
            'stress': '压力', 'stressed': '有压力的', 'emotion': '情绪', 'emotional': '情绪化的', 'guilt': '内疚', 'guilty': '内疚的',
            'fail': '失败', 'failed': '失败了', 'trying': '尝试', 'tried': '尝试了', 'try': '尝试',
            'always': '总是', 'never': '从不', 'nothing': '没什么', 'works': '有效', 'work': '工作',
            'lazy': '懒惰的', 'easy': '容易的', 'simple': '简单的', 'hard': '困难的', 'difficult': '困难的',
            'good': '好的', 'great': '棒的', 'nice': '好的', 'bad': '差的', 'happy': '开心的', 'sad': '悲伤的',
            'feel': '感觉', 'feeling': '感觉', 'felt': '感觉了', 'body': '身体', 'gut': '肠胃', 'stomach': '胃', 'digestive': '消化的',
            'profile': '主页', 'page': '页面', 'blog': '博客', 'dm': '私信', 'message': '消息', 'check': '查看', 'come': '来',
            'see': '看', 'look': '看', 'my': '我的', 'your': '你的', 'me': '我', 'this': '这个', 'that': '那个',
            'want': '想要', 'need': '需要', 'help': '帮助', 'know': '知道', 'understand': '理解', 'get': '得到',
            'make': '做', 'take': '拿', 'give': '给', 'keep': '保持', 'start': '开始', 'stop': '停止', 'go': '去',
            'time': '时间', 'day': '天', 'daily': '每天', 'small': '小的', 'big': '大的', 'little': '小的',
            'change': '改变', 'changes': '改变', 'habit': '习惯', 'habits': '习惯', 'tip': '小贴士', 'tips': '小贴士',
            'try': '尝试', 'trying': '尝试', 'tried': '尝试了', 'totally': '完全', 'really': '真的', 'just': '只是',
            'like': '喜欢', 'love': '爱', 'hate': '讨厌', 'think': '想', 'thought': '想了',
            'should': '应该', 'must': '必须', 'might': '可能', 'could': '可以', 'would': '会',
            'when': '当', 'what': '什么', 'how': '怎么', 'why': '为什么', 'where': '哪里', 'who': '谁',
            'from': '从', 'into': '进入', 'out': '出去', 'up': '向上', 'down': '向下', 'over': '在上面', 'under': '在下面',
            'more': '更多', 'less': '更少', 'most': '最多', 'very': '非常', 'much': '很多', 'many': '很多',
            'still': '仍然', 'yet': '还', 'already': '已经', 'now': '现在', 'today': '今天',
            'girl': '姐妹', 'hey': '嘿', 'hi': '你好', 'hello': '你好', 'bye': '再见',
            'same': '同样的', 'different': '不同的', 'new': '新的', 'old': '旧的',
            'first': '第一', 'last': '最后', 'only': '只有', 'also': '也', 'too': '也', 'either': '也',
            'well': '好', 'better': '更好', 'best': '最好', 'enough': '足够', 'little': '少',
            'each': '每个', 'every': '每个', 'all': '所有', 'some': '一些', 'any': '任何',
            'other': '其他', 'another': '另一个', 'such': '这样', 'so': '如此', 'as': '作为',
            'than': '比', 'of': '的', 'off': '离开', 'about': '关于', 'above': '在上面', 'across': '穿过',
            'after': '之后', 'against': '反对', 'along': '沿着', 'among': '在...之中', 'around': '周围',
            'before': '之前', 'behind': '在后面', 'below': '在下面', 'between': '之间', 'beyond': '超越',
            'during': '期间', 'except': '除了', 'inside': '里面', 'outside': '外面', 'through': '通过',
            'toward': '朝向', 'under': '在下面', 'until': '直到', 'upon': '在...之上', 'within': '在...之内', 'without': '没有',
            'doing': '做', 'going': '去', 'having': '有', 'being': '是', 'seeing': '看', 'hearing': '听', 'feeling': '感觉',
            'been': '是', 'got': '得到', 'getting': '得到', 'made': '做了', 'making': '做', 'said': '说', 'saying': '说',
            'told': '告诉', 'telling': '告诉', 'asked': '问', 'asking': '问', 'answered': '回答', 'answering': '回答',
            'found': '发现', 'finding': '发现', 'known': '知道', 'knowing': '知道', 'thought': '想', 'thinking': '想',
            'given': '给了', 'giving': '给', 'taken': '拿了', 'taking': '拿', 'written': '写了', 'writing': '写',
            'broken': '打破', 'breaking': '打破', 'done': '做了', 'started': '开始', 'starting': '开始',
            'wanted': '想要', 'needing': '需要', 'helped': '帮助', 'helping': '帮助', 'loved': '爱', 'loving': '爱',
        }
        
        # 短语级翻译字典（优先）
        phrase_translations = {
            'Check my profile': '来看看我的主页',
            'DM me': '私信我',
            'Check out my page': '来看看我的主页',
            'Come check my page': '来看看我的主页',
            'Come check my profile': '来看看我的主页',
            'Check my page': '看看我的主页',
            'Hey girl': '嘿姐妹',
            'Hey there': '嘿',
            'Same here': '我也是',
            'I know the feeling': '我懂这种感觉',
            'I know what you mean': '我懂你的意思',
            'Let me help': '让我来帮你',
            'You got this': '你可以的',
            'You are not alone': '你不是一个人',
            'Follow me': '关注我',
            'Follow my journey': '关注我的旅程',
            'Healthy living': '健康生活',
            'Healthy habits': '健康习惯',
            'It takes time': '这需要时间',
            'Keep going': '继续加油',
            'Make a change': '做出改变',
            'Small changes': '小改变',
            'Daily practice': '日常练习',
            'Mindset shift': '心态转变',
            'Trust your body': '相信你的身体',
            'Listen to your body': '倾听你的身体',
            'Slow down': '慢下来',
            'Enjoy your food': '享受你的食物',
            'Eat mindfully': '用心吃饭',
            'Body positivity': '身体积极',
            'Self care': '自我关爱',
            'Self love': '自爱',
            'Be kind to yourself': '善待自己',
            'Give yourself grace': '给自己宽容',
            'You deserve it': '你值得',
            'No guilt': '没有罪恶感',
            'No shame': '没有羞耻',
            'Feel good': '感觉良好',
            'Stay motivated': '保持动力',
            'Stay positive': '保持积极',
            'Keep pushing': '继续努力',
            'You are amazing': '你很棒',
            'You are doing great': '你做得很好',
            'Take it easy': '放轻松',
            'One step at a time': '一步一步来',
            'Baby steps': '小步走',
            'Consistency is key': '坚持是关键',
            'Progress not perfection': '进步不是完美',
            'Celebrate small wins': '庆祝小胜利',
            'Keep it simple': '保持简单',
            'Make it easy': '让它简单',
            'No effort': '不费力',
            'Lazy girl': '懒人',
            'No complicated': '不复杂',
            'Simple trick': '简单方法',
            'Easy method': '简单方法',
            'Secret trick': '秘密方法',
            'Game changer': '改变游戏规则',
            'Life changing': '改变人生',
            'Changed everything': '改变了一切',
            'So much better': '好太多',
            'Way less': '少很多',
            'So much easier': '容易太多',
            'Totally normal': '完全正常',
            'It is normal': '这很正常',
            'Absolutely': '绝对',
            'Literally': '真的',
            'Honestly': '老实说',
            'Actually': '实际上',
            'Basically': '基本上',
            'Essentially': '本质上',
            'Specifically': '具体来说',
            'Particularly': '特别',
            'Especially': '尤其',
            'Definitely': '肯定',
            'Probably': '可能',
            'Maybe': '也许',
            'Perhaps': '也许',
            'Anyway': '不管怎样',
            'Anyways': '不管怎样',
            'Like I said': '就像我说的',
            'You know': '你知道',
            'I mean': '我的意思是',
            'Kind of': '有点',
            'Sort of': '有点',
            'A little': '一点',
            'A bit': '一点',
            'A lot': '很多',
            'Lots of': '很多',
            'Plenty of': '很多',
            'Not really': '不是真的',
            'Kind of': '有点',
            'Sort of': '有点',
            'Kind of like': '有点像',
            'Sort of like': '有点像',
            'More or less': '差不多',
            'Pretty much': '差不多',
            'For sure': '肯定',
            'For real': '真的',
            'No way': '不可能',
            'Of course': '当然',
            'Obviously': '显然',
            'Naturally': '自然',
            'Actually': '实际上',
            'In fact': '事实上',
            'As a matter of fact': '事实上',
            'To be honest': '老实说',
            'To tell you the truth': '说实话',
            'Frankly': '坦率地说',
            'Honestly speaking': '老实说',
            'Basically': '基本上',
            'Essentially': '本质上',
            'Fundamentally': '根本上',
            'Ultimately': '最终',
            'Eventually': '最终',
            'Finally': '最后',
            'At the end of the day': '说到底',
            'All in all': '总而言之',
            'Overall': '总体来说',
            'In general': '一般来说',
            'On the whole': '整体上',
            'By and large': '大体上',
            'For the most part': '大部分',
            'Mostly': '大部分',
            'Mainly': '主要',
            'Primarily': '主要',
            'Chiefly': '主要',
            'Especially': '尤其',
            'Particularly': '特别',
            'Specifically': '具体来说',
            'Namely': '即',
            'That is': '那就是',
            'Which is': '也就是',
            'What I mean is': '我的意思是',
            'What I am saying is': '我想说的是',
            'The thing is': '问题是',
            'The point is': '关键是',
            'My point is': '我的观点是',
            'The fact is': '事实是',
            'As a result': '因此',
            'As a consequence': '因此',
            'Consequently': '因此',
            'Therefore': '因此',
            'Thus': '因此',
            'Hence': '因此',
            'So': '所以',
            'That is why': '这就是为什么',
            'Which is why': '这就是为什么',
            'For this reason': '因为这个原因',
            'Because of this': '因为这个',
            'Due to this': '由于这个',
            'Thanks to this': '多亏这个',
            'In spite of this': '尽管如此',
            'Despite this': '尽管如此',
            'Nevertheless': '尽管如此',
            'Nonetheless': '尽管如此',
            'However': '然而',
            'But': '但是',
            'Yet': '但是',
            'Still': '仍然',
            'Even so': '即使如此',
            'On the other hand': '另一方面',
            'On the contrary': '相反',
            'In contrast': '相比之下',
            'Instead': '相反',
            'Rather': '而是',
            'Alternatively': '或者',
            'Otherwise': '否则',
            'If not': '如果不',
            'Unless': '除非',
            'Provided that': '如果',
            'As long as': '只要',
            'In case': '以防',
            'Just in case': '以防万一',
            'If only': '要是...就好了',
            'I wish': '我希望',
            'I hope': '我希望',
            'I think': '我认为',
            'I believe': '我相信',
            'I feel': '我感觉',
            'I guess': '我猜',
            'I suppose': '我想',
            'I assume': '我假设',
            'I reckon': '我认为',
            'In my opinion': '在我看来',
            'From my perspective': '从我的角度',
            'As far as I am concerned': '就我而言',
            'As I see it': '在我看来',
            'To my mind': '在我看来',
            'I would say': '我会说',
            'I would argue': '我认为',
            'I tend to think': '我倾向于认为',
            'It seems to me': '在我看来',
            'It appears that': '看起来',
            'It looks like': '看起来',
            'It seems like': '看起来',
            'Apparently': '显然',
            'Supposedly': '据说',
            ' Allegedly': '据称',
            'Reportedly': '据报道',
            'I heard that': '我听说',
            'I read that': '我读到',
            'They say': '他们说',
            'People say': '人们说',
            'It is said that': '据说',
            'It has been said that': '据说',
            'There is a saying that': '有句话说',
            'As the saying goes': '俗话说',
            'You know what they say': '你知道他们说',
            'I have heard it said that': '我听说',
            'From what I understand': '据我了解',
            'From what I gather': '据我所知',
            'As far as I know': '就我所知',
            'To the best of my knowledge': '据我所知',
            'For all I know': '据我所知',
            'So far as I know': '就我所知',
            'As I understand it': '据我理解',
            'From my understanding': '据我的理解',
            'I understand that': '我理解',
            'I realize that': '我意识到',
            'I notice that': '我注意到',
            'I see that': '我看到',
            'I find that': '我发现',
            'I think that': '我认为',
            'I feel that': '我感觉',
            'I believe that': '我相信',
            'I suspect that': '我怀疑',
            'I doubt that': '我怀疑',
            'I wonder if': '我想知道是否',
            'I wonder why': '我想知道为什么',
            'I wonder how': '我想知道怎么',
            'I am wondering': '我在想',
            'I was wondering': '我在想',
            'Could you please': '你能',
            'Would you mind': '你介意',
            'If you do not mind': '如果你不介意',
            'If it is not too much trouble': '如果不太麻烦',
            'I would appreciate it if': '如果...我会很感激',
            'I would be grateful if': '如果...我会很感激',
            'I would like to': '我想',
            'I would love to': '我很想',
            'I want to': '我想要',
            'I need to': '我需要',
            'I have to': '我必须',
            'I should': '我应该',
            'I ought to': '我应该',
            'I must': '我必须',
            'I can': '我能',
            'I could': '我可以',
            'I will': '我会',
            'I would': '我会',
            'I may': '我可能',
            'I might': '我可能',
            'I used to': '我以前',
            'I have been': '我一直',
            'I have been doing': '我一直在做',
            'I had been': '我曾经',
            'I was doing': '我当时正在做',
            'I am doing': '我正在做',
            'I am going to': '我打算',
            'I am about to': '我即将',
            'I am planning to': '我计划',
            'I intend to': '我打算',
            'I hope to': '我希望',
            'I expect to': '我期望',
            'I anticipate': '我预期',
            'I predict': '我预测',
            'I foresee': '我预见',
            'I imagine': '我想象',
            'I picture': '我想象',
            'I visualize': '我想象',
            'I dream of': '我梦想',
            'I aspire to': '我渴望',
            'I aim to': '我的目标是',
            'I strive to': '我努力',
            'I try to': '我尝试',
            'I attempt to': '我尝试',
            'I endeavor to': '我努力',
            'I work hard to': '我努力',
            'I am trying to': '我正在尝试',
            'I have been trying to': '我一直在尝试',
            'I keep trying to': '我一直在尝试',
            'I keep on trying to': '我一直在尝试',
            'I never give up': '我永不放弃',
            'I never quit': '我永不放弃',
            'I always try': '我总是尝试',
            'I always do my best': '我总是尽力',
            'I always give it my all': '我总是全力以赴',
            'I always put my heart into it': '我总是用心',
            'I always try my hardest': '我总是尽最大努力',
            'I always do everything I can': '我总是尽我所能',
            'I always go the extra mile': '我总是多走一步',
            'I always go above and beyond': '我总是超越',
            'I always go out of my way': '我总是想尽办法',
            'I always make an effort': '我总是努力',
            'I always try to improve': '我总是努力改进',
            'I always try to do better': '我总是努力做得更好',
            'I always try to be better': '我总是努力变得更好',
            'I always try to improve myself': '我总是努力提升自己',
            'I always try to better myself': '我总是努力提升自己',
            'I always try to be the best': '我总是努力做到最好',
            'I always try to give my best': '我总是努力做到最好',
            'I always try to do my best': '我总是尽力',
            'I always try to be perfect': '我总是努力做到完美',
            'I always try to achieve perfection': '我总是努力达到完美',
            'I always try to be flawless': '我总是努力做到完美',
            'I always try to be impeccable': '我总是努力做到完美',
            'I always try to be error-free': '我总是努力做到无错误',
            'I always try to be mistake-free': '我总是努力做到无错误',
            'I always try to be accurate': '我总是努力做到准确',
            'I always try to be precise': '我总是努力做到精确',
            'I always try to be thorough': '我总是努力做到彻底',
            'I always try to be comprehensive': '我总是努力做到全面',
            'I always try to be detailed': '我总是努力做到详细',
            'I always try to be meticulous': '我总是努力做到一丝不苟',
            'I always try to be careful': '我总是努力做到小心',
            'I always try to be cautious': '我总是努力做到谨慎',
            'I always try to be prudent': '我总是努力做到谨慎',
            'I always try to be thoughtful': '我总是努力做到周到',
            'I always try to be considerate': '我总是努力做到体贴',
            'I always try to be kind': '我总是努力做到善良',
            'I always try to be generous': '我总是努力做到慷慨',
            'I always try to be helpful': '我总是努力做到乐于助人',
            'I always try to be supportive': '我总是努力做到支持',
            'I always try to be encouraging': '我总是努力做到鼓励',
            'I always try to be positive': '我总是努力做到积极',
            'I always try to be optimistic': '我总是努力做到乐观',
            'I always try to be cheerful': '我总是努力做到开朗',
            'I always try to be friendly': '我总是努力做到友好',
            'I always try to be approachable': '我总是努力做到平易近人',
            'I always try to be welcoming': '我总是努力做到热情',
            'I always try to be warm': '我总是努力做到温暖',
            'I always try to be sincere': '我总是努力做到真诚',
            'I always try to be honest': '我总是努力做到诚实',
            'I always try to be trustworthy': '我总是努力做到值得信赖',
            'I always try to be reliable': '我总是努力做到可靠',
            'I always try to be dependable': '我总是努力做到可靠',
            'I always try to be consistent': '我总是努力做到一致',
            'I always try to be persistent': '我总是努力做到坚持',
            'I always try to be resilient': '我总是努力做到有韧性',
            'I always try to be determined': '我总是努力做到坚定',
            'I always try to be focused': '我总是努力做到专注',
            'I always try to be dedicated': '我总是努力做到专注',
            'I always try to be committed': '我总是努力做到投入',
            'I always try to be loyal': '我总是努力做到忠诚',
            'I always try to be faithful': '我总是努力做到忠诚',
            'I always try to be true': '我总是努力做到真实',
            'I always try to be authentic': '我总是努力做到真实',
            'I always try to be genuine': '我总是努力做到真诚',
            'I always try to be myself': '我总是努力做自己',
            'I always try to stay true to myself': '我总是努力保持真实',
            'I always try to be true to myself': '我总是努力忠于自己',
            'I always try to stay grounded': '我总是努力保持脚踏实地',
            'I always try to stay humble': '我总是努力保持谦虚',
            'I always try to stay grateful': '我总是努力保持感恩',
            'I always try to stay positive': '我总是努力保持积极',
            'I always try to stay motivated': '我总是努力保持动力',
            'I always try to stay inspired': '我总是努力保持灵感',
            'I always try to stay creative': '我总是努力保持创意',
            'I always try to stay curious': '我总是努力保持好奇',
            'I always try to stay open-minded': '我总是努力保持开放',
            'I always try to stay flexible': '我总是努力保持灵活',
            'I always try to stay adaptable': '我总是努力保持适应',
            'I always try to stay resilient': '我总是努力保持韧性',
            'I always try to stay strong': '我总是努力保持坚强',
            'I always try to stay brave': '我总是努力保持勇敢',
            'I always try to stay confident': '我总是努力保持自信',
            'I always try to stay self-assured': '我总是努力保持自信',
            'I always try to stay assertive': '我总是努力保持坚定',
            'I always try to stay independent': '我总是努力保持独立',
            'I always try to stay self-reliant': '我总是努力保持自立',
            'I always try to stay proactive': '我总是努力保持积极主动',
            'I always try to stay organized': '我总是努力保持有条理',
            'I always try to stay productive': '我总是努力保持高效',
            'I always try to stay efficient': '我总是努力保持高效',
            'I always try to stay focused': '我总是努力保持专注',
            'I always try to stay disciplined': '我总是努力保持自律',
            'I always try to stay consistent': '我总是努力保持一致',
            'I always try to stay persistent': '我总是努力保持坚持',
            'I always try to stay patient': '我总是努力保持耐心',
            'I always try to stay calm': '我总是努力保持冷静',
            'I always try to stay composed': '我总是努力保持镇定',
            'I always try to stay relaxed': '我总是努力保持放松',
            'I always try to stay peaceful': '我总是努力保持平静',
            'I always try to stay happy': '我总是努力保持快乐',
            'I always try to stay joyful': '我总是努力保持快乐',
            'I always try to stay content': '我总是努力保持满足',
            'I always try to stay grateful': '我总是努力保持感恩',
            'I always try to stay appreciative': '我总是努力保持感激',
            'I always try to stay thankful': '我总是努力保持感谢',
            'I always try to stay humble': '我总是努力保持谦虚',
            'I always try to stay modest': '我总是努力保持谦虚',
            'I always try to stay respectful': '我总是努力保持尊重',
            'I always try to stay polite': '我总是努力保持礼貌',
            'I always try to stay courteous': '我总是努力保持礼貌',
            'I always try to stay kind-hearted': '我总是努力保持善良',
            'I always try to stay compassionate': '我总是努力保持同情',
            'I always try to stay empathetic': '我总是努力保持同理心',
            'I always try to stay understanding': '我总是努力保持理解',
            'I always try to stay supportive': '我总是努力保持支持',
            'I always try to stay encouraging': '我总是努力保持鼓励',
            'I always try to stay uplifting': '我总是努力保持积极向上',
            'I always try to stay inspiring': '我总是努力保持鼓舞人心',
            'I always try to stay motivating': '我总是努力保持激励',
            'I always try to stay empowering': '我总是努力保持赋能',
            'I always try to stay empowering': '我总是努力保持赋能',
            'I always try to stay empowering': '我总是努力保持赋能',
        }
        
        # 先翻译短语
        result = text
        for en, zh in sorted(phrase_translations.items(), key=lambda x: -len(x[0])):
            result = result.replace(en, zh)
        
        # 然后翻译单词
        words = result.split()
        translated_words = []
        for word in words:
            # 去掉标点
            clean_word = re.sub(r'[.,!?;:()\[\]{}]', '', word.lower())
            if clean_word in word_translations:
                translated_words.append(word_translations[clean_word])
            else:
                translated_words.append(word)
        
        result = ' '.join(translated_words)
        
        # 清理多余空格和标点
        result = ' '.join(result.split())
        result = result.replace(' 。', '。').replace(' ，', '，').replace(' ！', '！').replace(' ？', '？')
        result = result.replace('。 ', '。').replace('， ', '，').replace('！ ', '！').replace('？ ', '？')
        
        return result

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
        """生成截流话术 - 模型+话术库结合"""
        user_input = comment_content if comment_content else post_content
        
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
            user_message = f"帖子内容: {post_content}\n评论内容: {comment_content}"
            system_prompt = self._build_system_prompt("intercept", detected_lang)
            raw_response = self._generate_response(system_prompt, user_message)
            response = self._parse_response(raw_response, "intercept", detected_lang)
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
