import flet as ft
import sqlite3
import json
from database import Database
from ai_engine import HealthAI

def main(page: ft.Page):
    # ==========================================
    # 1. إعدادات النافذة والتصميم
    # ==========================================
    page.title = "متجر المنتجات الصحية الذكي"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
    
    page.window.width = 450
    page.window.height = 850
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
            duration=3000
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

    # ==========================================
    # 4. بناء الواجهات (Views Builders)
    # ==========================================
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

    # --- 1. شاشة الدخول ---
    def build_login_view():
        email_input = ft.TextField(label="البريد الإلكتروني", width=320, border_radius=12, prefix_icon=ft.Icons.EMAIL)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, width=320, border_radius=12, prefix_icon=ft.Icons.LOCK)
        def do_login(e):
            if not email_input.value or not pass_input.value: return show_snack("أدخل البريد وكلمة المرور!", ft.Colors.RED_500)
            user = db.authenticate_user(email_input.value, pass_input.value)
            if user:
                app_state['user'] = dict(user)
                role = "المدير" if user['is_admin'] else "العميل"
                show_snack(f"أهلاً بك يا {role} {user['name']} 👋", ft.Colors.GREEN_600)
                nav("/home")
            else: show_snack("البيانات غير صحيحة!", ft.Colors.RED_500)
        return ft.View(route="/login", controls=[ft.Container(content=ft.Column(controls=[ft.Icon(ft.Icons.HEALTH_AND_SAFETY, size=90, color=ft.Colors.TEAL), ft.Text("المتجر الذكي", size=24, weight=ft.FontWeight.BOLD), ft.Container(height=15), email_input, pass_input, ft.Container(height=10), ft.Button(content=ft.Text("تسجيل الدخول"), on_click=do_login, width=320, height=50, style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE)), ft.TextButton("ليس لديك حساب؟ سجل الآن", on_click=lambda e: nav("/register"))], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER), expand=True)])

    # --- 2. شاشة التسجيل العامة (للعملاء فقط) ---
    def build_register_view():
        name_input = ft.TextField(label="الاسم الكامل", width=320, border_radius=12, prefix_icon=ft.Icons.PERSON)
        email_input = ft.TextField(label="البريد الإلكتروني", width=320, border_radius=12, prefix_icon=ft.Icons.EMAIL)
        pass_input = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, width=320, border_radius=12, prefix_icon=ft.Icons.LOCK)
        pass_confirm = ft.TextField(label="تأكيد كلمة المرور", password=True, can_reveal_password=True, width=320, border_radius=12, prefix_icon=ft.Icons.LOCK_OUTLINE)
        def do_register(e):
            if not name_input.value or not email_input.value or not pass_input.value or not pass_confirm.value: return show_snack("أكمل الحقول!", ft.Colors.RED_500)
            if pass_input.value != pass_confirm.value: return show_snack("كلمات المرور غير متطابقة!", ft.Colors.RED_500)
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)", (name_input.value, email_input.value, pass_input.value)); db.conn.commit()
                show_snack("تم إنشاء حساب العميل بنجاح!", ft.Colors.GREEN_600); nav("/login")
            except sqlite3.IntegrityError: show_snack("هذا البريد مسجل مسبقاً!", ft.Colors.RED_500)
        return ft.View(route="/register", controls=[ft.Container(content=ft.Column(controls=[ft.Icon(ft.Icons.PERSON_ADD_ALT_1, size=80, color=ft.Colors.TEAL), ft.Text("إنشاء حساب عميل", size=24, weight=ft.FontWeight.BOLD), name_input, email_input, pass_input, pass_confirm, ft.Button(content=ft.Text("إنشاء الحساب"), on_click=do_register, width=320, height=50, style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE)), ft.TextButton("تسجيل دخول", on_click=lambda e: nav("/login"))], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER), expand=True)])

    # --- 3. المتجر ---
    def build_home_view():
        products_list = ft.ListView(expand=True, spacing=15, padding=20)
        for p in db.get_all_products():
            prod = dict(p)
            if prod['quantity'] > 0:
                products_list.controls.append(ft.Card(elevation=8, shape=ft.RoundedRectangleBorder(radius=15), content=ft.Container(padding=20, content=ft.Column([ft.Row([ft.Icon(ft.Icons.MEDICATION_LIQUID, color=ft.Colors.TEAL), ft.Text(prod['name'], size=18, weight=ft.FontWeight.BOLD, expand=True), ft.Text(f"${prod['price']}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)]), ft.Text(prod['description'], size=14, color=ft.Colors.GREY_300), ft.Row([ft.Text(f"المتوفر: {prod['quantity']}", size=12, color=ft.Colors.GREY_500), ft.Button(content=ft.Text("أضف للسلة"), icon=ft.Icons.ADD_SHOPPING_CART, on_click=lambda e, p=prod: add_to_cart(p), bgcolor=ft.Colors.TEAL_700, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]))))
        return ft.View(route="/home", controls=[ft.AppBar(title=ft.Text("المنتجات"), actions=get_appbar_actions(), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, automatically_imply_leading=False), products_list, ft.FloatingActionButton(icon=ft.Icons.PSYCHOLOGY, content=ft.Text("المساعد الذكي", weight=ft.FontWeight.BOLD), on_click=lambda e: nav("/ai"), bgcolor=ft.Colors.TEAL, width=200)])

    # --- 4. الذكاء الاصطناعي ---
    def build_ai_view():
        user_input = ft.TextField(label="كيف تشعر اليوم؟", multiline=True, min_lines=3, max_lines=4, border_radius=12, border_color=ft.Colors.TEAL)
        results_list = ft.ListView(expand=True, spacing=15)
        def analyze_input(e=None):
            safe_val = user_input.value or ""
            if not safe_val.strip(): return show_snack("يرجى كتابة وصف لحالتك أولاً!", ft.Colors.RED_500)
            results_list.controls.clear()
            suggestions = HealthAI.suggest_products(safe_val, db.get_all_products())
            if not suggestions: results_list.controls.append(ft.Text("لم نجد منتجات تطابق وصفك.", color=ft.Colors.ORANGE_400, text_align=ft.TextAlign.CENTER))
            else:
                for item in suggestions:
                    p = item['product']
                    results_list.controls.append(ft.Card(elevation=5, shape=ft.RoundedRectangleBorder(radius=15), content=ft.Container(padding=15, border=ft.Border(top=ft.BorderSide(1, ft.Colors.TEAL_800), right=ft.BorderSide(1, ft.Colors.TEAL_800), bottom=ft.BorderSide(1, ft.Colors.TEAL_800), left=ft.BorderSide(1, ft.Colors.TEAL_800)), border_radius=15, content=ft.Column([ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME, color=ft.Colors.AMBER), ft.Text(p['name'], size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200)]), ft.Text(item['explanation'], color=ft.Colors.GREY_300, italic=True), ft.Divider(height=10), ft.Row([ft.Text(f"${p['price']}", weight=ft.FontWeight.BOLD), ft.Button(content=ft.Text("أضف للسلة"), on_click=lambda e, prod=p: add_to_cart(prod), bgcolor=ft.Colors.TEAL_700, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]))))
            page.update()
        def set_quick_symptom(text): user_input.value = text; analyze_input()
        quick_chips = ft.Row(controls=[ft.Button(content=ft.Text("أرق"), on_click=lambda e: set_quick_symptom("أعاني من أرق وصعوبة شديدة في النوم"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20))), ft.Button(content=ft.Text("إرهاق"), on_click=lambda e: set_quick_symptom("أحس بخمول وضعف عام وإرهاق"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20))), ft.Button(content=ft.Text("مفاصل"), on_click=lambda e: set_quick_symptom("ألم في المفاصل وطقطقة بالركبة"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)))], scroll=ft.ScrollMode.AUTO)
        return ft.View(route="/ai", controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("المساعد الذكي"), actions=get_appbar_actions(), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.Container(content=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_400), ft.Text("توصيات عامة وليست تشخيصاً طبياً.", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD, expand=True)]), bgcolor=ft.Colors.RED_900, padding=10, border_radius=10), ft.Text("تشخيص سريع:", color=ft.Colors.GREY_400, size=12), quick_chips, ft.Container(height=5), user_input, ft.Button(content=ft.Text("تحليل الحالة"), icon=ft.Icons.SEARCH, on_click=analyze_input, height=45, width=float('inf'), bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE), ft.Divider(color=ft.Colors.TRANSPARENT), results_list], padding=20)

    # --- 5. السلة ---
    def build_cart_view():
        cart_list = ft.ListView(expand=True, spacing=10)
        total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
        for item in app_state['cart']: cart_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.SHOPPING_BAG, color=ft.Colors.TEAL), title=ft.Text(item['product']['name']), subtitle=ft.Text(f"الكمية: {item['qty']} | الإجمالي: ${item['product']['price'] * item['qty']}"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, shape=ft.RoundedRectangleBorder(radius=10)))
        def proceed_to_checkout(e):
            if not app_state['cart']: return show_snack("سلتك فارغة!", ft.Colors.RED_500)
            nav("/checkout")
        return ft.View(route="/cart", controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("سلة المشتريات"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), cart_list if app_state['cart'] else ft.Text("سلتك فارغة حالياً.", size=18, text_align=ft.TextAlign.CENTER), ft.Divider(), ft.Row([ft.Text("الإجمالي الكلي:", size=20, weight=ft.FontWeight.BOLD), ft.Text(f"${total_price}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=10), ft.Button(content=ft.Text("متابعة الدفع", size=16, weight=ft.FontWeight.BOLD), on_click=proceed_to_checkout, bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE, height=50, width=float('inf'))], padding=20)

    # --- 6. الدفع ---
    def build_checkout_view():
        total_price = sum(item['product']['price'] * item['qty'] for item in app_state['cart'])
        address_input = ft.TextField(label="عنوان التوصيل بالتفصيل", multiline=True, border_radius=10)
        payment_method = ft.Dropdown(label="طريقة الدفع", options=[ft.dropdown.Option("الدفع عند الاستلام (كاش)"), ft.dropdown.Option("البطاقة الائتمانية")], value="الدفع عند الاستلام (كاش)", border_radius=10)
        def confirm_order(e):
            safe_address = address_input.value or ""
            if not safe_address.strip(): return show_snack("اكتب عنوان التوصيل!", ft.Colors.RED_500)
            order_id = db.create_order(app_state['user']['id'], app_state['cart'], total_price)
            app_state['cart'].clear() 
            nav("/home")
            show_snack(f"تم تأكيد الطلب بنجاح! رقم: #{order_id}", ft.Colors.GREEN_600)
        return ft.View(route="/checkout", controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("الدفع"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.Text("ملخص الطلب", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200), ft.Container(content=ft.Column([ft.Row([ft.Text("عدد المنتجات:"), ft.Text(str(sum(item['qty'] for item in app_state['cart'])))]), ft.Row([ft.Text("المبلغ المطلوب:"), ft.Text(f"${total_price}", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)])]), padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=10), ft.Divider(height=20), address_input, payment_method, ft.Container(height=20, expand=True), ft.Button(content=ft.Text("تأكيد الطلب نهائياً"), icon=ft.Icons.CHECK_CIRCLE, on_click=confirm_order, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, height=55, width=float('inf'))], padding=20)

    # --- 7. الملف الشخصي ---
    def build_profile_view():
        orders_list = ft.ListView(expand=True, spacing=10)
        for o in db.conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (app_state['user']['id'],)).fetchall(): orders_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.TEAL), title=ft.Text(f"طلب: #{o['id']}", weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"الإجمالي: ${o['total_price']}"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST))
        def logout(e): app_state['user'] = None; app_state['cart'].clear(); nav("/login"); show_snack("تم تسجيل الخروج", ft.Colors.GREEN_600)
        
        role_text = "المدير العام 🛡️" if app_state['user']['is_admin'] else "عميل 👤"
        return ft.View(route="/profile", controls=[ft.AppBar(leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back), title=ft.Text("الملف الشخصي"), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST), ft.Card(elevation=5, content=ft.Container(padding=20, content=ft.Column([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=70, color=ft.Colors.TEAL), ft.Text(app_state['user']['name'], size=22, weight=ft.FontWeight.BOLD), ft.Text(role_text, color=ft.Colors.AMBER if app_state['user']['is_admin'] else ft.Colors.GREY), ft.Button(content=ft.Text("تسجيل خروج"), icon=ft.Icons.LOGOUT, on_click=logout, bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE)], horizontal_alignment=ft.CrossAxisAlignment.CENTER))), ft.Divider(), ft.Text("سجل الطلبات:"), orders_list], padding=20)

    # --- 8. لوحة التحكم الشاملة (الآدمن) ---
    def build_admin_view():
        stats = db.get_dashboard_stats()
        
        stats_content = ft.Column([ft.Row([ft.Icon(ft.Icons.MONEY), ft.Text(f"المبيعات: ${stats['revenue']}", size=18)]), ft.Row([ft.Icon(ft.Icons.SHOPPING_BAG), ft.Text(f"الطلبات: {stats['orders_count']}", size=18)]), ft.Row([ft.Icon(ft.Icons.PEOPLE), ft.Text(f"المستخدمين: {stats['users_count']}", size=18)]), ft.Row([ft.Icon(ft.Icons.INVENTORY), ft.Text(f"المنتجات: {stats['products_count']}", size=18)])], spacing=20)
        
        p_name = ft.TextField(label="الاسم", width=150)
        p_desc = ft.TextField(label="الوصف", width=200)
        p_price = ft.TextField(label="السعر", width=80)
        p_qty = ft.TextField(label="الكمية", width=80)
        p_tags = ft.TextField(label="الكلمات المفتاحية", width=250)
        
        def save_product(e):
            db.add_product(p_name.value, p_desc.value, float(p_price.value), int(p_qty.value), p_tags.value)
            show_snack("تمت إضافة المنتج!", ft.Colors.GREEN_600); nav("/admin")

        def del_product(pid): db.delete_product(pid); show_snack("تم حذف المنتج!", ft.Colors.ORANGE); nav("/admin")

        products_list = ft.ListView(expand=True, spacing=5)
        for p in db.get_all_products(): products_list.controls.append(ft.ListTile(title=ft.Text(p['name']), subtitle=ft.Text(f"سعر: {p['price']}$ | متوفر: {p['quantity']}"), trailing=ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=lambda e, pid=p['id']: del_product(pid))))

        products_content = ft.Column([ft.Text("إضافة منتج جديد:", weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200), ft.Row([p_name, p_price, p_qty], scroll=ft.ScrollMode.AUTO), p_desc, p_tags, ft.Button(content=ft.Text("حفظ المنتج"), on_click=save_product, bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE), ft.Divider(), ft.Text("المنتجات الحالية:"), products_list], expand=True)

        # 🌟 إدارة المستخدمين (إضافة موظف/مدير أو عميل) 🌟
        u_name = ft.TextField(label="اسم المستخدم", width=150)
        u_email = ft.TextField(label="البريد الإلكتروني", width=200)
        u_pass = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, width=150)
        u_role = ft.Dropdown(label="الصلاحية", options=[ft.dropdown.Option("عميل"), ft.dropdown.Option("مدير / موظف")], value="عميل", width=150)

        def save_new_user(e):
            if not u_name.value or not u_email.value or not u_pass.value:
                return show_snack("يرجى تعبئة جميع الحقول!", ft.Colors.RED)
            
            is_adm = 1 if u_role.value == "مدير / موظف" else 0
            try:
                db.conn.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)", (u_name.value, u_email.value, u_pass.value, is_adm))
                db.conn.commit()
                show_snack("تمت إضافة المستخدم بنجاح!", ft.Colors.GREEN_600)
                nav("/admin")
            except sqlite3.IntegrityError:
                show_snack("هذا البريد مسجل مسبقاً!", ft.Colors.RED)

        users_list = ft.ListView(expand=True, spacing=5)
        def del_user(uid):
            db.conn.execute("DELETE FROM users WHERE id=?", (uid,))
            db.conn.commit()
            show_snack("تم حذف المستخدم!", ft.Colors.RED); nav("/admin")
            
        current_admin_id = app_state['user']['id']
        all_sys_users = db.conn.execute("SELECT * FROM users WHERE id != ? ORDER BY id DESC", (current_admin_id,)).fetchall()
        
        if not all_sys_users:
            users_list.controls.append(ft.Text("لا يوجد مستخدمين آخرين في النظام.", color=ft.Colors.GREY_500))
        else:
            for u in all_sys_users:
                r_text = "مدير/موظف 🛡️" if u['is_admin'] == 1 else "عميل 👤"
                r_color = ft.Colors.AMBER if u['is_admin'] == 1 else ft.Colors.GREY_400
                users_list.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.PERSON), title=ft.Row([ft.Text(u['name']), ft.Text(r_text, color=r_color, size=12)]), subtitle=ft.Text(u['email']), trailing=ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED, on_click=lambda e, uid=u['id']: del_user(uid))))

        users_content = ft.Column([
            ft.Text("إضافة مستخدم جديد (موظف أو عميل):", weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200),
            ft.Row([u_name, u_email, u_pass, u_role], scroll=ft.ScrollMode.AUTO),
            ft.Button(content=ft.Text("إضافة المستخدم"), on_click=save_new_user, bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE),
            ft.Divider(),
            ft.Text("إدارة المستخدمين المسجلين:"), users_list
        ], expand=True)

        # إدارة الطلبات
        orders_list = ft.ListView(expand=True)
        all_orders = db.get_all_orders()
        if not all_orders:
            orders_list.controls.append(ft.Text("لا توجد طلبات مسجلة حتى الآن.", color=ft.Colors.GREY_500))
        else:
            for o in all_orders: orders_list.controls.append(ft.ListTile(title=ft.Text(f"طلب #{o['id']} - عميل #{o['user_id']}"), subtitle=ft.Text(f"المبلغ: {o['total_price']}$ - التاريخ: {o['created_at']}")))
        orders_content = ft.Column([ft.Text("سجل الطلبات الشامل", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_200), ft.Divider(), orders_list], expand=True)

        # الذكاء الاصطناعي
        ai_content = ft.Column([ft.Text("محرك الذكاء الاصطناعي (مفعل 🟢)", color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD), ft.TextField(multiline=True, min_lines=8, value=json.dumps(HealthAI.SYNONYMS_MAP, ensure_ascii=False, indent=2), label="خريطة المفاهيم (JSON)"), ft.Button(content=ft.Text("تحديث خوارزمية AI"), bgcolor=ft.Colors.TEAL, color=ft.Colors.WHITE, on_click=lambda e: show_snack("تم التحديث!", ft.Colors.GREEN_600))], expand=True)

        content_area = ft.Container(content=stats_content, expand=True, padding=10)
        tab_btns = []

        def change_tab(index, content_ctrl):
            content_area.content = content_ctrl
            for i, btn in enumerate(tab_btns):
                btn.style = ft.ButtonStyle(color=ft.Colors.TEAL_400 if i == index else ft.Colors.GREY_500)
            page.update()

        def create_tab_btn(title, icon, index, content_ctrl):
            return ft.TextButton(content=ft.Row([ft.Icon(icon), ft.Text(title, weight=ft.FontWeight.BOLD)]), style=ft.ButtonStyle(color=ft.Colors.TEAL_400 if index == 0 else ft.Colors.GREY_500), on_click=lambda e, i=index, c=content_ctrl: change_tab(i, c))

        tab_btns.extend([
            create_tab_btn("الإحصائيات", ft.Icons.DASHBOARD, 0, stats_content),
            create_tab_btn("المنتجات", ft.Icons.INVENTORY, 1, products_content),
            create_tab_btn("المستخدمين", ft.Icons.PEOPLE, 2, users_content),
            create_tab_btn("الطلبات", ft.Icons.RECEIPT, 3, orders_content),
            create_tab_btn("الذكاء", ft.Icons.SMART_TOY, 4, ai_content),
        ])

        custom_tabs_layout = ft.Column([ft.Row(controls=tab_btns, scroll=ft.ScrollMode.AUTO), ft.Divider(height=1, color=ft.Colors.GREY_800), content_area], expand=True)
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