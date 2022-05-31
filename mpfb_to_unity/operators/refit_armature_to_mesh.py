import os

from bpy.types import Operator
from mpfb.entities.rig import Rig
from mpfb.services.objectservice import ObjectService
from mpfb_to_unity.utils import get_data_directory


class RefitArmatureToMesh(Operator):
    bl_idname = "mtu.refit_armature_to_mesh"
    bl_label = "Convert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return ObjectService.object_is_skeleton(context.active_object)

    def execute(self, context):
        armature = context.active_object
        basemesh = ObjectService.find_object_of_type_amongst_nearest_relatives(armature, "Basemesh")
        data_dir = get_data_directory()
        rig_file = os.path.join(data_dir, "rig.json")
        rig = Rig.from_json_file_and_basemesh(rig_file, basemesh)
        rig.armature_object = armature

        rig.reposition_edit_bone()
        return {"FINISHED"}
