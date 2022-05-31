import os

from bpy.types import Operator, Scene
from mpfb.entities.rig import Rig
from mpfb.services.assetservice import AssetService
from mpfb.services.blenderconfigset import BlenderConfigSet
from mpfb.services.humanservice import HumanService
from mpfb.services.rigservice import RigService
from mpfb_to_unity.utils import get_data_directory, load_json, select_objects, rename_object

_AVALIABLE_EYES = AssetService.get_asset_list("eyes", "mhclo")
NEW_HUMAN_PROPERTIES = BlenderConfigSet(
    [
        {
            "name": "name",
            "label": "Name",
            "description": "Objects name",
            "type": "string",
            "default": "Human",
        },
        {
            "name": "eyes_type",
            "label": "Eyes type",
            "description": "Human eyes type",
            "type": "enum",
            "default": None,
            "items": [(label, label, "") for label, info in _AVALIABLE_EYES.items()],
        },
    ],
    Scene,
    prefix="mtu_new_human_",
)


class NewUnityHuman(Operator):
    bl_idname = "mtu.new_unity_human"
    bl_label = "Create with unity rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        name = NEW_HUMAN_PROPERTIES.get_value("name", entity_reference=context.scene)

        basemesh = HumanService.create_human()
        basemesh.use_shape_key_edit_mode = True
        rename_object(basemesh, f"{name}Mesh")

        armature = self._rig_with_mpfb(basemesh)
        rename_object(armature, name)
        eyes_type = NEW_HUMAN_PROPERTIES.get_value("eyes_type", entity_reference=context.scene)
        self._add_eyes(basemesh, eyes_type, name)

        select_objects(context, [armature])
        return {"FINISHED"}

    def _rig_with_mpfb(self, basemesh):
        data_dir = get_data_directory()

        armature_object = self._create_armature(data_dir, basemesh)
        basemesh.parent = armature_object
        self._apply_wieghts(data_dir, armature_object, basemesh)
        RigService.normalize_rotation_mode(armature_object)
        return armature_object

    def _create_armature(self, data_dir, basemesh):
        rig_file = os.path.join(data_dir, "rig.json")
        rig = Rig.from_json_file_and_basemesh(rig_file, basemesh)
        return rig.create_armature_and_fit_to_basemesh()

    def _apply_wieghts(self, data_dir, armature_object, basemesh):
        weights_file = os.path.join(data_dir, "weights.json")
        weights = load_json(weights_file)
        RigService.apply_weights(armature_object, basemesh, weights)

    def _add_eyes(self, basemesh, eyes_type, name):
        eyes = HumanService.add_mhclo_asset(
            _AVALIABLE_EYES[eyes_type]["full_path"],
            basemesh,
            asset_type="Eyes",
            subdiv_levels=0,
            material_type="PROCEDURAL_EYES",
        )
        rename_object(eyes, f"{name}EyesMesh")

        eye_l_group = eyes.vertex_groups.new(name="eye_l")
        eye_l_group.add([v.index for v in eyes.data.vertices if v.co.x > 0], 1 / 3, "ADD")
        eye_r_group = eyes.vertex_groups.new(name="eye_r")
        eye_r_group.add([v.index for v in eyes.data.vertices if v.co.x < 0], 1 / 3, "ADD")
        eyes.vertex_groups.remove(eyes.vertex_groups["head"])
