import bpy
from bpy.types import Operator
from mpfb.services.objectservice import ObjectService
from mpfb.services.rigifyhelpers.gameenginerigifyhelpers import GameEngineRigifyHelpers
from mpfb.services.rigservice import RigService
from mpfb_to_unity.utils import select_objects, change_mode_contextually, rename_object

from mpfb_to_unity.helpers import DeformBonesHierarchyHelper


class ConvertToRigify(Operator):
    bl_idname = "mtu.convert_to_rigify"
    bl_label = "Convert"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return ObjectService.object_is_skeleton(context.active_object)

    def execute(self, context):
        armature = context.active_object
        name = armature.name
        rename_object(armature, f"{name}Original")
        basemesh = ObjectService.find_object_of_type_amongst_nearest_relatives(
            context.active_object, "Basemesh"
        )
        select_objects(context, [armature])  # ensure it's the only object selected
        rigify_armature = self._convert_to_rigify(context, armature, name)

        select_objects(context, [rigify_armature])
        self._simplify_bones_hierarchy(rigify_armature, basemesh)
        self._disable_ik_stretching(rigify_armature)
        self._disable_bones_bending(rigify_armature)
        return {"FINISHED"}

    def _convert_to_rigify(self, context, armature, name):
        bpy.ops.object.transform_apply(location=True, scale=False, rotation=False)
        rigify_helpers = UnityRigifyHelpers({"produce": True, "keep_meta": False})
        rigify_helpers.convert_to_rigify(armature)
        rename_object(context.active_object, name)
        return context.active_object

    def _simplify_bones_hierarchy(self, armature, mesh):
        with change_mode_contextually("EDIT"):
            helper = DeformBonesHierarchyHelper(armature.data.edit_bones)
            _constraints_copy_queue = helper.simplify_hierarchy(armature, mesh)

        for src_name, dst_name in _constraints_copy_queue:
            self._copy_constraints(armature, src_name, dst_name)

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
