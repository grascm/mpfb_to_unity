from bpy.types import Panel
from mpfb.services.objectservice import ObjectService
from mpfb.services.uiservice import UiService


class RigForUnityPanel(Panel):
    bl_idname = "MTU_PT_Rig_For_Unity_Panel"
    bl_label = "Rig for Unity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = UiService.get_value("MODELCATEGORY")
    bl_parent_id = "MPFB_PT_Rig_Panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False

        armature_object = ObjectService.find_object_of_type_amongst_nearest_relatives(
            context.active_object, "Skeleton"
        )
        if armature_object is not None:
            return False
        return ObjectService.object_is_basemesh(context.active_object)

    def draw(self, context):
        self.layout.operator("mtu.rig_for_unity")
