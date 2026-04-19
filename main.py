import flet as ft
import sqlite3
import json
from database import Database
from ai_engine import HealthAI

def main(page: ft.Page):
    # ==========================================
    # 1. إعدادات النافذة والتصميم (متجاوب مع الجوال)
    # ==========================================
    page.title = "متجر المنتجات الصحية الذكي"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # ==========================================
    # 2. حالة التطبيق وقاعدة البيانات
    # ==========================================
    db = Database()
    app_state = {
        "user": None,
        "cart": []
    }

    # ==========================================
    # 3. دوال مساعدة والإشعارات
    # ==========================================
    def nav(route):
        page.run_task(page.push_route, route)

    def go_back(e=None):
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            nav(top_view.route)

    def show_snack(message, color=ft.Colors.GREEN_600):
        icon = ft.Icons.CHECK_CIRCLE if color == ft.Colors.GREEN_600 else ft.Icons.ERROR
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(icon, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, expand=True)
            ]),
            bgcolor=color,
            duration=3000,
            behavior=ft.SnackBarBehavior.FLOATING,
            margin=20
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def update_cart_badges():
        total_items = sum(item['qty'] for item in app_state['cart'])
        for view in page.views:
            if view.appbar and view.appbar.actions:
                for action in view.appbar.actions:
                    if isinstance(action, ft.Stack) and len(action.controls) > 1:
                        badge_container = action.controls[1]
                        if isinstance(badge_container, ft.Container) and isinstance(badge_container.content, ft.Text):
                            badge_container.content.value = str(total_items)
                            badge_container.visible = total_items > 0
        page.update()

    def add_to_cart(product):
        existing_item = next((item for item in app_state['cart'] if item['product']['id'] == product['id']), None)
        if existing_item:
            existing_item['qty'] += 1
        else:
            app_state['cart'].append({'product': product, 'qty': 1})
        show_snack(f"🛒 تمت إضافة '{product['name']}' إلى السلة", ft.Colors.GREEN_600)
        update_cart_badges()

    def get_appbar_actions():
        total_items = sum(item['qty'] for item in app_state['cart'])
        cart_badge = ft.Container(
            content=ft.Text(str(total_items), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
            bgcolor=ft.Colors.RED_600, border_radius=10, padding=3, right=0, top=0, visible=total_items > 0, width=20, height=20
        )
        cart_btn = ft.Stack([ft.IconButton(ft.Icons.SHOPPING_CART, on_click=lambda e: nav("/cart"), tooltip="السلة"), cart_badge], width=45, height=45)
        actions = [ft.IconButton(ft.Icons.PERSON, on_click=lambda e: nav("/profile"), tooltip="الملف الشخصي"), cart_btn]
        if app_state['user'] and app_state['user'].get('is_admin'):
            actions.insert(0, ft.IconButton(ft.Icons.ADMIN_PANEL_SETTINGS, on_click=lambda e: nav("/admin"), tooltip="لوحة التحكم"))
        return actions

    # ==========================================
    # 4. بناء الواجهات (Views Builders)
    # ==========================================

    # --- 1. شاشة الدخول (تصميم Glassmorphism) ---
    def build_login_view():
        email_input = ft.TextField(label="البريد الإلكتروني", border_radius=12, prefix_icon=ft.Icons.EMAIL, border_color=ft.Colors.BLUE_300)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK, border_color=ft.Colors.BLUE_300)
        
        def do_login(e):
            if not email_input.value or not pass_input.value: return show_snack("أدخل البريد وكلمة المرور!", ft.Colors.RED_500)
            user = db.authenticate_user(email_input.value, pass_input.value)
            if user:
                app_state['user'] = dict(user)
                role = "المدير" if user['is_admin'] else "العميل"
                show_snack(f"أهلاً بك يا {role} {user['name']} 👋", ft.Colors.GREEN_600)
                nav("/home")
            else: show_snack("البيانات غير صحيحة!", ft.Colors.RED_500)

        form_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.HEALTH_AND_SAFETY, size=90, color=ft.Colors.BLUE_400),
                    ft.Text("المتجر الذكي", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=15),
                    email_input,
                    pass_input,
                    ft.Container(height=10),
                    ft.Button(content=ft.Text("تسجيل الدخول", size=16, weight=ft.FontWeight.BOLD), on_click=do_login, height=55, width=float('inf'), style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ft.TextButton("ليس لديك حساب؟ سجل الآن", on_click=lambda e: nav("/register"))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=30,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            blur=15,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
            ),
            width=400,
        )

        return ft.View(
            route="/login",
            padding=0,
            controls=[
                ft.Container(
                    content=ft.Column([form_card], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1.0, -1.0),
                        end=ft.Alignment(1.0, 1.0),
                        colors=[ft.Colors.BLUE_900, ft.Colors.BLACK]
                    ),
                    expand=True,
                    alignment=ft.Alignment(0.0, 0.0),
                    padding=20
                )
            ]
        )

    # --- 2. شاشة التسجيل العامة (تصميم Glassmorphism) ---
    def build_register_view():
        name_input = ft.TextField(label="الاسم الكامل", border_radius=12, prefix_icon=ft.Icons.PERSON, border_color=ft.Colors.BLUE_300)
        email_input = ft.TextField(label="البريد الإلكتروني", border_radius=12, prefix_icon=ft.Icons.EMAIL, border_color=ft.Colors.BLUE_300)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK, border_color=ft.Colors.BLUE_300)
        pass_confirm = ft.TextField(label="تأكيد كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK_OUTLINE, border_color=ft.Colors.BLUE_300)
        
        def do_register(e):
            if not name_input.value or not email_input.value or not pass_input.value or not pass_confirm.value: return show_snack("أكمل الحقول!", ft.Colors.RED_500)
            if pass_input.value != pass_confirm.value: return show_snack("كلمات المرور غير متطابقة!", ft.Colors.RED_500)
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)", (name_input.value, email_input.value, pass_input.value)); db.conn.commit()
                show_snack("تم إنشاء حساب العميل بنجاح!", ft.Colors.GREEN_600); nav("/login")
            except sqlite3.IntegrityError: show_snack("هذا البريد مسجل مسبقاً!", ft.Colors.RED_500)

        form_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=70, color=ft.Colors.BLUE_400),
                    ft.Text("إنشاء حساب عميل", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=10),
                    name_input, email_input, pass_input, pass_confirm,
                    ft.Container(height=10),
                    ft.Button(content=ft.Text("إنشاء الحساب", size=16, weight=ft.FontWeight.BOLD), on_click=do_register, height=55, width=float('inf'), style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ft.TextButton("لديك حساب؟ تسجيل دخول", on_click=lambda e: nav("/login"))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=30,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            blur=15,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE)),
                left=ft.BorderSide(1, ft.Colors.with_opacity(0.3, ft.Colors.WHITE))
            ),
            width=400,
        )

        return ft.View(
            route="/register",
            padding=0,
            controls=[
                ft.Container(
                    content=ft.Column([form_card], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1.0, -1.0),
                        end=ft.Alignment(1.0, 1.0),
                        colors=[ft.Colors.BLUE_900, ft.Colors.BLACK]
                    ),
                    expand=True,
                    alignment=ft.Alignment(0.0, 0.0),
                    padding=20
                )
            ]
        )

    # --- 3. المتجر الرئيسي ---
    def build_home_view():
        products_list = ft.ListView(expand=True, spacing=15, padding=10)
        for p in db.get_all_products():
            prod = dict(p)
            if prod['quantity'] > 0:
                products_list.controls.append(
                    ft.Card(
                        elevation=8, 
                        shape=ft.RoundedRectangleBorder(radius=15), 
                        content=ft.Container(
                            padding=20, 
                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                            border_radius=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.MEDICATION_LIQUID, color=ft.Colors.BLUE_400, size=30), 
                                    ft.Text(prod['name'], size=18, weight=ft.FontWeight.BOLD, expand=True), 
                                    ft.Text(f"${prod['price']}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
                                ]), 
                                ft.Text(prod['description'], size=14, color=ft.Colors.GREY_300), 
                                ft.Divider(height=10, color=ft.Colors.GREY_800),
                                ft.Row([
                                    ft.Text(f"المتوفر: {prod['quantity']}", size=12, color=ft.Colors.GREY_400), 
                                    ft.Button(content=ft.Text("أضف للسلة", weight=ft.FontWeight.BOLD), icon=ft.Icons.ADD_SHOPPING_CART, on_click=lambda e, p=prod: add_to_cart(p), bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                            ])
                        )
                    )
                )
        return ft.View(route="/home", controls=[
            ft.AppBar(title=ft.Text("المنتجات", weight=ft.FontWeight.BOLD), actions=get_appbar_actions(), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, automatically_imply_leading=False), 
            products_list, 
            ft.FloatingActionButton(icon=ft.Icons.PSYCHOLOGY, content=ft.Text("المساعد الذكي", weight=ft.FontWeight.BOLD), on_click=lambda e: nav("/ai"), bgcolor=ft.Colors.BLUE_500, width=180)
        ])

    # --- 4. الذكاء الاصطناعي (مدمج مع Gemini والمحرك المحلي) ---
    def build_ai_view():
        user_input = ft.TextField(label="كيف تشعر اليوم؟", multiline=True, min_lines=3, max_lines=5, border_radius=12, border_color=ft.Colors.BLUE_400)
        results_list = ft.ListView(expand=True, spacing=15)
        
        def analyze_input(e=None):
            safe_val = user_input.value or ""
            if not safe_val.strip(): return show_snack("يرجى كتابة وصف لحالتك أولاً!", ft.Colors.RED_500)
            
            # إظهار شاشة التحميل
            results_list.controls.clear()
            loading_indicator = ft.Row([ft.ProgressRing(width=20, height=20, color=ft.Colors.BLUE_400), ft.Text("الذكاء الاصطناعي يحلل حالتك...", color=ft.Colors.BLUE_200, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER)
            results_list.controls.append(loading_indicator)
            page.update()
            
            # التحقق من إعدادات الآدمن
            is_gemini_enabled = db.get_setting("gemini_enabled") == "1"
            api_key = db.get_setting("gemini_api_key")
            
            suggestions = None
            
            # محاولة استخدام Gemini إذا كان مفعلاً
            if is_gemini_enabled and api_key:
                suggestions = HealthAI.suggest_products_gemini(safe_val, db.get_all_products(), api_key)
            
            # (Fallback) استخدام المحرك المحلي إذا كان Gemini مغلقاً أو فشل الاتصال بالإنترنت
            if not suggestions:
                suggestions = HealthAI.suggest_products(safe_val, db.get_all_products())
                
            results_list.controls.clear()
            
            if not suggestions: 
                results_list.controls.append(ft.Text("لم نجد منتجات تطابق وصفك.", color=ft.Colors.ORANGE_400, text_align=ft.TextAlign.CENTER))
            else:
                for item in suggestions:
                    p = item['product']
                    results_list.controls.append(
                        ft.Card(
                            elevation=5, shape=ft.RoundedRectangleBorder(radius=15), 
                            content=ft.Container(
                                padding=15, border=ft.Border(top=ft.BorderSide(1, ft.Colors.BLUE_700), left=ft.BorderSide(1, ft.Colors.BLUE_700)), border_radius=15, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                content=ft.Column([
                                    ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER), ft.Text(p['name'], size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200, expand=True)]), 
                                    ft.Text(item['explanation'], color=ft.Colors.GREY_300, italic=True), 
                                    ft.Divider(height=10, color=ft.Colors.GREY_800), 
                                    ft.Row([ft.Text(f"${p['price']}", weight=ft.FontWeight.BOLD, size=18), ft.Button(content=ft.Text("أضف للسلة"), on_click=lambda e, prod=p: add_to_cart(prod), bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ])
                            )
                        )
                    )
            page.update()
            
        def set_quick_symptom(text): user_input.value = text; analyze_input()
        
        quick_chips = ft.Row(
            controls=[
                ft.Button(content=ft.Text("أرق"), on_click=lambda e: set_quick_symptom("أعاني من أرق وصعوبة شديدة في النوم"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), bgcolor=ft.Colors.BLUE_900)), 
                ft.Button(content=ft.Text("إرهاق"), on_click=lambda e: set_quick_symptom("أحس بخمول وضعف عام وإرهاق"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), bgcolor=ft.Colors.BLUE_900)), 
                ft.Button(content=ft.Text("مفاصل"), on_click=lambda e: set_quick_symptom("ألم في المفاصل وطقطقة بالركبة"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), bgcolor=ft.Colors.BLUE_900))
            ], 
            scroll=ft.ScrollMode.AUTO
        )
        
        return ft.View(route="/ai", controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("المساعد الذكي", weight=ft.FontWeight.BOLD), actions=get_appbar_actions(), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), 
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER_400), ft.Text("توصيات عامة وليست تشخيصاً طبياً.", color=ft.Colors.AMBER_400, weight=ft.FontWeight.BOLD, expand=True)]), bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER), padding=10, border_radius=10), 
            ft.Text("تشخيص سريع:", color=ft.Colors.GREY_400, size=14), quick_chips, ft.Container(height=5), user_input, 
            ft.Button(content=ft.Text("تحليل الحالة الذكي", weight=ft.FontWeight.BOLD, size=16), icon=ft.Icons.SEARCH, on_click=analyze_input, height=55, width=float('inf'), bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))), 
            ft.Divider(color=ft.Colors.TRANSPARENT), results_list
        ], padding=20)

    # --- 5. السلة ---
    def build_cart_view():
        cart_list = ft.ListView(expand=True, spacing=10)
        total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
        for item in app_state['cart']: 
            cart_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.SHOPPING_BAG, color=ft.Colors.BLUE_400, size=30), title=ft.Text(item['product']['name'], weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"الكمية: {item['qty']} | الإجمالي: ${item['product']['price'] * item['qty']}"), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, shape=ft.RoundedRectangleBorder(radius=10)))
            
        def proceed_to_checkout(e):
            if not app_state['cart']: return show_snack("سلتك فارغة!", ft.Colors.RED_500)
            nav("/checkout")
            
        return ft.View(route="/cart", controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("سلة المشتريات"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), 
            cart_list if app_state['cart'] else ft.Column([ft.Icon(ft.Icons.REMOVE_SHOPPING_CART, size=80, color=ft.Colors.GREY_600), ft.Text("سلتك فارغة حالياً.", size=18)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True), 
            ft.Divider(), 
            ft.Row([ft.Text("الإجمالي الكلي:", size=20, weight=ft.FontWeight.BOLD), ft.Text(f"${total_price}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
            ft.Container(height=10), 
            ft.Button(content=ft.Text("متابعة الدفع", size=18, weight=ft.FontWeight.BOLD), on_click=proceed_to_checkout, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, height=55, width=float('inf'), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))
        ], padding=20)

    # --- 6. الدفع ---
    def build_checkout_view():
        total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
        address_input = ft.TextField(label="عنوان التوصيل بالتفصيل", multiline=True, min_lines=2, border_radius=10, border_color=ft.Colors.BLUE_300)
        payment_method = ft.Dropdown(label="طريقة الدفع", options=[ft.dropdown.Option("الدفع عند الاستلام (كاش)"), ft.dropdown.Option("البطاقة الائتمانية")], value="الدفع عند الاستلام (كاش)", border_radius=10)
        
        def confirm_order(e):
            safe_address = address_input.value or ""
            if not safe_address.strip(): return show_snack("اكتب عنوان التوصيل!", ft.Colors.RED_500)
            order_id = db.create_order(app_state['user']['id'], app_state['cart'], total_price)
            app_state['cart'].clear() 
            nav("/home")
            show_snack(f"تم تأكيد الطلب بنجاح! رقم: #{order_id}", ft.Colors.GREEN_600)
            
        return ft.View(route="/checkout", controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("إتمام الطلب"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), 
            ft.Text("ملخص الطلب", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200), 
            ft.Container(content=ft.Column([
                ft.Row([ft.Text("عدد المنتجات:", size=16), ft.Text(str(sum(item['qty'] for item in app_state['cart'])), size=16, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                ft.Divider(color=ft.Colors.GREY_800),
                ft.Row([ft.Text("المبلغ المطلوب:", size=18), ft.Text(f"${total_price}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]), padding=20, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border_radius=15), 
            ft.Container(height=10),
            address_input, 
            payment_method, 
            ft.Container(expand=True), 
            ft.Button(content=ft.Text("تأكيد الطلب نهائياً", size=18, weight=ft.FontWeight.BOLD), icon=ft.Icons.CHECK_CIRCLE, on_click=confirm_order, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, height=55, width=float('inf'), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))
        ], padding=20)

    # --- 7. الملف الشخصي ---
    def build_profile_view():
        orders_list = ft.ListView(expand=True, spacing=10)
        for o in db.conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (app_state['user']['id'],)).fetchall(): 
            orders_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.BLUE_400), title=ft.Text(f"طلب: #{o['id']}", weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"الإجمالي: ${o['total_price']}"), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, shape=ft.RoundedRectangleBorder(radius=10)))
            
        def logout(e): app_state['user'] = None; app_state['cart'].clear(); nav("/login"); show_snack("تم تسجيل الخروج", ft.Colors.GREEN_600)
        
        role_text = "المدير العام 🛡️" if app_state['user']['is_admin'] else "عميل 👤"
        
        profile_card = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_300), 
                ft.Text(app_state['user']['name'], size=24, weight=ft.FontWeight.BOLD), 
                ft.Text(role_text, color=ft.Colors.AMBER if app_state['user']['is_admin'] else ft.Colors.GREY_400, size=16),
                ft.Container(height=10),
                ft.Button(content=ft.Text("تسجيل خروج", weight=ft.FontWeight.BOLD), icon=ft.Icons.LOGOUT, on_click=logout, bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.RED), color=ft.Colors.RED_200)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border_radius=15,
            width=float('inf')
        )
        
        return ft.View(route="/profile", controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("الملف الشخصي"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), 
            profile_card, 
            ft.Divider(height=20), 
            ft.Text("سجل الطلبات:", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200), 
            orders_list
        ], padding=20)

    # --- 8. لوحة التحكم الشاملة (متجاوبة ومدمجة مع إعدادات الذكاء) ---
    def build_admin_view():
        stats = db.get_dashboard_stats()
        
        # إحصائيات متجاوبة
        stats_content = ft.Column([
            ft.Row([
                ft.Container(content=ft.Column([ft.Icon(ft.Icons.MONEY, color=ft.Colors.GREEN_400), ft.Text("المبيعات", color=ft.Colors.GREY_400), ft.Text(f"${stats['revenue']}", size=22, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, padding=15, border_radius=12, expand=True),
                ft.Container(content=ft.Column([ft.Icon(ft.Icons.SHOPPING_BAG, color=ft.Colors.BLUE_400), ft.Text("الطلبات", color=ft.Colors.GREY_400), ft.Text(str(stats['orders_count']), size=22, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, padding=15, border_radius=12, expand=True)
            ]),
            ft.Row([
                ft.Container(content=ft.Column([ft.Icon(ft.Icons.PEOPLE, color=ft.Colors.PURPLE_400), ft.Text("المستخدمين", color=ft.Colors.GREY_400), ft.Text(str(stats['users_count']), size=22, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, padding=15, border_radius=12, expand=True),
                ft.Container(content=ft.Column([ft.Icon(ft.Icons.INVENTORY, color=ft.Colors.ORANGE_400), ft.Text("المنتجات", color=ft.Colors.GREY_400), ft.Text(str(stats['products_count']), size=22, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, padding=15, border_radius=12, expand=True)
            ])
        ], spacing=15, scroll=ft.ScrollMode.AUTO)
        
        # حقول المنتجات بدون عرض ثابت لتتمدد حسب الشاشة
        p_name = ft.TextField(label="الاسم", border_radius=10)
        p_desc = ft.TextField(label="الوصف", multiline=True, border_radius=10)
        p_price = ft.TextField(label="السعر ($)", border_radius=10)
        p_qty = ft.TextField(label="الكمية", border_radius=10)
        p_tags = ft.TextField(label="الكلمات المفتاحية", border_radius=10)
        
        def save_product(e):
            if not p_name.value or not p_price.value or not p_qty.value: return show_snack("أكمل البيانات الأساسية", ft.Colors.RED)
            db.add_product(p_name.value, p_desc.value, float(p_price.value), int(p_qty.value), p_tags.value)
            show_snack("تمت إضافة المنتج!", ft.Colors.GREEN_600); nav("/admin")

        def del_product(pid): db.delete_product(pid); show_snack("تم حذف المنتج!", ft.Colors.ORANGE); nav("/admin")

        products_list = ft.ListView(expand=True, spacing=10)
        for p in db.get_all_products(): 
            products_list.controls.append(ft.ListTile(title=ft.Text(p['name'], weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"سعر: {p['price']}$ | متوفر: {p['quantity']}"), trailing=ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, pid=p['id']: del_product(pid)), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, shape=ft.RoundedRectangleBorder(radius=8)))

        products_content = ft.Column([
            ft.Text("إضافة منتج جديد:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300, size=16), 
            p_name, 
            ft.Row([ft.Container(content=p_price, expand=True), ft.Container(content=p_qty, expand=True)]), 
            p_desc, 
            p_tags, 
            ft.Button(content=ft.Text("حفظ المنتج", weight=ft.FontWeight.BOLD), icon=ft.Icons.SAVE, on_click=save_product, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, height=50, width=float('inf'), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), 
            ft.Divider(height=20), 
            ft.Text("المنتجات الحالية:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300, size=16), 
            products_list
        ], expand=True)

        # إدارة المستخدمين
        u_name = ft.TextField(label="اسم المستخدم", border_radius=10)
        u_email = ft.TextField(label="البريد الإلكتروني", border_radius=10)
        u_pass = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=10)
        u_role = ft.Dropdown(label="الصلاحية", options=[ft.dropdown.Option("عميل"), ft.dropdown.Option("مدير / موظف")], value="عميل", border_radius=10)

        def save_new_user(e):
            if not u_name.value or not u_email.value or not u_pass.value: return show_snack("يرجى تعبئة جميع الحقول!", ft.Colors.RED)
            is_adm = 1 if u_role.value == "مدير / موظف" else 0
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)", (u_name.value, u_email.value, u_pass.value, is_adm))
                db.conn.commit()
                show_snack("تمت إضافة المستخدم بنجاح!", ft.Colors.GREEN_600); nav("/admin")
            except sqlite3.IntegrityError:
                show_snack("هذا البريد مسجل مسبقاً!", ft.Colors.RED)

        users_list = ft.ListView(expand=True, spacing=10)
        def del_user(uid):
            db.conn.execute("DELETE FROM users WHERE id=?", (uid,)); db.conn.commit()
            show_snack("تم حذف المستخدم!", ft.Colors.RED); nav("/admin")
            
        all_sys_users = db.conn.execute("SELECT * FROM users WHERE id != ? ORDER BY id DESC", (app_state['user']['id'],)).fetchall()
        if not all_sys_users:
            users_list.controls.append(ft.Text("لا يوجد مستخدمين آخرين.", color=ft.Colors.GREY_500))
        else:
            for u in all_sys_users:
                r_text = "مدير/موظف 🛡️" if u['is_admin'] == 1 else "عميل 👤"
                r_color = ft.Colors.AMBER if u['is_admin'] == 1 else ft.Colors.GREY_400
                users_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.BLUE_200), title=ft.Row([ft.Text(u['name'], weight=ft.FontWeight.BOLD), ft.Text(r_text, color=r_color, size=11)]), subtitle=ft.Text(u['email'], size=12), trailing=ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_400, on_click=lambda e, uid=u['id']: del_user(uid)), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, shape=ft.RoundedRectangleBorder(radius=8)))

        users_content = ft.Column([
            ft.Text("إضافة مستخدم جديد:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300, size=16),
            u_name, u_email, u_pass, u_role,
            ft.Button(content=ft.Text("إضافة المستخدم", weight=ft.FontWeight.BOLD), icon=ft.Icons.PERSON_ADD, on_click=save_new_user, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, height=50, width=float('inf'), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))),
            ft.Divider(height=20),
            ft.Text("إدارة المستخدمين المسجلين:", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300, size=16), 
            users_list
        ], expand=True)

        # إدارة الطلبات
        orders_list = ft.ListView(expand=True, spacing=10)
        all_orders = db.get_all_orders()
        if not all_orders:
            orders_list.controls.append(ft.Text("لا توجد طلبات مسجلة حتى الآن.", color=ft.Colors.GREY_500))
        else:
            for o in all_orders: 
                orders_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.LOCAL_SHIPPING, color=ft.Colors.GREEN_400), title=ft.Text(f"طلب #{o['id']} - عميل #{o['user_id']}", weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"المبلغ: {o['total_price']}$ - التاريخ: {o['created_at'].split(' ')[0]}"), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, shape=ft.RoundedRectangleBorder(radius=8)))
        orders_content = ft.Column([ft.Text("سجل الطلبات الشامل", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300), ft.Divider(), orders_list], expand=True)

        # إعدادات الذكاء الاصطناعي (Gemini + Offline)
        gemini_switch = ft.Switch(label="تفعيل محرك Gemini السحابي 🌐", value=(db.get_setting("gemini_enabled") == "1"), active_color=ft.Colors.GREEN_400)
        gemini_key_input = ft.TextField(label="مفتاح API (Gemini Key)", value=db.get_setting("gemini_api_key"), password=True, can_reveal_password=True, border_radius=10)
        
        def save_ai_settings(e):
            db.set_setting("gemini_enabled", "1" if gemini_switch.value else "0")
            db.set_setting("gemini_api_key", gemini_key_input.value)
            show_snack("تم حفظ إعدادات الذكاء الاصطناعي بنجاح!", ft.Colors.GREEN_600)

        ai_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.CLOUD_DONE, color=ft.Colors.BLUE_400), ft.Text("إعدادات الذكاء السحابي", color=ft.Colors.BLUE_400, weight=ft.FontWeight.BOLD, size=18)]), 
            ft.Container(content=ft.Column([
                ft.Text("ربط التطبيق مع سيرفرات جوجل (Gemini) لفهم وتبرير طبي فائق الدقة. يتطلب إنترنت.", color=ft.Colors.GREY_400, size=12),
                gemini_switch,
                gemini_key_input,
                ft.Button(content=ft.Text("حفظ إعدادات الربط", weight=ft.FontWeight.BOLD), icon=ft.Icons.SAVE, on_click=save_ai_settings, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=float('inf'), height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
            ]), padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, border_radius=12),
            
            ft.Divider(height=20),
            ft.Row([ft.Icon(ft.Icons.OFFLINE_BOLT, color=ft.Colors.TEAL_400), ft.Text("المحرك المحلي (Offline)", color=ft.Colors.TEAL_400, weight=ft.FontWeight.BOLD, size=18)]), 
            ft.Text("هذا المحرك يعمل تلقائياً في حال فشل الاتصال بالإنترنت أو إيقاف Gemini أعلاه.", color=ft.Colors.GREY_400, size=12),
            ft.TextField(multiline=True, min_lines=6, max_lines=8, value=json.dumps(HealthAI.SYNONYMS_MAP, ensure_ascii=False, indent=2), label="خريطة المفاهيم (JSON)", border_radius=10, read_only=True), 
        ], expand=True, scroll=ft.ScrollMode.AUTO)

        content_area = ft.Container(content=stats_content, expand=True, padding=10)
        tab_btns = []

        def change_tab(index, content_ctrl):
            content_area.content = content_ctrl
            for i, btn in enumerate(tab_btns):
                btn.style = ft.ButtonStyle(color=ft.Colors.BLUE_300 if i == index else ft.Colors.GREY_500)
            page.update()

        def create_tab_btn(title, icon, index, content_ctrl):
            return ft.TextButton(content=ft.Row([ft.Icon(icon), ft.Text(title, weight=ft.FontWeight.BOLD)]), style=ft.ButtonStyle(color=ft.Colors.BLUE_300 if index == 0 else ft.Colors.GREY_500), on_click=lambda e, i=index, c=content_ctrl: change_tab(i, c))

        tab_btns.extend([
            create_tab_btn("الإحصائيات", ft.Icons.DASHBOARD, 0, stats_content),
            create_tab_btn("المنتجات", ft.Icons.INVENTORY, 1, products_content),
            create_tab_btn("المستخدمين", ft.Icons.PEOPLE, 2, users_content),
            create_tab_btn("الطلبات", ft.Icons.RECEIPT, 3, orders_content),
            create_tab_btn("الذكاء", ft.Icons.SMART_TOY, 4, ai_content),
        ])

        # شريط التبويبات قابل للسحب يميناً ويساراً ليناسب الجوال
        custom_tabs_layout = ft.Column([ft.Row(controls=tab_btns, scroll=ft.ScrollMode.AUTO, spacing=15), ft.Divider(height=1, color=ft.Colors.GREY_800), content_area], expand=True)
        
        return ft.View(route="/admin", controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("الإدارة الشاملة"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), custom_tabs_layout], padding=10)

    # ==========================================
    # 6. نظام التوجيه (Routing System)
    # ==========================================
    def route_change(route):
        page.views.clear()
        if page.route not in ["/login", "/register"] and not app_state['user']: return nav("/login")
        if page.route == "/login": page.views.append(build_login_view())
        elif page.route == "/register": page.views.append(build_register_view())
        elif page.route == "/home": page.views.append(build_home_view())
        elif page.route == "/ai": page.views.extend([build_home_view(), build_ai_view()])
        elif page.route == "/cart": page.views.extend([build_home_view(), build_cart_view()])
        elif page.route == "/checkout": page.views.extend([build_home_view(), build_cart_view(), build_checkout_view()])
        elif page.route == "/profile": page.views.extend([build_home_view(), build_profile_view()])
        elif page.route == "/admin" and app_state['user'].get('is_admin'): page.views.extend([build_home_view(), build_admin_view()])
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = lambda view: go_back()
    nav("/login")

if __name__ == "__main__":
    ft.run(main)