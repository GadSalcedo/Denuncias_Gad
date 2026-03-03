# web/migrations/0006_seed_menus.py
from django.db import migrations


def seed_data(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Menus = apps.get_model("web", "Menus")

    # =========================
    # 1) Grupos
    # =========================
    g_admin, _ = Group.objects.get_or_create(name="TICS_ADMIN")
    g_func, _ = Group.objects.get_or_create(name="FUNCIONARIO")

    # =========================
    # Helper: crear/actualizar menú sin ID manual
    # Lookup estable por (nombre, padre)
    # =========================
    def upsert_menu(nombre, url, icono, orden, padre):
        obj, _ = Menus.objects.update_or_create(
            nombre=nombre,
            padre=padre,
            defaults={
                "url": url or "",
                "icono": icono or "",
                "orden": orden or 0,
            },
        )
        return obj

    # =========================
    # 2) Menús raíz
    # =========================
    # (nombre, url, icono, orden, padre_key)
    menus_data = [
        ("Denuncias", None, "mdi mdi-clipboard-text", 1, None),
        ("Catalogos", None, "mdi mdi-apps", 2, None),
        ("FAQ", None, "mdi mdi-help-circle", 3, None),
        ("Funcionarios", None, "mdi mdi-account-group", 4, None),
        ("Administracion", None, "mdi mdi-shield-key", 98, None),
        ("Página Web", "web:public_home", "mdi mdi-application", 99, None),
    ]

    menu_objs = {}  # key: nombre del menú raíz

    for nombre, url, icono, orden, _padre_key in menus_data:
        obj = upsert_menu(nombre=nombre, url=url, icono=icono, orden=orden, padre=None)
        menu_objs[nombre] = obj

    # =========================
    # 3) Submenús
    # =========================
    # (nombre, url, icono, orden, padre_nombre)
    submenus_data = [
        ("Listado", "web:denuncia_list", None, 1, "Denuncias"),
        ("Mis denuncias", "web:mis_denuncias", None, 2, "Denuncias"),

        ("Departamentos", "web:departamento_list", "bi bi-building", 1, "Catalogos"),
        ("Tipos de denuncia", "web:tipos_denuncia_list", "bi bi-tags", 2, "Catalogos"),
        ("Tipo <-> Departamento", "web:tipo_denuncia_departamento_list", "bi bi-diagram-3", 3, "Catalogos"),

        ("Preguntas frecuentes", "web:faq_list", None, 1, "FAQ"),

        ("Listado", "web:unified_user_list", None, 1, "Funcionarios"),

        ("Grupos", "web:grupo_list", "bi bi-people", 2, "Administracion"),
    ]

    for nombre, url, icono, orden, padre_nombre in submenus_data:
        padre = menu_objs.get(padre_nombre)
        upsert_menu(nombre=nombre, url=url, icono=icono, orden=orden, padre=padre)

    # =========================
    # 4) Permisos (ManyToMany)
    # =========================
    # Admin ve todo MENOS "Mis denuncias"
    for menu in Menus.objects.all():
        menu.permisos.add(g_admin)

    # Quitar "Mis denuncias" al admin
    mis_denuncias_menu = Menus.objects.filter(
        nombre="Mis denuncias",
        padre=menu_objs["Denuncias"]
    ).first()

    if mis_denuncias_menu:
        mis_denuncias_menu.permisos.remove(g_admin)

    # Funcionario ve algunos por NOMBRE
    funcionario_allow = {"Denuncias", "Listado", "Mis denuncias", "Página Web"}

    for menu in Menus.objects.filter(nombre__in=funcionario_allow):
        menu.permisos.add(g_func)


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0005_alter_menus_options_alter_menus_icono_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_data, migrations.RunPython.noop),
    ]