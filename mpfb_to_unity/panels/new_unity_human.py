from bpy.types import Panel
from mpfb.services.uiservice import UiService
from mpfb_to_unity.operators.new_unity_human import NEW_HUMAN_PROPERTIES


class NewUnityHumanPanel(Panel):
    bl_idname = "MTU_PT_New_Unity_Human_Panel"
    bl_label = "For unity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = UiService.get_value("MODELCATEGORY")
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "MPFB_PT_New_Panel"

    def draw(self, context):
        NEW_HUMAN_PROPERTIES.draw_properties(context.scene, self.layout, ["eyes_type"])
        self.layout.operator("mtu.new_unity_human")
