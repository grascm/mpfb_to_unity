from functools import reduce

import bpy
from bpy.types import Operator
from mpfb.services.objectservice import ObjectService
from mpfb.services.rigifyhelpers.gameenginerigifyhelpers import GameEngineRigifyHelpers
from mpfb.services.rigservice import RigService
from rigify.utils.layers import DEF_LAYER, ROOT_LAYER
from mpfb_to_unity.utils import (
    change_armature_layers_contextually,
    change_mode_contextually,
    select_objects,
)


class ConvertToRigify(Operator):
    bl_idname = "mtu.convert_to_rigify"
    bl_label = "Convert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return ObjectService.object_is_skeleton(context.active_object)

    def execute(self, context):
        armature = context.active_object
        basemesh = ObjectService.find_object_of_type_amongst_nearest_relatives(
            context.active_object, "Basemesh"
        )
        select_objects(context, [armature])  # ensure it's the only object selected
        rigify_armature = self._convert_to_rigify(context, armature)

        select_objects(context, [rigify_armature])
        self._fix_def_bones_hierarchy(rigify_armature)
        self._remove_unused_deform_bones(rigify_armature, basemesh)
        self._disable_ik_stretching(rigify_armature)
        self._disable_bones_bending(rigify_armature)
        return {"FINISHED"}

    def _convert_to_rigify(self, context, armature):
        bpy.ops.object.transform_apply(location=True, scale=False, rotation=False)
        rigify_helpers = UnityRigifyHelpers({"produce": True, "keep_meta": False})
        rigify_helpers.convert_to_rigify(armature)
        return context.active_object

    def _fix_def_bones_hierarchy(self, armature):
        _constraints_copy_queue = []
        with change_mode_contextually("EDIT"):
            deform_bones = self._get_bones_for_layer(armature.data.edit_bones, DEF_LAYER)
            root_bone = self._get_bones_for_layer(armature.data.edit_bones, ROOT_LAYER)[0]

            for bone in deform_bones:
                if bone.parent == root_bone or bone.parent in deform_bones:
                    continue

                try:
                    name_parts = bone.name.split("-")
                    self._ensure_bone_prefix(name_parts, "DEF")

                    full_parent_name = self._convert_org_name_to_def(bone.parent.name)
                    if full_parent_name == bone.name:
                        # Some DEF bones parented to their ORG equivalent
                        full_parent_name = self._convert_org_name_to_def(bone.parent.parent.name)
                        _constraints_copy_queue.append((bone.parent.name, bone.name))

                    print(f"{bone.name}: {bone.parent.name} -> {full_parent_name}")
                    if full_parent_name == "DEF-Root":
                        bone.parent = root_bone
                    else:
                        bone.parent = next(
                            filter(lambda b: b.name == full_parent_name, deform_bones)
                        )
                except Exception as e:
                    print(f"Bone {bone.name} not processed correctly, reason: {str(e)}")
                    self.report(
                        {"WARNING"}, f"Bone {bone.name} not processed correctly, reason: {str(e)}"
                    )
        for src_name, dst_name in _constraints_copy_queue:
            self._copy_constraints(armature, src_name, dst_name)

    def _remove_unused_deform_bones(self, armature, mesh):
        with change_armature_layers_contextually(armature, DEF_LAYER):
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

    def _disable_bones_bending(self, armature):
        for bone in armature.data.bones:
            bone.driver_remove("bbone_easein")
            bone.driver_remove("bbone_easeout")
            bone.bbone_segments = 1

    def _get_bones_for_layer(self, bones, layer_mask):
        res = []
        for bone in bones:
            matches = map(
                lambda layers: layers[0] == layers[1] or not layers[0], zip(layer_mask, bone.layers)
            )
            if reduce(lambda m1, m2: m1 and m2, matches):
                res.append(bone)
        return res

    def _ensure_bone_prefix(self, name_parts, expected_prefix):
        if name_parts[0] != expected_prefix:
            raise Exception(f"Bad bone prefix, excepted {expected_prefix}, got {name_parts[0]}")

    def _convert_org_name_to_def(self, org_name):
        name_parts = org_name.split("-")
        self._ensure_bone_prefix(name_parts, "ORG")
        name_parts[0] = "DEF"
        return "-".join(name_parts)

    def _copy_constraints(self, armature, src_name, dst_name):
        src_bone = armature.pose.bones[src_name]
        dst_bone = armature.pose.bones[dst_name]

        for constraint in src_bone.constraints:
            attributes = self._get_attributes_for_constraint_type(constraint.type) + [
                "enabled",
                "influence",
                "owner_space",
                "target_space",
            ]
            copy = dst_bone.constraints.new(constraint.type)
            for attr in attributes:
                setattr(copy, attr, getattr(constraint, attr))

    def _get_attributes_for_constraint_type(self, t):
        if t == "COPY_TRANSFORMS":
            return [
                "head_tail",
                "mix_mode",
                "remove_target_shear",
                "subtarget",
                "target",
                "use_bbone_shape",
            ]
        else:
            raise Exception(f"Unknown constraint type: {t}")


class UnityRigifyHelpers(GameEngineRigifyHelpers):
    def get_list_of_head_bones(self):
        return ["neck_01", "head", "jaw", "eye_l", "eye_r"]

    def get_list_of_connected_head_bones(self):
        return ["neck_01", "head"]

    def _setup_legs(self, armature_object):
        for side in [True, False]:
            leg = self.get_list_of_leg_bones(side)
            self._set_use_connect_on_bones(armature_object, leg)
            self._create_heel(armature_object, side)
            bpy.ops.object.mode_set(mode="POSE", toggle=False)
            first_leg_bone = RigService.find_pose_bone_by_name(leg[0], armature_object)
            first_leg_bone.rigify_type = "limbs.leg"

    def _setup_head(self, armature_object):
        head = self.get_list_of_connected_head_bones()
        self._set_use_connect_on_bones(armature_object, head)
        bpy.ops.object.mode_set(mode="POSE", toggle=False)
        first_head_bone = RigService.find_pose_bone_by_name(head[0], armature_object)
        first_head_bone.rigify_type = "spines.super_head"
        self._setup_face(armature_object)

    def _setup_face(self, armature_object):
        jaw_bone = RigService.find_pose_bone_by_name("jaw", armature_object)
        jaw_bone.rigify_type = "basic.super_copy"
        jaw_bone.rigify_parameters.super_copy_widget_type = "jaw"

        for eye in ("eye_l", "eye_r"):
            eye_bone = RigService.find_pose_bone_by_name(eye, armature_object)
            eye_bone.rigify_type = "basic.super_copy"

    def _create_heel(self, armature_object, left_side):
        bpy.ops.object.mode_set(mode="EDIT", toggle=False)
        suffix = "l" if left_side else "r"
        bones = armature_object.data.edit_bones
        foot = RigService.find_edit_bone_by_name(f"foot_{suffix}", armature_object)

        heel = bones.new(f"heel_{suffix}")
        heel.parent = foot
        heel.use_connect = False

        for joint in (heel.head, heel.tail):
            joint.x = foot.head.x
            joint.y = 0
            joint.z = foot.tail.z

        self._set_heel_width(heel, left_side)

    def _set_heel_width(self, bone, left_side):
        HEEL_WIDTH = 0.02
        if left_side:
            right, left = bone.head, bone.tail
        else:
            right, left = bone.tail, bone.head

        right.x -= HEEL_WIDTH / 2
        left.x += HEEL_WIDTH / 2
