from bpy.types import Panel
from mpfb.services.uiservice import UiService


class BakeMeshForUnityPanel(Panel):
    bl_idname = "MTU_PT_Bake_Mesh_For_Unity_Panel"
    bl_label = "Bake mesh for Unity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = UiService.get_value("OPERATIONSCATEGORY")
    bl_parent_id = "MPFB_PT_Operations_Panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        self.layout.operator("mtu.bake_mesh_for_unity")
