# web/utils/menus.py
from web.models import Menus


def build_menus_for_user(user):
    if not user.is_authenticated:
        return []

    # nombres de grupos reales del usuario
    group_names = list(user.groups.values_list("name", flat=True))

    # si es superuser, lo tratamos como TICS_ADMIN
    # pero NO como "ve todo"
    if user.is_superuser and "TICS_ADMIN" not in group_names:
        group_names.append("TICS_ADMIN")

    if not group_names:
        return []

    menus = (
        Menus.objects.filter(permisos__name__in=group_names)
        .distinct()
        .select_related("padre")
        .prefetch_related("permisos")
        .order_by("orden", "nombre")
    )

    padres = [m for m in menus if m.padre_id is None]
    hijos = [m for m in menus if m.padre_id is not None]

    hijos_por_padre = {}
    for h in hijos:
        hijos_por_padre.setdefault(h.padre_id, []).append(h)

    for p in padres:
        p.children = sorted(hijos_por_padre.get(p.id, []), key=lambda x: x.orden)

    return sorted(padres, key=lambda x: x.orden)