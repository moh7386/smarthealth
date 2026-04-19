import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name="smart_store.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row 
        self.create_tables()
        self.seed_data()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, is_admin INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL, price REAL NOT NULL, quantity INTEGER NOT NULL, category TEXT NOT NULL, symptoms_tags TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, total_price REAL NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(product_id) REFERENCES products(id))''')
        
        # الجدول الخاص بإعدادات الذكاء الاصطناعي (Gemini)
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key_name TEXT PRIMARY KEY, key_value TEXT)''')
        
        self.conn.commit()

    def seed_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            # قائمة بـ 50 منتج صحي معتمد بدقة
            products = [
                # --- الفيتامينات والمعادن ---
                ("مغنيسيوم جلايسينات", "يساعد على الاسترخاء، تحسين جودة النوم، وتخفيف الشد العضلي.", 15.0, 50, "معادن", json.dumps(["نوم", "ارق", "تعب", "عضلات", "ارهاق", "شد", "توتر"])),
                ("فيتامين د3 5000 وحدة", "يدعم صحة العظام، يقوي المناعة، ويحسن المزاج ويقلل الخمول.", 12.0, 100, "فيتامينات", json.dumps(["عظام", "مناعة", "اكتئاب", "خمول", "مفاصل", "كسل"])),
                ("فيتامين سي كومبلكس", "مضاد أكسدة قوي، يحمي من نزلات البرد ويعطي نشاطاً عاماً.", 10.0, 80, "فيتامينات", json.dumps(["زكام", "مناعة", "برد", "تعب", "انفلونزا"])),
                ("زنك بيكولينات 50 مج", "يدعم جهاز المناعة، يحسن صحة الجلد والشعر، ويسرع التئام الجروح.", 14.0, 60, "معادن", json.dumps(["مناعة", "شعر", "بشرة", "حبوب", "جروح"])),
                ("حديد بيسجلايسينات", "يعالج فقر الدم (الأنيميا)، يقلل الدوخة والشحوب، لطيف على المعدة.", 16.0, 45, "معادن", json.dumps(["دوخة", "انيميا", "دم", "شحوب", "ضعف", "تساقط"])),
                ("فيتامين ب12 (ميثيلكوبالامين)", "يدعم صحة الأعصاب، يقلل التنميل، ويزيد من طاقة الجسم.", 18.0, 70, "فيتامينات", json.dumps(["اعصاب", "تنميل", "طاقة", "ارهاق", "رعشة"])),
                ("فيتامين ب كومبلكس", "مجموعة فيتامينات ب لتحويل الغذاء لطاقة ودعم الجهاز العصبي.", 20.0, 55, "فيتامينات", json.dumps(["اعصاب", "طاقة", "ارهاق", "ايض", "تركيز"])),
                ("كالسيوم مع فيتامين د3", "مزيج مثالي لتقوية العظام والأسنان ومنع الهشاشة.", 13.0, 90, "معادن", json.dumps(["عظام", "اسنان", "هشاشة", "كسور", "مفاصل"])),
                ("بوتاسيوم 99 مج", "ينظم ضغط الدم، يحافظ على توازن السوائل ويمنع تشنج العضلات.", 11.0, 40, "معادن", json.dumps(["ضغط", "سوائل", "عضلات", "تشنج", "قلب"])),
                ("سيلينيوم 200 ميكروجرام", "مضاد أكسدة يدعم وظائف الغدة الدرقية ويحمي الخلايا.", 15.0, 30, "معادن", json.dumps(["غدة", "درقية", "مناعة", "ايض", "شعر"])),
                ("فيتامين هـ (Vitamin E)", "فيتامين الجمال، يرطب البشرة ويقلل التجاعيد ويدعم صحة القلب.", 17.0, 50, "فيتامينات", json.dumps(["بشرة", "تجاعيد", "قلب", "جفاف", "ندبات"])),
                ("حمض الفوليك (Folic Acid)", "ضروري للحوامل لمنع تشوهات الجنين ويدعم إنتاج خلايا الدم.", 9.0, 120, "فيتامينات", json.dumps(["حمل", "جنين", "دم", "انيميا", "نساء"])),
                ("بيوتين 10,000 ميكروجرام", "الفيتامين الأساسي لوقف تساقط الشعر وتقوية الأظافر الضعيفة.", 22.0, 65, "فيتامينات", json.dumps(["شعر", "تساقط", "اظافر", "تكسر", "صلع"])),
                ("فيتامين أ (Vitamin A)", "يعزز صحة الرؤية الليلية ويجدد خلايا البشرة ويعالج حب الشباب.", 14.0, 45, "فيتامينات", json.dumps(["نظر", "عين", "بشرة", "حبوب", "رؤية"])),
                ("ملتي فيتامين للرجال", "تركيبة شاملة تدعم طاقة الرجل، البروستاتا، والنشاط اليومي.", 25.0, 40, "فيتامينات", json.dumps(["طاقة", "ارهاق", "رجال", "بروستاتا", "نشاط"])),
                ("ملتي فيتامين للنساء", "تركيبة شاملة تدعم الهرمونات، الشعر، البشرة، والعظام.", 25.0, 40, "فيتامينات", json.dumps(["طاقة", "نساء", "شعر", "عظام", "هرمونات"])),

                # --- المكملات التخصصية (Specialty) ---
                ("أوميجا 3 (زيت السمك)", "يدعم صحة القلب، يحسن التركيز ونشاط الدماغ ويقلل الكوليسترول.", 20.0, 80, "مكملات", json.dumps(["تركيز", "نسيان", "قلب", "كوليسترول", "مفاصل"])),
                ("بروبيوتيك 50 مليار", "بكتيريا نافعة لدعم صحة القولون، تقليل الغازات وتحسين الهضم.", 28.0, 50, "مكملات", json.dumps(["قولون", "غازات", "هضم", "امساك", "معدة", "انتفاخ"])),
                ("ميلاتونين 5 مجم", "هرمون النوم الطبيعي، يساعد على الدخول في النوم سريعاً وتعديل الساعة البيولوجية.", 12.0, 100, "مكملات", json.dumps(["نوم", "ارق", "سهر", "سفر"])),
                ("كولاجين بحري متحلل", "يحسن مرونة البشرة، يخفف آلام المفاصل، ويقوي الشعر.", 35.0, 30, "مكملات", json.dumps(["بشرة", "تجاعيد", "مفاصل", "شعر", "شيخوخة"])),
                ("جلوكوزامين وكوندرويتين", "الداعم الأول لصحة المفاصل والغضاريف وتقليل آلام الخشونة.", 24.0, 45, "مكملات", json.dumps(["مفاصل", "خشونة", "ركبة", "عظام", "غضاريف"])),
                ("كو إنزيم كيو 10 (CoQ10)", "إنزيم الطاقة الخلوية، ممتاز لدعم عضلة القلب وحيوية الجسم.", 30.0, 35, "مكملات", json.dumps(["قلب", "طاقة", "خلايا", "ارهاق", "شرايين"])),
                ("حمض الهيالورونيك", "مرطب داخلي للبشرة والمفاصل، يعطي نضارة وحيوية ملحوظة.", 26.0, 40, "مكملات", json.dumps(["بشرة", "جفاف", "نضارة", "مفاصل", "ترطيب"])),
                ("لوتين وزياكسانثين", "مكمل لحماية العين من أشعة الشاشات الزرقاء وتقليل إجهاد النظر.", 19.0, 55, "مكملات", json.dumps(["عين", "نظر", "شاشات", "جفاف", "رؤية"])),
                ("سبيرولينا عضوية", "سوبر فود غني بالبروتين والحديد، يعطي طاقة وينقي الجسم من السموم.", 22.0, 60, "مكملات", json.dumps(["ديتوكس", "طاقة", "سموم", "نباتي", "انيميا"])),
                ("إنزيمات هضمية", "تساعد في تكسير الدهون والبروتينات لتخفيف ثقل المعدة بعد الأكل.", 18.0, 50, "مكملات", json.dumps(["هضم", "ثقل", "معدة", "حموضة", "تخمة"])),

                # --- الأعشاب والنباتات الطبية ---
                ("أشواجاندا KSM-66", "عشبة أدابتوجينيك تقلل التوتر، تخفض الكورتيزول وتحسن المزاج.", 21.0, 65, "أعشاب", json.dumps(["توتر", "قلق", "ضغط", "نفسية", "اكتئاب", "كورتيزول"])),
                ("جنسنج كوري أحمر", "منشط طبيعي قوي للرجال والنساء، يزيد النشاط البدني والذهني.", 24.0, 40, "أعشاب", json.dumps(["طاقة", "ضعف", "تركيز", "نشاط", "خمول"])),
                ("جنكة بيلوبا (Ginkgo)", "تنشط الدورة الدموية في الدماغ، ممتازة لتقوية الذاكرة وعلاج النسيان.", 16.0, 50, "أعشاب", json.dumps(["ذاكرة", "نسيان", "تركيز", "دماغ", "دورة"])),
                ("كركمين مع فلفل أسود", "أقوى مضاد التهاب طبيعي، يخفف التهابات المفاصل والجسم عموماً.", 23.0, 55, "أعشاب", json.dumps(["التهاب", "مفاصل", "الم", "مناعة", "تورم"])),
                ("مستخلص الثوم المعتق", "ينقي الدم، يدعم صحة القلب ويخفض ضغط الدم بدون رائحة مزعجة.", 15.0, 60, "أعشاب", json.dumps(["ضغط", "قلب", "كوليسترول", "شرايين", "مناعة"])),
                ("زيت الحبة السوداء", "معزز مناعي شامل يخفف الحساسية ومشاكل الجهاز التنفسي.", 19.0, 45, "أعشاب", json.dumps(["مناعة", "حساسية", "صدر", "كحة", "ربو"])),
                ("شاي البابونج النقي", "يهدئ الأعصاب، يقلل تشنجات المعدة، ويساعد على استرخاء ما قبل النوم.", 8.0, 100, "أعشاب", json.dumps(["معدة", "مغص", "اعصاب", "نوم", "استرخاء"])),
                ("زيت النعناع كبسولات", "ممتاز لمرضى القولون العصبي، يزيل التشنجات والانتفاخات فوراً.", 14.0, 50, "أعشاب", json.dumps(["قولون", "غازات", "مغص", "انتفاخ", "عصبي"])),
                ("جذور الماكا (Maca)", "توازن الهرمونات بشكل طبيعي وتزيد النشاط والطاقة وتخفف أعراض انقطاع الطمث.", 20.0, 40, "أعشاب", json.dumps(["هرمونات", "نساء", "طاقة", "مزاج", "خصوبة"])),
                ("جذور الناردين (Valerian)", "عشبة طبية قوية لعلاج الأرق الشديد والمساعدة على النوم العميق.", 17.0, 45, "أعشاب", json.dumps(["ارق", "نوم", "سهر", "قلق", "تفكير"])),
                ("نبتة سانت جون", "مضاد اكتئاب طبيعي، ترفع مستويات السيروتونين وتحسن الحالة المزاجية.", 22.0, 35, "أعشاب", json.dumps(["اكتئاب", "حزن", "مزاج", "نفسية", "ضيق"])),
                ("حليب الشوك (Milk Thistle)", "العشبة الأولى لتنظيف الكبد من السموم ودعم وظائفه وتجديد خلاياه.", 21.0, 40, "أعشاب", json.dumps(["كبد", "سموم", "ديتوكس", "دهون", "تليف"])),
                ("البلميط المنشاري", "يدعم صحة البروستاتا عند الرجال ويقلل من تكرار التبول الليلي.", 25.0, 30, "أعشاب", json.dumps(["بروستاتا", "تبول", "رجال", "شعر"])),
                ("عشبة القنفذية (Echinacea)", "ترفع مناعة الجسم بشكل فوري عند أول علامات الإصابة بالزكام.", 16.0, 55, "أعشاب", json.dumps(["زكام", "برد", "مناعة", "حلق", "عطس"])),

                # --- التغذية الرياضية (Sports Nutrition) ---
                ("بروتين مصل اللبن (Whey)", "بروتين سريع الامتصاص لبناء العضلات والاستشفاء بعد التمرين.", 45.0, 20, "رياضة", json.dumps(["عضلات", "تمرين", "نحافة", "رياضة", "بناء"])),
                ("كرياتين مونوهيدرات", "يزيد من القوة البدنية وحجم العضلات وطاقة التحمل أثناء التدريب.", 30.0, 35, "رياضة", json.dumps(["قوة", "عضلات", "تحمل", "تمرين", "طاقة"])),
                ("أحماض BCAA", "تمنع الهدم العضلي أثناء التمارين الشاقة وتقلل الإجهاد العضلي.", 28.0, 40, "رياضة", json.dumps(["هدم", "اجهاد", "تمرين", "عضلات", "استشفاء"])),
                ("إل-كارنيتين (L-Carnitine)", "يحول الدهون المخزنة إلى طاقة، مما يساعد في حرق الدهون وإنقاص الوزن.", 25.0, 45, "رياضة", json.dumps(["تخسيس", "حرق", "دهون", "وزن", "طاقة"])),
                ("إل-أرجينين (L-Arginine)", "يوسع الأوعية الدموية مما يزيد ضخ الدم للعضلات ويعطي نشاطاً كبيراً.", 22.0, 40, "رياضة", json.dumps(["ضخ", "دورة", "دم", "طاقة", "عضلات"])),
                ("إل-جلوتامين (Glutamine)", "يسرع الاستشفاء العضلي بقوة ويدعم صحة جدار الأمعاء والمناعة.", 24.0, 35, "رياضة", json.dumps(["استشفاء", "عضلات", "مناعة", "امعاء", "تمرين"])),
                ("بيتا ألانين", "يمنع تراكم حمض اللاكتيك في العضلات، مما يؤخر التعب أثناء التمرين.", 20.0, 50, "رياضة", json.dumps(["تعب", "حرقان", "عضلات", "تمرين", "تحمل"])),
                ("سيترولين مالات", "يزيد من إنتاج أكسيد النيتريك لضخ دم خرافي وتأخير الإرهاق الرياضي.", 26.0, 30, "رياضة", json.dumps(["ضخ", "دم", "ارهاق", "عضلات", "طاقة"])),
                ("تورين (Taurine)", "يدعم صحة القلب والجهاز العصبي ويمنع الشد العضلي للرياضيين.", 15.0, 60, "رياضة", json.dumps(["شد", "قلب", "اعصاب", "رياضة", "تشنج"])),
                ("إل-ثيانين (L-Theanine)", "حمض أميني من الشاي الأخضر، يعطي تركيزاً عالياً وهدوءاً بدون نعاس.", 18.0, 45, "رياضة", json.dumps(["تركيز", "هدوء", "توتر", "دماغ", "انتباه"]))
            ]
            
            cursor.executemany('''INSERT INTO products (name, description, price, quantity, category, symptoms_tags) VALUES (?, ?, ?, ?, ?, ?)''', products)
            cursor.execute('''INSERT INTO users (name, email, password, is_admin) VALUES ('Admin', 'admin@store.com', 'admin123', 1)''')
            self.conn.commit()

    # ==========================================
    # إعدادات الذكاء الاصطناعي (Gemini)
    # ==========================================
    def get_setting(self, key_name, default=""):
        res = self.conn.execute("SELECT key_value FROM settings WHERE key_name = ?", (key_name,)).fetchone()
        return res['key_value'] if res else default

    def set_setting(self, key_name, key_value):
        self.conn.execute("INSERT OR REPLACE INTO settings (key_name, key_value) VALUES (?, ?)", (key_name, key_value))
        self.conn.commit()

    # ==========================================
    # دوال العمليات الأساسية
    # ==========================================
    def authenticate_user(self, email, password):
        return self.conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()

    def get_all_products(self):
        return self.conn.execute("SELECT * FROM products").fetchall()

    def update_inventory(self, product_id, qty):
        self.conn.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (qty, product_id))
        self.conn.commit()

    def create_order(self, user_id, cart_items, total):
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO orders (user_id, total_price, created_at) VALUES (?, ?, ?)", (user_id, total, date_now))
        order_id = cursor.lastrowid
        for item in cart_items:
            product_id = item['product']['id']
            qty = item['qty']
            cursor.execute("INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)", (order_id, product_id, qty))
            self.update_inventory(product_id, qty)
        self.conn.commit()
        return order_id

    # ========== دوال لوحة تحكم الآدمن (Admin CRUD) ==========
    def get_dashboard_stats(self):
        orders_count = self.conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        revenue = self.conn.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0.0
        users_count = self.conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
        products_count = self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        return {"orders_count": orders_count, "revenue": revenue, "users_count": users_count, "products_count": products_count}

    def add_product(self, name, desc, price, qty, tags):
        self.conn.execute('''INSERT INTO products (name, description, price, quantity, category, symptoms_tags) VALUES (?, ?, ?, ?, 'عام', ?)''', (name, desc, price, qty, json.dumps(tags.split(","))))
        self.conn.commit()

    def delete_product(self, product_id):
        self.conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        self.conn.commit()

    def get_all_users(self):
        return self.conn.execute("SELECT id, name, email FROM users WHERE is_admin=0 ORDER BY id DESC").fetchall()

    def delete_user(self, user_id):
        self.conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        self.conn.commit()

    def get_all_orders(self):
        return self.conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()