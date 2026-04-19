import re
import difflib
import json
import urllib.request
import urllib.error

class HealthAI:
    # --- 1. خريطة المفاهيم (للمحرك المحلي / Offline) ---
    SYNONYMS_MAP = {
        "صداع": ["الم راس", "شقيقة", "وجع راس", "دوار", "دوخة", "نصفيات", "راسي", "الم بالراس"],
        "ارهاق": ["تعب", "خمول", "ضعف", "كسل", "طاقة", "مجهد", "فشل", "تعبان", "دايخ", "اعياء"],
        "مفاصل": ["ركبة", "عظام", "روماتيزم", "ظهر", "عضلات", "طقطقة", "خشونة", "الام", "مفصل", "غضروف"],
        "ارق": ["نوم", "سهر", "قلق", "صعوبة", "تفكير", "منبهات", "نعاس", "ما انام", "ارق"],
        "زكام": ["برد", "انفلونزا", "سعال", "كحة", "رشح", "عطس", "احتقان", "نشلة", "بلغم", "حمى", "حرارة"],
        "مناعة": ["فيتامين", "وقاية", "مكمل", "تغذية", "صحة", "حديد", "زنك", "مرض", "فيتامينات"],
        "معدة": ["هضم", "قولون", "غازات", "حموضة", "مغص", "اسهال", "امساك", "بطن", "غثيان", "قرحة"],
        "عناية": ["بشرة", "شعر", "تساقط", "حب شباب", "جفاف", "نضارة", "تجميل", "كريم", "مرطب"]
    }

    STOP_WORDS = {"من", "في", "على", "عن", "الى", "انا", "عندي", "اعاني", "احس", "اشعر", "لي", "يا", "هل", "كيف", "اريد", "علاج", "دواء", "مشكلة", "جدا", "كثيرا", "شديد", "اليوم"}

    # ==========================================
    # محرك الذكاء السحابي (Gemini API - Online)
    # ==========================================
    @staticmethod
    def suggest_products_gemini(user_input, all_products, api_key):
        """الاستعانة بـ Gemini عبر الإنترنت لوصف ذكي جداً"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            # تجهيز المنتجات ليفهمها الذكاء الاصطناعي
            products_text = "\n".join([f'- رقم المنتج: {p["id"]} | الاسم: {p["name"]} | الوصف: {p["description"]} | الكلمات المفتاحية: {p.get("tags", "")}' for p in all_products if p.get('quantity', 1) > 0])
            
            # هندسة الأوامر (Prompt Engineering) لإجبار الذكاء على الرد كـ JSON
            prompt = f"""
            أنت طبيب وصيدلاني خبير في متجر منتجات صحية.
            حالة المريض: "{user_input}"
            المنتجات المتوفرة:
            {products_text}
            
            بناءً على حالة المريض بدقة، اختر أفضل المنتجات المتوفرة (كحد أقصى 3 منتجات).
            يجب أن يكون الرد عبارة عن مصفوفة JSON فقط، وكل عنصر يحتوي على:
            "id": رقم المنتج،
            "explanation": "شرح طبي مقنع ومختصر يبرر للمريض سبب اختيار هذا المنتج لحالته."
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
            
            with urllib.request.urlopen(req, timeout=15) as response:
                result_data = json.loads(response.read().decode('utf-8'))
                text_response = result_data['candidates'][0]['content']['parts'][0]['text']
                
                suggestions = json.loads(text_response)
                final_results = []
                for sug in suggestions:
                    prod_id = sug.get('id')
                    prod = next((p for p in all_products if str(p['id']) == str(prod_id)), None)
                    if prod:
                        final_results.append({
                            "product": prod,
                            "explanation": "✨ (Gemini): " + sug.get('explanation', '')
                        })
                return final_results
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None # في حالة فشل الإنترنت أو المفتاح، سيعيد None ليتم تفعيل المحرك المحلي

    # ==========================================
    # محرك الذكاء المحلي (Offline Fallback)
    # ==========================================
    @staticmethod
    def normalize_text(text):
        if not text: return ""
        text = re.sub(r'[\u0617-\u061A\u064B-\u0652]', '', text)
        text = re.sub(r'[إأآا]', 'ا', text)
        text = re.sub(r'[يى]', 'ي', text)
        text = re.sub(r'ة', 'ه', text)
        text = re.sub(r'ـ', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.lower().strip()

    @staticmethod
    def correct_typos_and_get_tokens(text):
        text = HealthAI.normalize_text(text)
        raw_tokens = text.split()
        tokens = []
        known_words = list(HealthAI.SYNONYMS_MAP.keys())
        for synonyms in HealthAI.SYNONYMS_MAP.values():
            for s in synonyms: known_words.extend(s.split())
        known_words = list(set([HealthAI.normalize_text(w) for w in known_words]))

        for token in raw_tokens:
            if token in HealthAI.STOP_WORDS or len(token) < 2: continue
            matches = difflib.get_close_matches(token, known_words, n=1, cutoff=0.7)
            tokens.append(matches[0] if matches else token)
        return tokens

    @staticmethod
    def extract_intents_and_expand(tokens):
        expanded_query = set(tokens)
        intents_detected = set()
        for token in tokens:
            for category, synonyms in HealthAI.SYNONYMS_MAP.items():
                norm_category = HealthAI.normalize_text(category)
                norm_synonyms = [HealthAI.normalize_text(s) for s in synonyms]
                if token == norm_category or any(token in s for s in norm_synonyms):
                    intents_detected.add(category)
                    expanded_query.add(norm_category)
                    for s in norm_synonyms: expanded_query.update(s.split())
        return list(expanded_query), list(intents_detected)

    @staticmethod
    def calculate_score(expanded_query, product):
        doc_name = HealthAI.normalize_text(product.get('name', ''))
        doc_desc = HealthAI.normalize_text(product.get('description', ''))
        doc_tags = HealthAI.normalize_text(product.get('tags', ''))
        full_doc = f"{doc_name} {doc_desc} {doc_tags}"
        
        score = 0.0
        matched_words = []
        for word in expanded_query:
            if word in full_doc:
                weight = 1.0
                if word in doc_name: weight += 2.0
                if doc_tags and word in doc_tags: weight += 1.5
                score += weight
                matched_words.append(word)
        return score, list(set(matched_words))

    @staticmethod
    def suggest_products(user_input, all_products, top_n=3):
        tokens = HealthAI.correct_typos_and_get_tokens(user_input)
        if not tokens: return []
        expanded_query, intents = HealthAI.extract_intents_and_expand(tokens)
        
        scored_products = []
        for p in all_products:
            score, matched_words = HealthAI.calculate_score(expanded_query, p)
            if score >= 1.0 and p.get('quantity', 1) > 0:
                scored_products.append({"product": p, "score": score, "matches": matched_words})

        scored_products.sort(key=lambda x: x['score'], reverse=True)
        results = []
        for item in scored_products[:top_n]:
            p = item['product']
            score = item['score']
            if score >= 4.0: explanation = f"⭐ خيار ممتاز ومحلي! مرتبط بـ: ({'، '.join(item['matches'][:2])})."
            elif intents: explanation = f"بناءً على التحليل المحلي، هذا المنتج مخصص لمشاكل ({' و '.join(intents[:2])})."
            else: explanation = f"هذا المنتج قد يساعد في تخفيف الأعراض المذكورة."
            results.append({"product": p, "explanation": "⚡ (Offline): " + explanation})
        return results