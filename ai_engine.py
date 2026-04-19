import json
import re
import difflib

class HealthAI:
    
    # 1. القاموس الطبي الموسع (Medical Ontology) - يربط الأعراض، المعاني، والكلمات العامية
    SYNONYMS_MAP = {
        "تعب": ["ارهاق", "اجهاد", "ضعف", "خمول", "كسل", "هزلان", "مجهد", "طاقة", "فشل"],
        "ارق": ["نوم", "سهر", "تفكير", "مواصيل", "تعبان", "مانام", "قلق"],
        "مناعة": ["زكام", "برد", "انفلونزا", "عطس", "رشح", "حلق", "كحة", "سعال", "بلغم", "مرض", "حرارة"],
        "توتر": ["ضغط", "نفسية", "اكتئاب", "حزن", "ضيق", "عصبية", "مزاج", "كورتيزول"],
        "دماغ": ["ذاكرة", "نسيان", "تركيز", "مذاكرة", "تشتت", "دوار", "دوخة", "صداع", "استيعاب"],
        "عظام": ["مفاصل", "ركبة", "هشاشة", "ظهر", "خشونة", "طقطقة", "الم", "روماتيزم", "عضلات", "شد"],
        "معدة": ["هضم", "قولون", "غازات", "انتفاخ", "حموضة", "امساك", "مغص", "اسهال", "حرقان", "غثيان"],
        "جمال": ["شعر", "تساقط", "صلع", "فراغات", "اظافر", "بشرة", "تجاعيد", "حبوب", "جفاف", "نضارة", "شحوب"],
        "رياضة": ["تمرين", "جيم", "حديد", "بناء", "استشفاء", "بروتين", "كارديو", "نشاط", "مكمل", "عضلات"],
        "قلب": ["كوليسترول", "شرايين", "دورة", "دم", "خفقان", "انيميا", "ضغط"],
    }

    # 2. كلمات الشدة (تضاعف تقييم المنتج إذا ظهرت في وصف المستخدم)
    INTENSITY_WORDS = {"شديد", "قوي", "مزمن", "جدا", "حيل", "كثير", "دائما", "مستمر", "تعبان", "موت", "حيلي"}
    
    # 3. كلمات التوقف (تُحذف لتسريع التحليل وتخفيف الضوضاء)
    STOP_WORDS = {"اشعر", "عندي", "اعاني", "من", "في", "علي", "هل", "اريد", "احس", "انا", "يا", "ما", "مش", "بسبب", "علاج", "دواء", "شي"}

    @staticmethod
    def normalize_text(text):
        """توحيد النص وتجهيزه للتحليل الدقيق"""
        if not text: return ""
        text = re.sub(r'[\u064B-\u065F]', '', text) # مسح التشكيل
        text = re.sub(r'[أإآ]', 'ا', text)
        text = re.sub(r'[ة]', 'ه', text)
        text = re.sub(r'[ى]', 'ي', text)
        return text.lower()

    @classmethod
    def extract_and_expand(cls, text):
        """استخراج الكلمات، تصحيح الأخطاء الإملائية، وتوسيع المفاهيم"""
        normalized_text = cls.normalize_text(text)
        words = list(re.findall(r'\b[^\W\d_]+\b', normalized_text, re.UNICODE))
        
        # استشعار هل الحالة "شديدة" بناءً على كلمات المستخدم
        has_intensity = any(w in cls.INTENSITY_WORDS for w in words)
        
        # تنظيف الكلمات غير المفيدة
        filtered_words = [w for w in words if w not in cls.STOP_WORDS and w not in cls.INTENSITY_WORDS]
        
        # تجهيز قائمة بكل الكلمات المعروفة لدينا لاستخدامها في تصحيح الأخطاء
        all_known_words = list(cls.SYNONYMS_MAP.keys())
        for syn_list in cls.SYNONYMS_MAP.values():
            all_known_words.extend(syn_list)
        
        expanded_keywords = set()
        
        for w in filtered_words:
            # الخوارزمية 1: تصحيح الأخطاء الإملائية (Fuzzy String Matching)
            # إذا أخطأ المستخدم بحرف، سيجد الذكاء أقرب كلمة طبية مطابقة بنسبة 70% فأكثر
            matches = difflib.get_close_matches(w, all_known_words, n=1, cutoff=0.70)
            target_word = matches[0] if matches else w
            
            expanded_keywords.add(target_word)
            
            # الخوارزمية 2: توسيع الإدراك عبر المرادفات (Semantic Expansion)
            for core, synonyms in cls.SYNONYMS_MAP.items():
                if target_word == core or target_word in synonyms:
                    expanded_keywords.add(core)
                    expanded_keywords.update(synonyms)
                    
        return expanded_keywords, has_intensity

    @classmethod
    def suggest_products(cls, user_input, products, limit=4):
        """محرك التوصية الرئيسي والمزود بأوزان التقييم (Weighted Scoring)"""
        user_keywords, has_intensity = cls.extract_and_expand(user_input)
        
        if not user_keywords:
            return []

        scored_products = []
        
        for p in products:
            product_dict = dict(p)
            try:
                tags = json.loads(product_dict['symptoms_tags'])
            except json.JSONDecodeError:
                tags = []
                
            normalized_tags = [cls.normalize_text(tag) for tag in tags]
            
            score = 0
            matched_tags = []
            
            # احتساب النقاط بناءً على جودة المطابقة
            for word in user_keywords:
                for i, tag in enumerate(normalized_tags):
                    if word == tag:
                        score += 3.0  # مطابقة دقيقة (نقطة عالية)
                        matched_tags.append(tags[i])
                    elif len(word) > 3 and (word in tag or tag in word):
                        score += 1.5  # مطابقة جزئية لكلمات طويلة (نقطة متوسطة)
                        matched_tags.append(tags[i])

            # تنظيف التكرارات
            matched_tags = list(set(matched_tags))
            
            if score > 0:
                # الخوارزمية 3: مضاعفة النقاط للحالات الشديدة (Intensity Multiplier)
                # إذا كانت حالة المستخدم "شديدة" والمنتج يعالج أكثر من عرض من أعراضه، نعطيه أولوية قصوى!
                if has_intensity and len(matched_tags) > 1:
                    score *= 1.8 
                    
                # حساب خوارزمية ذكية لنسبة المطابقة (Confidence Score)
                match_percentage = min(98, int((score / 12.0) * 100) + 45) # معادلة تعطي نسب بين 50% إلى 98%
                
                # صياغة الرد الذكي
                symptoms_str = " و ".join(matched_tags[:2])
                intensity_text = "بكفاءة عالية " if has_intensity else ""
                
                explanation = f"✨ نسبة توافق المنتج معك: {match_percentage}%\nالذكاء الاصطناعي يرشح لك هذا ليعالج ({symptoms_str}) {intensity_text}بناءً على الأعراض التي وصفتها."
                
                scored_products.append({
                    'product': product_dict,
                    'score': score,
                    'explanation': explanation,
                    'match_percentage': match_percentage
                })
        
        # ترتيب المنتجات من الأنسب إلى الأقل مناسبة
        scored_products.sort(key=lambda x: x['score'], reverse=True)
        return scored_products[:limit]