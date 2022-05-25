import os
from functools import reduce

import bpy
from bpy.types import Operator
from mpfb.entities.rig import Rig
from mpfb.services.locationservice import LocationService
from mpfb.services.objectservice import ObjectService
from mpfb.services.rigifyhelpers.rigifyhelpers import RigifyHelpers
from mpfb.services.rigservice import RigService
from rigify.utils.layers import DEF_LAYER, ROOT_LAYER

from mpfb_to_unity.utils import select_objects, edit_objects, load_json, change_mode_contextually


class RigForUnity(Operator):
    bl_idname = "mtu.rig_for_unity"
    bl_label = "Rig for unity"
    bl_options = {"REGISTER", "UNDO"}

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

    def execute(self, context):
        body_mesh = context.active_object
        armature = self._rig_with_mpfb(body_mesh)
        rigify_armature = self._convert_to_rigify(context, armature)
        self._fix_def_bones_hierarchy(context, rigify_armature)
        self._remove_unused_deform_bones(context, rigify_armature, body_mesh)
        self._disable_ik_stretching(rigify_armature)
        self._disable_bones_bending(context, rigify_armature)

        select_objects(context, [rigify_armature])
        return {"FINISHED"}

    def _rig_with_mpfb(self, basemesh):
        rigs_dir = LocationService.get_mpfb_data("rigs")

        armature_object = self._create_armature(rigs_dir, basemesh)
        basemesh.parent = armature_object
        self._apply_wieghts(rigs_dir, armature_object, basemesh)
        RigService.normalize_rotation_mode(armature_object)
        return armature_object

    def _convert_to_rigify(self, context, armature):
        select_objects(context, [armature])
        bpy.ops.object.transform_apply(location=True, scale=False, rotation=False)
        rigify_helpers = RigifyHelpers.get_instance({"produce": True, "keep_meta": False})
        rigify_helpers.convert_to_rigify(armature)
        return context.active_object

    def _fix_def_bones_hierarchy(self, context, armature):
        edit_objects(context, [armature])
        deform_bones = self._get_bones_for_layer(armature.data.edit_bones, DEF_LAYER)
        root_bone = self._get_bones_for_layer(armature.data.edit_bones, ROOT_LAYER)[0]

        for bone in deform_bones:
            if bone.parent == root_bone or bone.parent in deform_bones:
                continue

            try:
                self._update_parent_bone(bone, deform_bones, root_bone)
            except Exception as e:
                print(f"Bone {bone.name} not processed correctly, reason: {str(e)}")
                self.report(
                    {"WARNING"}, f"Bone {bone.name} not processed correctly, reason: {str(e)}"
                )

    def _remove_unused_deform_bones(self, context, armature, mesh):
        select_objects(context, [armature])
        armature.data.layers = DEF_LAYER

        with change_mode_contextually("EDIT"):
            bpy.ops.armature.select_all(action="DESELECT")

        deform_bones = self._get_bones_for_layer(armature.data.bones, DEF_LAYER)
        for bone in deform_bones:
            if bone.name not in mesh.vertex_groups:
                bone.driver_remove("bbone_easein")
                bone.driver_remove("bbone_easeout")
                bone.parent.select_tail = True

        with change_mode_contextually("EDIT"):
            bpy.ops.armature.dissolve()

    def _disable_ik_stretching(self, armature):
        for bone in armature.pose.bones:
            bone.ik_stretch = 0  # general blender property
            if "IK_Stretch" in bone:
                bone["IK_Stretch"] = 0.0  # custom rigify property

    def _disable_bones_bending(self, context, armature):
        select_objects(context, [armature])
        for bone in armature.data.bones:
            bone.driver_remove("bbone_easein")
            bone.driver_remove("bbone_easeout")
            bone.bbone_segments = 1

    def _create_armature(self, rigs_dir, basemesh):
        rig_file = os.path.join(rigs_dir, "standard", "rig.game_engine.json")
        rig = Rig.from_json_file_and_basemesh(rig_file, basemesh)
        return rig.create_armature_and_fit_to_basemesh()

    def _apply_wieghts(self, rigs_dir, armature_object, basemesh):
        weights_file = os.path.join(rigs_dir, "standard", "weights.game_engine.json")
        weights = load_json(weights_file)
        RigService.apply_weights(armature_object, basemesh, weights)

    def _get_bones_for_layer(self, bones, layer_mask):
        res = []
        for bone in bones:
            matches = map(
                lambda layers: layers[0] == layers[1] or not layers[0], zip(layer_mask, bone.layers)
            )
            if reduce(lambda m1, m2: m1 and m2, matches):
                res.append(bone)
        return res

    def _update_parent_bone(self, bone, deform_bones, root_bone):
        name_parts = bone.name.split("-")
        self._ensure_bone_prefix(name_parts, "DEF")

        full_parent_name = self._convert_org_name_to_def(bone.parent.name)
        if full_parent_name == bone.name:
            # Some DEF bones parented to their ORG equivalent
            full_parent_name = self._convert_org_name_to_def(bone.parent.parent.name)

        print(f"{bone.name}: {bone.parent.name} -> {full_parent_name}")
        if full_parent_name == "DEF-Root":
            bone.parent = root_bone
        else:
            bone.parent = next(filter(lambda b: b.name == full_parent_name, deform_bones))

    def _convert_org_name_to_def(self, org_name):
        name_parts = org_name.split("-")
        self._ensure_bone_prefix(name_parts, "ORG")
        name_parts[0] = "DEF"
        return "-".join(name_parts)

    def _ensure_bone_prefix(self, name_parts, expected_prefix):
        if name_parts[0] != expected_prefix:
            raise Exception(f"Bad bone prefix, excepted {expected_prefix}, got {name_parts[0]}")
