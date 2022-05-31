from bpy.types import Panel
from mpfb.services.uiservice import UiService


class RefitArmatureToMeshPanel(Panel):
    bl_idname = "MTU_PT_Refit_Armature_To_Mesh_Panel"
    bl_label = "Refit Unity armature to mesh"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = UiService.get_value("OPERATIONSCATEGORY")
    bl_parent_id = "MPFB_PT_Operations_Panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        self.layout.operator("mtu.refit_armature_to_mesh")
