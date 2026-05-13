import flet as ft
import sqlite3
import json
import time
import asyncio
from database import Database
from ai_engine import HealthAI

def main(page: ft.Page):
    # ==========================================
    # 1. إعدادات النافذة والتصميم (Theme Palette المستوحى من الصورة)
    # ==========================================
    page.title = "متجر المنتجات الصحية الذكي"
    page.theme_mode = ft.ThemeMode.LIGHT 
    page.theme = ft.Theme(color_scheme_seed="#0b6b7a") # الأزرق المخضر الداكن (الأساسي)
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#eff5f7" # خلفية التطبيق الثلجية المريحة للعين (من الصورة)

    # ألوان ثوابت للتصميم
    PRIMARY = "#0b6b7a"
    PRIMARY_DARK = "#064650"
    BG_LIGHT = "#eff5f7"
    CARD_BG = ft.Colors.WHITE
    TEXT_DARK = "#1a2b3c"
    TEXT_MUTED = "#7a8b99"
    BORDER_LIGHT = "#dfeaef"
    DANGER = "#e65c5c"

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

    def show_snack(message, color=PRIMARY):
        icon = ft.Icons.CHECK_CIRCLE if color == PRIMARY else ft.Icons.ERROR
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

    def manage_cart(product, action="add"):
        if not app_state['user']:
            show_snack("يجب تسجيل الدخول أولاً!", DANGER)
            nav("/login")
            return

        cart = app_state['cart']
        existing = next((i for i in cart if i['product']['id'] == product['id']), None)

        if action == "add":
            if existing:
                existing['qty'] += 1
            else:
                cart.append({'product': product, 'qty': 1})
            show_snack(f"🛒 تمت الإضافة: {product['name']}", PRIMARY)
        elif action == "decrease" and existing:
            existing['qty'] -= 1
            if existing['qty'] <= 0:
                cart.remove(existing)
        elif action == "remove" and existing:
            cart.remove(existing)
            show_snack(f"🗑️ تم الحذف: {product['name']}", "#e69b5c")

        update_cart_badges()
        
        if hasattr(page, 'refresh_home') and page.route == "/home":
            page.refresh_home()
        if hasattr(page, 'refresh_cart') and page.route == "/cart":
            page.refresh_cart()

    def get_appbar_actions():
        total_items = sum(item['qty'] for item in app_state['cart'])
        cart_badge = ft.Container(
            content=ft.Text(str(total_items), size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
            bgcolor=DANGER, border_radius=10, padding=3, right=0, top=0, visible=total_items > 0, width=20, height=20
        )
        
        def handle_protected_route(route):
            if not app_state['user']:
                show_snack("يجب تسجيل الدخول أولاً", DANGER)
                nav("/login")
            else:
                nav(route)

        cart_btn = ft.Stack([ft.IconButton(ft.Icons.SHOPPING_CART, icon_color=PRIMARY_DARK, on_click=lambda e: handle_protected_route("/cart"), tooltip="السلة"), cart_badge], width=45, height=45)
        actions = [ft.IconButton(ft.Icons.PERSON, icon_color=PRIMARY_DARK, on_click=lambda e: handle_protected_route("/profile"), tooltip="الملف الشخصي"), cart_btn]
        if app_state['user'] and app_state['user'].get('is_admin'):
            actions.insert(0, ft.IconButton(ft.Icons.ADMIN_PANEL_SETTINGS, icon_color="#e69b5c", on_click=lambda e: nav("/admin"), tooltip="لوحة التحكم"))
        return actions

    # ==========================================
    # 4. بناء الواجهات (Views Builders)
    # ==========================================

    # --- 1. شاشة الدخول ---
    def build_login_view():
        email_input = ft.TextField(label="البريد الإلكتروني", border_radius=12, prefix_icon=ft.Icons.EMAIL, border_color=BORDER_LIGHT, color=TEXT_DARK, bgcolor=CARD_BG)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK, border_color=BORDER_LIGHT, color=TEXT_DARK, bgcolor=CARD_BG)
        
        def do_login(e):
            if not email_input.value or not pass_input.value: return show_snack("أدخل البريد وكلمة المرور!", DANGER)
            user = db.authenticate_user(email_input.value, pass_input.value)
            if user:
                app_state['user'] = dict(user)
                role = "المدير" if user['is_admin'] else "العميل"
                show_snack(f"أهلاً بك يا {role} {user['name']} 👋", PRIMARY)
                nav("/home")
            else: show_snack("البيانات غير صحيحة!", DANGER)

        form_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.HEALTH_AND_SAFETY, size=90, color=PRIMARY),
                    ft.Text("المتجر الذكي", size=28, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK),
                    ft.Container(height=15),
                    email_input,
                    pass_input,
                    ft.Container(height=10),
                    ft.Container(content=ft.Text("تسجيل الدخول", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16), bgcolor=PRIMARY, padding=15, border_radius=12, alignment=ft.Alignment(0.0, 0.0), on_click=do_login, ink=True),
                    ft.TextButton("ليس لديك حساب؟ سجل الآن", on_click=lambda e: nav("/register"), style=ft.ButtonStyle(color=PRIMARY)),
                    ft.TextButton("تصفح المتجر كزائر", on_click=lambda e: nav("/home"), icon=ft.Icons.STOREFRONT, style=ft.ButtonStyle(color=TEXT_MUTED))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=30,
            border_radius=25,
            bgcolor=CARD_BG,
            border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT)),
            width=400,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.Colors.with_opacity(0.1, TEXT_DARK))
        )

        return ft.View(
            route="/login", padding=0, bgcolor=BG_LIGHT,
            controls=[
                ft.Container(
                    content=ft.Column([form_card], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                    gradient=ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(1.0, 1.0), colors=[PRIMARY, PRIMARY_DARK]),
                    expand=True, alignment=ft.Alignment(0.0, 0.0), padding=20
                )
            ]
        )

    # --- 2. شاشة التسجيل العامة ---
    def build_register_view():
        name_input = ft.TextField(label="الاسم الكامل", border_radius=12, prefix_icon=ft.Icons.PERSON, border_color=BORDER_LIGHT, bgcolor=CARD_BG)
        email_input = ft.TextField(label="البريد الإلكتروني", border_radius=12, prefix_icon=ft.Icons.EMAIL, border_color=BORDER_LIGHT, bgcolor=CARD_BG)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK, border_color=BORDER_LIGHT, bgcolor=CARD_BG)
        pass_confirm = ft.TextField(label="تأكيد كلمة المرور", password=True, can_reveal_password=True, border_radius=12, prefix_icon=ft.Icons.LOCK_OUTLINE, border_color=BORDER_LIGHT, bgcolor=CARD_BG)
        
        def do_register(e):
            if not name_input.value or not email_input.value or not pass_input.value or not pass_confirm.value: return show_snack("أكمل الحقول!", DANGER)
            if pass_input.value != pass_confirm.value: return show_snack("كلمات المرور غير متطابقة!", DANGER)
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)", (name_input.value, email_input.value, pass_input.value)); db.conn.commit()
                show_snack("تم إنشاء حساب العميل بنجاح!", PRIMARY); nav("/login")
            except sqlite3.IntegrityError: show_snack("هذا البريد مسجل مسبقاً!", DANGER)

        form_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=70, color=PRIMARY),
                    ft.Text("إنشاء حساب عميل", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK),
                    ft.Container(height=10),
                    name_input, email_input, pass_input, pass_confirm,
                    ft.Container(height=10),
                    ft.Container(content=ft.Text("إنشاء الحساب", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=16), bgcolor=PRIMARY, padding=15, border_radius=12, alignment=ft.Alignment(0.0, 0.0), on_click=do_register, ink=True),
                    ft.TextButton("لديك حساب؟ تسجيل دخول", on_click=lambda e: nav("/login"), style=ft.ButtonStyle(color=PRIMARY))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=30, border_radius=25, bgcolor=CARD_BG, 
            border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT)),
            width=400,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.Colors.with_opacity(0.1, TEXT_DARK))
        )

        return ft.View(
            route="/register", padding=0, bgcolor=BG_LIGHT,
            controls=[
                ft.Container(
                    content=ft.Column([form_card], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                    gradient=ft.LinearGradient(begin=ft.Alignment(-1.0, -1.0), end=ft.Alignment(1.0, 1.0), colors=[PRIMARY, PRIMARY_DARK]),
                    expand=True, alignment=ft.Alignment(0.0, 0.0), padding=20
                )
            ]
        )

    # --- 3. المتجر الرئيسي ---
    def build_home_view():
        products_list = ft.ListView(expand=True, spacing=15, padding=10)
        
        def update_home_ui():
            products_list.controls.clear()
            for p in db.get_all_products():
                prod = dict(p)
                if prod['quantity'] > 0:
                    in_cart = next((item for item in app_state['cart'] if item['product']['id'] == prod['id']), None)
                    
                    if in_cart:
                        action_ui = ft.Row([
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, on_click=lambda e, p=prod: manage_cart(p, "remove")),
                            ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=TEXT_MUTED, on_click=lambda e, p=prod: manage_cart(p, "decrease")),
                            ft.Text(str(in_cart['qty']), weight=ft.FontWeight.BOLD, size=18, color=PRIMARY_DARK),
                            ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=PRIMARY, on_click=lambda e, p=prod: manage_cart(p, "add"))
                        ], alignment=ft.MainAxisAlignment.END, spacing=0)
                    else:
                        action_ui = ft.Container(content=ft.Row([ft.Icon(ft.Icons.ADD_SHOPPING_CART, size=18, color=ft.Colors.WHITE), ft.Text("أضف للسلة", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor=PRIMARY, padding=8, border_radius=8, on_click=lambda e, p=prod: manage_cart(p, "add"), ink=True)

                    products_list.controls.append(
                        ft.Card(
                            elevation=0, 
                            shape=ft.RoundedRectangleBorder(radius=15), 
                            content=ft.Container(
                                padding=20, 
                                bgcolor=CARD_BG,
                                border_radius=15,
                                border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT)),
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.MEDICATION_LIQUID, color=PRIMARY, size=30), 
                                        ft.Text(prod['name'], size=18, weight=ft.FontWeight.BOLD, color=TEXT_DARK, expand=True), 
                                        ft.Text(f"${prod['price']}", size=20, weight=ft.FontWeight.BOLD, color=PRIMARY)
                                    ]), 
                                    ft.Text(prod['description'], size=14, color=TEXT_MUTED), 
                                    ft.Divider(height=10, color=BORDER_LIGHT),
                                    ft.Row([
                                        ft.Text(f"المتوفر: {prod['quantity']}", size=12, color=TEXT_MUTED), 
                                        action_ui
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ])
                            )
                        )
                    )
            page.update()

        page.refresh_home = update_home_ui
        update_home_ui()

        return ft.View(route="/home", bgcolor=BG_LIGHT, controls=[
            ft.AppBar(title=ft.Text("المنتجات", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK), actions=get_appbar_actions(), bgcolor=CARD_BG, automatically_imply_leading=False), 
            products_list, 
            ft.FloatingActionButton(icon=ft.Icons.PSYCHOLOGY, content=ft.Text("المساعد الذكي", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), on_click=lambda e: nav("/ai"), bgcolor=PRIMARY, width=180)
        ])

    # --- 4. الذكاء الاصطناعي ---
    def build_ai_view():
        user_input = ft.TextField(label="كيف تشعر اليوم؟", multiline=True, min_lines=3, max_lines=5, border_radius=12, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        results_list = ft.ListView(expand=True, spacing=15)
        
        analyze_btn = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.SEARCH, color=ft.Colors.WHITE), ft.Text("تحليل الحالة الذكي", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=PRIMARY,
            padding=15,
            border_radius=12,
            ink=True
        )

        def do_heavy_lifting(safe_val):
            time.sleep(0.8) 
            is_gemini_enabled = db.get_setting("gemini_enabled") == "1"
            api_key = db.get_setting("gemini_api_key")
            sugs = None
            if is_gemini_enabled and api_key:
                sugs = HealthAI.suggest_products_gemini(safe_val, db.get_all_products(), api_key)
            if not sugs:
                sugs = HealthAI.suggest_products(safe_val, db.get_all_products())
            return sugs

        async def analyze_input(e=None):
            safe_val = user_input.value or ""
            if not safe_val.strip(): return show_snack("يرجى كتابة وصف لحالتك أولاً!", DANGER)
            
            user_input.disabled = True
            analyze_btn.disabled = True
            analyze_btn.bgcolor = TEXT_MUTED
            
            results_list.controls.clear()
            loading_indicator = ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=60, height=60, color=PRIMARY, stroke_width=6),
                    ft.Container(height=15),
                    ft.Text("جاري تحليل حالتك الطبية بدقة...", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD, size=18)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0.0, 0.0),
                padding=50
            )
            results_list.controls.append(loading_indicator)
            page.update()
            
            suggestions = await asyncio.to_thread(do_heavy_lifting, safe_val)
            
            results_list.controls.clear()
            
            if not suggestions: 
                results_list.controls.append(ft.Text("لم نجد منتجات تطابق وصفك حالياً.", color="#e69b5c", text_align=ft.TextAlign.CENTER))
            else:
                for item in suggestions:
                    p = item['product']
                    results_list.controls.append(
                        ft.Card(
                            elevation=0, shape=ft.RoundedRectangleBorder(radius=15), 
                            content=ft.Container(
                                padding=15, border=ft.Border(top=ft.BorderSide(2, PRIMARY), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT)), border_radius=15, bgcolor=CARD_BG,
                                content=ft.Column([
                                    ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color="#e69b5c"), ft.Text(p['name'], size=18, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK, expand=True)]), 
                                    ft.Text(item['explanation'], color=TEXT_MUTED, italic=True), 
                                    ft.Divider(height=10, color=BORDER_LIGHT), 
                                    ft.Row([
                                        ft.Text(f"${p['price']}", weight=ft.FontWeight.BOLD, size=18, color=PRIMARY), 
                                        ft.Container(content=ft.Row([ft.Icon(ft.Icons.ADD_SHOPPING_CART, size=16, color=ft.Colors.WHITE), ft.Text("أضف للسلة", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor=PRIMARY, padding=10, border_radius=8, on_click=lambda e, prod=p: manage_cart(prod, "add"), ink=True)
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ])
                            )
                        )
                    )
            
            user_input.disabled = False
            analyze_btn.disabled = False
            analyze_btn.bgcolor = PRIMARY
            page.update()

        analyze_btn.on_click = analyze_input
        
        def create_chip(title, symptom_text):
            async def chip_click(e):
                user_input.value = symptom_text
                await analyze_input()

            return ft.Container(
                content=ft.Text(title, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK),
                bgcolor=BORDER_LIGHT,
                padding=10,
                border_radius=20,
                ink=True,
                on_click=chip_click
            )

        quick_chips = ft.Row(
            controls=[
                create_chip("أرق 😴", "أعاني من أرق وصعوبة شديدة في النوم"),
                create_chip("إرهاق 😩", "أحس بخمول وضعف عام وإرهاق"),
                create_chip("مفاصل 🦴", "ألم في المفاصل وطقطقة بالركبة"),
                create_chip("صداع 🤕", "أعاني من صداع شديد ومستمر")
            ], 
            scroll=ft.ScrollMode.AUTO
        )
        
        return ft.View(route="/ai", bgcolor=BG_LIGHT, controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=PRIMARY_DARK, on_click=go_back), title=ft.Text("المساعد الذكي", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK), actions=get_appbar_actions(), bgcolor=CARD_BG), 
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#e69b5c"), ft.Text("توصيات عامة وليست تشخيصاً طبياً.", color="#e69b5c", weight=ft.FontWeight.BOLD, expand=True)]), bgcolor="#fcf2e8", padding=10, border_radius=10), 
            ft.Text("تشخيص سريع:", color=TEXT_MUTED, size=14), 
            quick_chips, 
            ft.Container(height=5), 
            user_input, 
            analyze_btn, 
            ft.Divider(color=ft.Colors.TRANSPARENT), 
            results_list
        ], padding=20)

    # --- 5. السلة ---
    def build_cart_view():
        cart_list = ft.ListView(expand=True, spacing=10)
        total_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=PRIMARY)
        
        def update_cart_ui():
            cart_list.controls.clear()
            total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
            total_text.value = f"${total_price}"
            
            if not app_state['cart']:
                cart_list.controls.append(ft.Column([ft.Icon(ft.Icons.REMOVE_SHOPPING_CART, size=80, color=BORDER_LIGHT), ft.Text("سلتك فارغة حالياً.", size=18, color=TEXT_MUTED)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True))
            else:
                for item in app_state['cart']: 
                    prod = item['product']
                    qty = item['qty']
                    cart_list.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.SHOPPING_BAG, color=PRIMARY, size=30), 
                            title=ft.Text(prod['name'], weight=ft.FontWeight.BOLD, color=TEXT_DARK), 
                            subtitle=ft.Text(f"${prod['price']} × {qty} = ${prod['price'] * qty}", color=TEXT_MUTED), 
                            trailing=ft.Row([
                                ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=TEXT_MUTED, on_click=lambda e, p=prod: manage_cart(p, "decrease")),
                                ft.Text(str(qty), weight=ft.FontWeight.BOLD, size=16, color=PRIMARY_DARK),
                                ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=PRIMARY, on_click=lambda e, p=prod: manage_cart(p, "add")),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=DANGER, on_click=lambda e, p=prod: manage_cart(p, "remove"))
                            ], tight=True, spacing=0),
                            bgcolor=CARD_BG, shape=ft.RoundedRectangleBorder(radius=10)
                        )
                    )
            page.update()
        
        page.refresh_cart = update_cart_ui
        update_cart_ui()
            
        def proceed_to_checkout(e):
            if not app_state['cart']: return show_snack("سلتك فارغة!", DANGER)
            nav("/checkout")
            
        return ft.View(route="/cart", bgcolor=BG_LIGHT, controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=PRIMARY_DARK, on_click=go_back), title=ft.Text("سلة المشتريات", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD), bgcolor=CARD_BG), 
            cart_list, 
            ft.Divider(color=BORDER_LIGHT), 
            ft.Row([ft.Text("الإجمالي الكلي:", size=20, weight=ft.FontWeight.BOLD, color=TEXT_DARK), total_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
            ft.Container(height=10), 
            ft.Container(content=ft.Text("متابعة الدفع", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=18), bgcolor=PRIMARY, padding=15, border_radius=12, alignment=ft.Alignment(0.0, 0.0), on_click=proceed_to_checkout, ink=True)
        ], padding=20)

    # --- 6. الدفع ---
    def build_checkout_view():
        total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
        address_input = ft.TextField(label="عنوان التوصيل بالتفصيل", multiline=True, min_lines=2, border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        payment_method = ft.Dropdown(label="طريقة الدفع", options=[ft.dropdown.Option("الدفع عند الاستلام (كاش)"), ft.dropdown.Option("البطاقة الائتمانية")], value="الدفع عند الاستلام (كاش)", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        
        def confirm_order(e):
            safe_address = address_input.value or ""
            if not safe_address.strip(): return show_snack("اكتب عنوان التوصيل!", DANGER)
            order_id = db.create_order(app_state['user']['id'], app_state['cart'], total_price)
            app_state['cart'].clear() 
            nav("/home")
            show_snack(f"تم تأكيد الطلب بنجاح! رقم: #{order_id}", PRIMARY)
            
        return ft.View(route="/checkout", bgcolor=BG_LIGHT, controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=PRIMARY_DARK, on_click=go_back), title=ft.Text("إتمام الطلب", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD), bgcolor=CARD_BG), 
            ft.Text("ملخص الطلب", size=20, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK), 
            ft.Container(content=ft.Column([
                ft.Row([ft.Text("عدد المنتجات:", size=16, color=TEXT_MUTED), ft.Text(str(sum(item['qty'] for item in app_state['cart'])), size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                ft.Divider(color=BORDER_LIGHT),
                ft.Row([ft.Text("المبلغ المطلوب:", size=18, color=TEXT_DARK), ft.Text(f"${total_price}", size=20, weight=ft.FontWeight.BOLD, color=PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]), padding=20, bgcolor=CARD_BG, border_radius=15, border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT))), 
            ft.Container(height=10),
            address_input, 
            payment_method, 
            ft.Container(expand=True), 
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE), ft.Text("تأكيد الطلب نهائياً", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=18)], alignment=ft.MainAxisAlignment.CENTER), bgcolor=PRIMARY, padding=15, border_radius=12, on_click=confirm_order, ink=True)
        ], padding=20)

    # --- 7. الملف الشخصي ---
    def build_profile_view():
        orders_list = ft.ListView(expand=True, spacing=10)
        for o in db.conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (app_state['user']['id'],)).fetchall(): 
            orders_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.RECEIPT_LONG, color=PRIMARY), title=ft.Text(f"طلب: #{o['id']}", weight=ft.FontWeight.BOLD, color=TEXT_DARK), subtitle=ft.Text(f"الإجمالي: ${o['total_price']}", color=TEXT_MUTED), bgcolor=CARD_BG, shape=ft.RoundedRectangleBorder(radius=10)))
            
        def logout(e): app_state['user'] = None; app_state['cart'].clear(); nav("/home"); show_snack("تم تسجيل الخروج", PRIMARY)
        
        role_text = "المدير العام 🛡️" if app_state['user']['is_admin'] else "عميل 👤"
        
        profile_card = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=PRIMARY), 
                ft.Text(app_state['user']['name'], size=24, weight=ft.FontWeight.BOLD, color=TEXT_DARK), 
                ft.Text(role_text, color=PRIMARY_DARK if app_state['user']['is_admin'] else TEXT_MUTED, size=16),
                ft.Container(height=10),
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOGOUT, color=DANGER), ft.Text("تسجيل خروج", weight=ft.FontWeight.BOLD, color=DANGER)], alignment=ft.MainAxisAlignment.CENTER), bgcolor="#fce8e8", padding=10, border_radius=8, on_click=logout, ink=True, width=150)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, bgcolor=CARD_BG, border_radius=15, width=float('inf'), shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.with_opacity(0.05, TEXT_DARK))
        )
        
        return ft.View(route="/profile", bgcolor=BG_LIGHT, controls=[
            ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=PRIMARY_DARK, on_click=go_back), title=ft.Text("الملف الشخصي", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD), bgcolor=CARD_BG), 
            profile_card, 
            ft.Divider(height=20, color=BORDER_LIGHT), 
            ft.Text("سجل الطلبات:", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK), 
            orders_list
        ], padding=20)

    # --- 8. لوحة التحكم الشاملة ---
    def build_admin_view():
        stats = db.get_dashboard_stats()
        
        def build_stat_card(title, val, icon, color):
            return ft.Card(
                elevation=0, shape=ft.RoundedRectangleBorder(radius=15),
                content=ft.Container(
                    padding=20, bgcolor=CARD_BG, border_radius=15, border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT)),
                    content=ft.Column([
                        ft.Icon(icon, color=color, size=35),
                        ft.Text(title, size=14, color=TEXT_MUTED),
                        ft.Text(str(val), size=24, weight=ft.FontWeight.BOLD, color=TEXT_DARK)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
        
        stats_content = ft.Column([
            ft.Row([
                ft.Container(content=build_stat_card("الأرباح", f"${stats['revenue']}", ft.Icons.ATTACH_MONEY, PRIMARY), expand=True),
                ft.Container(content=build_stat_card("الطلبات", stats['orders_count'], ft.Icons.SHOPPING_BAG, "#e69b5c"), expand=True)
            ]),
            ft.Row([
                ft.Container(content=build_stat_card("المستخدمين", stats['users_count'], ft.Icons.PEOPLE, "#5c9be6"), expand=True),
                ft.Container(content=build_stat_card("المنتجات", stats['products_count'], ft.Icons.INVENTORY, "#9b5ce6"), expand=True)
            ])
        ], spacing=15, scroll=ft.ScrollMode.AUTO)
        
        p_name = ft.TextField(label="الاسم", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        p_desc = ft.TextField(label="الوصف", multiline=True, border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        p_price = ft.TextField(label="السعر ($)", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        p_qty = ft.TextField(label="الكمية", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        p_tags = ft.TextField(label="الكلمات المفتاحية", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        
        def save_product(e):
            if not p_name.value or not p_price.value or not p_qty.value: return show_snack("أكمل البيانات الأساسية", DANGER)
            db.add_product(p_name.value, p_desc.value, float(p_price.value), int(p_qty.value), p_tags.value)
            show_snack("تمت إضافة المنتج!", PRIMARY); nav("/admin")

        def del_product(pid): db.delete_product(pid); show_snack("تم حذف المنتج!", "#e69b5c"); nav("/admin")

        products_list = ft.ListView(expand=True, spacing=10)
        for p in db.get_all_products(): 
            products_list.controls.append(ft.ListTile(title=ft.Text(p['name'], weight=ft.FontWeight.BOLD, color=TEXT_DARK), subtitle=ft.Text(f"سعر: {p['price']}$ | متوفر: {p['quantity']}", color=TEXT_MUTED), trailing=ft.IconButton(ft.Icons.DELETE, icon_color=DANGER, on_click=lambda e, pid=p['id']: del_product(pid)), bgcolor=CARD_BG, shape=ft.RoundedRectangleBorder(radius=8), border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT))))

        products_content = ft.Column([
            ft.Text("إضافة منتج جديد:", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK, size=16), 
            p_name, ft.Row([ft.Container(content=p_price, expand=True), ft.Container(content=p_qty, expand=True)]), p_desc, p_tags, 
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.SAVE, color=ft.Colors.WHITE), ft.Text("حفظ المنتج", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER), bgcolor=PRIMARY, padding=12, border_radius=10, on_click=save_product, ink=True), 
            ft.Divider(height=20, color=BORDER_LIGHT), ft.Text("المنتجات الحالية:", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK, size=16), products_list
        ], expand=True)

        u_name = ft.TextField(label="اسم المستخدم", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        u_email = ft.TextField(label="البريد الإلكتروني", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        u_pass = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        u_role = ft.Dropdown(label="الصلاحية", options=[ft.dropdown.Option("عميل"), ft.dropdown.Option("مدير / موظف")], value="عميل", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)

        def save_new_user(e):
            if not u_name.value or not u_email.value or not u_pass.value: return show_snack("يرجى تعبئة جميع الحقول!", DANGER)
            is_adm = 1 if u_role.value == "مدير / موظف" else 0
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)", (u_name.value, u_email.value, u_pass.value, is_adm))
                db.conn.commit()
                show_snack("تمت إضافة المستخدم بنجاح!", PRIMARY); nav("/admin")
            except sqlite3.IntegrityError:
                show_snack("هذا البريد مسجل مسبقاً!", DANGER)

        users_list = ft.ListView(expand=True, spacing=10)
        def del_user(uid):
            db.conn.execute("DELETE FROM users WHERE id=?", (uid,)); db.conn.commit()
            show_snack("تم حذف المستخدم!", DANGER); nav("/admin")
            
        all_sys_users = db.conn.execute("SELECT * FROM users WHERE id != ? ORDER BY id DESC", (app_state['user']['id'],)).fetchall()
        if not all_sys_users:
            users_list.controls.append(ft.Text("لا يوجد مستخدمين آخرين.", color=TEXT_MUTED))
        else:
            for u in all_sys_users:
                r_text = "مدير/موظف 🛡️" if u['is_admin'] == 1 else "عميل 👤"
                r_color = PRIMARY if u['is_admin'] == 1 else TEXT_MUTED
                users_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.PERSON, color=PRIMARY), title=ft.Row([ft.Text(u['name'], weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Text(r_text, color=r_color, size=11)]), subtitle=ft.Text(u['email'], size=12, color=TEXT_MUTED), trailing=ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=DANGER, on_click=lambda e, uid=u['id']: del_user(uid)), bgcolor=CARD_BG, shape=ft.RoundedRectangleBorder(radius=8), border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT))))

        users_content = ft.Column([
            ft.Text("إضافة مستخدم جديد:", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK, size=16),
            u_name, u_email, u_pass, u_role,
            ft.Container(content=ft.Row([ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.WHITE), ft.Text("إضافة المستخدم", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER), bgcolor=PRIMARY, padding=12, border_radius=10, on_click=save_new_user, ink=True),
            ft.Divider(height=20, color=BORDER_LIGHT), ft.Text("إدارة المستخدمين المسجلين:", weight=ft.FontWeight.BOLD, color=PRIMARY_DARK, size=16), users_list
        ], expand=True)

        orders_list = ft.ListView(expand=True, spacing=10)
        all_orders = db.get_all_orders()
        if not all_orders:
            orders_list.controls.append(ft.Text("لا توجد طلبات مسجلة حتى الآن.", color=TEXT_MUTED))
        else:
            for o in all_orders: 
                orders_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.LOCAL_SHIPPING, color=PRIMARY), title=ft.Text(f"طلب #{o['id']} - عميل #{o['user_id']}", weight=ft.FontWeight.BOLD, color=TEXT_DARK), subtitle=ft.Text(f"المبلغ: {o['total_price']}$ - التاريخ: {o['created_at'].split(' ')[0]}", color=TEXT_MUTED), bgcolor=CARD_BG, shape=ft.RoundedRectangleBorder(radius=8), border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT))))
        orders_content = ft.Column([ft.Text("سجل الطلبات الشامل", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY_DARK), ft.Divider(color=BORDER_LIGHT), orders_list], expand=True)

        gemini_switch = ft.Switch(label="تفعيل محرك Gemini السحابي 🌐", value=(db.get_setting("gemini_enabled") == "1"), active_color=PRIMARY)
        gemini_key_input = ft.TextField(label="مفتاح API (Gemini Key)", value=db.get_setting("gemini_api_key"), password=True, can_reveal_password=True, border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, color=TEXT_DARK)
        
        def save_ai_settings(e):
            db.set_setting("gemini_enabled", "1" if gemini_switch.value else "0")
            db.set_setting("gemini_api_key", gemini_key_input.value)
            show_snack("تم حفظ إعدادات الذكاء الاصطناعي بنجاح!", PRIMARY)

        ai_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.CLOUD_DONE, color=PRIMARY), ft.Text("إعدادات الذكاء السحابي", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD, size=18)]), 
            ft.Container(content=ft.Column([
                ft.Text("ربط التطبيق مع سيرفرات جوجل (Gemini) لفهم وتبرير طبي فائق الدقة. يتطلب إنترنت.", color=TEXT_MUTED, size=12),
                gemini_switch, gemini_key_input,
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.SAVE, color=ft.Colors.WHITE), ft.Text("حفظ إعدادات الربط", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER), bgcolor=PRIMARY, padding=12, border_radius=10, on_click=save_ai_settings, ink=True)
            ]), padding=15, bgcolor=CARD_BG, border_radius=12, border=ft.Border(top=ft.BorderSide(1, BORDER_LIGHT), left=ft.BorderSide(1, BORDER_LIGHT), right=ft.BorderSide(1, BORDER_LIGHT), bottom=ft.BorderSide(1, BORDER_LIGHT))),
            
            ft.Divider(height=20, color=BORDER_LIGHT),
            ft.Row([ft.Icon(ft.Icons.OFFLINE_BOLT, color=PRIMARY), ft.Text("المحرك المحلي (Offline)", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD, size=18)]), 
            ft.Text("هذا المحرك يعمل تلقائياً في حال فشل الاتصال بالإنترنت أو إيقاف Gemini أعلاه.", color=TEXT_MUTED, size=12),
            ft.TextField(multiline=True, min_lines=6, max_lines=8, value=json.dumps(HealthAI.SYNONYMS_MAP, ensure_ascii=False, indent=2), label="خريطة المفاهيم (JSON)", border_radius=10, border_color=BORDER_LIGHT, bgcolor=CARD_BG, read_only=True, color=TEXT_DARK), 
        ], expand=True, scroll=ft.ScrollMode.AUTO)

        content_area = ft.Container(content=stats_content, expand=True, padding=10)
        tab_btns = []

        def change_tab(index, content_ctrl):
            content_area.content = content_ctrl
            for i, btn in enumerate(tab_btns):
                btn.style = ft.ButtonStyle(color=PRIMARY if i == index else TEXT_MUTED)
            page.update()

        def create_tab_btn(title, icon, index, content_ctrl):
            return ft.TextButton(content=ft.Row([ft.Icon(icon), ft.Text(title, weight=ft.FontWeight.BOLD)]), style=ft.ButtonStyle(color=PRIMARY if index == 0 else TEXT_MUTED), on_click=lambda e, i=index, c=content_ctrl: change_tab(i, c))

        tab_btns.extend([
            create_tab_btn("الإحصائيات", ft.Icons.DASHBOARD, 0, stats_content),
            create_tab_btn("المنتجات", ft.Icons.INVENTORY, 1, products_content),
            create_tab_btn("المستخدمين", ft.Icons.PEOPLE, 2, users_content),
            create_tab_btn("الطلبات", ft.Icons.RECEIPT, 3, orders_content),
            create_tab_btn("الذكاء", ft.Icons.SMART_TOY, 4, ai_content),
        ])

        custom_tabs_layout = ft.Column([ft.Row(controls=tab_btns, scroll=ft.ScrollMode.AUTO, spacing=15), ft.Divider(height=1, color=BORDER_LIGHT), content_area], expand=True)
        return ft.View(route="/admin", bgcolor=BG_LIGHT, controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=PRIMARY_DARK, on_click=go_back), title=ft.Text("الإدارة الشاملة", color=PRIMARY_DARK, weight=ft.FontWeight.BOLD), bgcolor=CARD_BG), custom_tabs_layout], padding=10)

    # ==========================================
    # 6. نظام التوجيه والمسارات (Routing System)
    # ==========================================
    def route_change(route):
        page.views.clear()
        
        public_routes = ["/home", "/ai", "/login", "/register"]
        if page.route not in public_routes and not app_state['user']:
            show_snack("يجب تسجيل الدخول للوصول إلى هذه الصفحة", DANGER)
            nav("/login")
            return
            
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
    
    nav("/home")

if __name__ == "__main__":
    ft.run(main)
