from functools import reduce
from bpy.ops import armature as ArmatureOps
from rigify.utils.layers import DEF_LAYER, ROOT_LAYER
from mpfb_to_unity.utils import change_armature_layers_contextually, change_mode_contextually


class DeformBonesHierarchyHelper:
    def __init__(self, edit_bones):
        self._deform_bones = _get_bones_for_layer(edit_bones, DEF_LAYER)
        self._root_bone = _get_bones_for_layer(edit_bones, ROOT_LAYER)[0]

    def simplify_hierarchy(self, armature, mesh):
        _constraints_copy_queue = []
        for bone in self._deform_bones:
            if bone.parent == self._root_bone or bone.parent in self._deform_bones:
                continue

            try:
                new_parent_name = self._convert_bone_name_to_def(bone.parent)
                if new_parent_name == bone.name:
                    # Some DEF bones parented to their ORG equivalent
                    _constraints_copy_queue.append((bone.parent.name, bone.name))
                    new_parent_name = self._convert_bone_name_to_def(bone.parent.parent)

                self._update_bone_parent(bone, new_parent_name)
            except Exception as e:
                print(f"Bone {bone.name} not processed correctly, reason: {str(e)}")
                self.report(
                    {"WARNING"}, f"Bone {bone.name} not processed correctly, reason: {str(e)}"
                )
        self._remove_unused_deform_bones(armature, mesh)
        return _constraints_copy_queue

    def _convert_bone_name_to_def(self, bone):
        name_parts = bone.name.split("-")
        self._ensure_bone_prefix(name_parts, "ORG")
        name_parts[0] = "DEF"
        return "-".join(name_parts)

    def _update_bone_parent(self, bone, new_parent_name):
        print(f"{bone.name}: {bone.parent.name} -> {new_parent_name}")
        if new_parent_name == "DEF-Root":
            bone.parent = self._root_bone
        else:
            bone.parent = next(filter(lambda b: b.name == new_parent_name, self._deform_bones))

    def _remove_unused_deform_bones(self, armature, mesh):
        with change_armature_layers_contextually(armature, DEF_LAYER):
            ArmatureOps.select_all(action="DESELECT")

            deform_bones = _get_bones_for_layer(armature.data.bones, DEF_LAYER)
            for bone in deform_bones:
                if bone.name not in mesh.vertex_groups:
                    bone.driver_remove("bbone_easein")
                    bone.driver_remove("bbone_easeout")
                    bone.parent.select_tail = True

            ArmatureOps.dissolve()

    def _ensure_bone_prefix(self, name_parts, expected_prefix):
        if name_parts[0] != expected_prefix:
            raise Exception(f"Bad bone prefix, excepted {expected_prefix}, got {name_parts[0]}")


def _get_bones_for_layer(bones, layer_mask):
    res = []
    for bone in bones:
        matches = map(
            lambda layers: layers[0] == layers[1] or not layers[0], zip(layer_mask, bone.layers)
        )
        if reduce(lambda m1, m2: m1 and m2, matches):
            res.append(bone)
    return res
