"""
Structura.AI Bridge — Blender 3.x / 4.x Official Addon
Ponte direta entre modelagem arquitetônica no Blender e verificação física no Structura.AI.
"""
bl_info = {
    "name": "Structura.AI Bridge",
    "author": "Lucas Cristiano Soares Lino (Structura.AI)",
    "version": (2, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Structura.AI",
    "description": "Verificação física determinística (NBR 6118) e motor de 5 redesigns estruturais em tempo real.",
    "category": "Architecture",
}

import bpy
import json
import urllib.request
import urllib.error
import webbrowser


class StructuraSettings(bpy.types.PropertyGroup):
    api_url: bpy.props.StringProperty(
        name="API URL",
        description="Endereço do servidor Structura.AI",
        default="http://localhost:8000",
    )
    project_name: bpy.props.StringProperty(
        name="Projeto",
        description="Nome identificador do projeto",
        default="Residência — Estudo Conceitual",
    )
    beam_width_cm: bpy.props.FloatProperty(
        name="Largura Viga (cm)",
        description="Largura da seção de concreto",
        default=20.0,
        min=12.0,
        max=100.0,
    )
    beam_height_cm: bpy.props.FloatProperty(
        name="Altura Viga (cm)",
        description="Altura da seção de concreto",
        default=30.0,
        min=15.0,
        max=300.0,
    )
    fck_mpa: bpy.props.FloatProperty(
        name="fck (MPa)",
        description="Resistência característica do concreto",
        default=30.0,
        min=20.0,
        max=90.0,
    )
    # Resultados cacheados
    last_status: bpy.props.StringProperty(name="Status", default="Aguardando Análise")
    last_deflection_mm: bpy.props.FloatProperty(name="Flecha (mm)", default=0.0)
    last_limit_mm: bpy.props.FloatProperty(name="Limite NBR (mm)", default=0.0)
    last_is_feasible: bpy.props.BoolProperty(name="Viável", default=True)
    last_project_url: bpy.props.StringProperty(name="URL Laudo", default="")


class STRUCTURA_OT_analyze(bpy.types.Operator):
    """Envia o modelo ativo ou seleção para cálculo estrutural no Structura.AI"""
    bl_idname = "structura.analyze"
    bl_label = "🚀 Analisar no Structura.AI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.structura_settings
        active_obj = context.active_object

        if not active_obj:
            self.report({"WARNING"}, "Selecione ao menos um objeto estrutural no Blender.")
            return {"CANCELLED"}

        # Calcular bounding box e vão estimado
        dim = active_obj.dimensions
        span_m = max(float(dim.x), float(dim.y))
        if span_m < 0.5:
            span_m = 6.0  # Vão padrão se escala for unitária

        payload = {
            "project_name": settings.project_name or active_obj.name,
            "source_software": "Blender 3D",
            "span_meters": round(span_m, 2),
            "beam_width_cm": settings.beam_width_cm,
            "beam_height_cm": settings.beam_height_cm,
            "fck_mpa": settings.fck_mpa,
            "cantilever_meters": 0.0,
            "dead_load_kn_m": 22.0,
            "live_load_kn_m": 3.0,
            "geometry_metadata": {
                "blender_object": active_obj.name,
                "dim_x": float(dim.x),
                "dim_y": float(dim.y),
                "dim_z": float(dim.z),
            }
        }

        endpoint = f"{settings.api_url.rstrip('/')}/api/plugins/sync"
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data_bytes,
                headers={"Content-Type": "application/json", "User-Agent": "Blender-StructuraAI-Plugin/2.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            diag = result.get("deterministic_diagnosis", {})
            settings.last_is_feasible = diag.get("is_feasible", True)
            settings.last_deflection_mm = diag.get("calculated_deflection_mm", 0.0)
            settings.last_limit_mm = diag.get("normative_limit_mm", 0.0)
            settings.last_project_url = result.get("studio_url", f"{settings.api_url}/analyzer")
            settings.last_status = "APROVADO (NBR 6118)" if settings.last_is_feasible else "REPROVADO (Flecha Excessiva)"

            msg_type = "INFO" if settings.last_is_feasible else "WARNING"
            self.report({msg_type}, f"Structura.AI: {settings.last_status} (Flecha: {settings.last_deflection_mm}mm)")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Erro ao conectar com Structura.AI ({endpoint}): {e}")
            return {"CANCELLED"}


class STRUCTURA_OT_open_studio(bpy.types.Operator):
    """Abre o laudo e as 5 propostas de redesign no navegador"""
    bl_idname = "structura.open_studio"
    bl_label = "🌐 Abrir 5 Redesigns no Browser"

    def execute(self, context):
        settings = context.scene.structura_settings
        url = settings.last_project_url or f"{settings.api_url}/analyzer"
        webbrowser.open(url)
        return {"FINISHED"}


class STRUCTURA_PT_main_panel(bpy.types.Panel):
    bl_label = "Structura.AI — Bridge"
    bl_idname = "STRUCTURA_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Structura.AI"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.structura_settings

        box = layout.box()
        box.label(text="🏛️ Conexão com Structura.AI", icon="NETWORK_DRIVE")
        box.prop(settings, "api_url")
        box.prop(settings, "project_name")

        col = layout.column(align=True)
        col.label(text="Dimensões Estruturais Estimadas:", icon="SNAP_GRID")
        col.prop(settings, "beam_width_cm")
        col.prop(settings, "beam_height_cm")
        col.prop(settings, "fck_mpa")

        layout.separator()
        layout.operator("structura.analyze", icon="PHYSICS")

        # Painel de Resultados
        res_box = layout.box()
        res_box.label(text="Diagnóstico da Física (NBR 6118):", icon="CHECKMARK" if settings.last_is_feasible else "ERROR")
        res_box.label(text=f"Status: {settings.last_status}")
        if settings.last_deflection_mm > 0:
            res_box.label(text=f"Flecha: {settings.last_deflection_mm:.1f} mm (Lim: {settings.last_limit_mm:.1f} mm)")

        if not settings.last_is_feasible:
            res_box.operator("structura.open_studio", icon="URL")


classes = (
    StructuraSettings,
    STRUCTURA_OT_analyze,
    STRUCTURA_OT_open_studio,
    STRUCTURA_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.structura_settings = bpy.props.PointerProperty(type=StructuraSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.structura_settings


if __name__ == "__main__":
    register()
