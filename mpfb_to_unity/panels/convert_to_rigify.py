from bpy.types import Panel
from mpfb.services.objectservice import ObjectService
from mpfb.services.uiservice import UiService


class ConvertToRigifyPanel(Panel):
    bl_idname = "MTU_PT_Convert_To_Rigify_Panel"
    bl_label = "Convert to rigify for Unity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = UiService.get_value("MODELCATEGORY")
    bl_parent_id = "MPFB_PT_Rig_Panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return ObjectService.object_is_skeleton(context.active_object)

    def draw(self, context):
        self.layout.operator("mtu.convert_to_rigify")
