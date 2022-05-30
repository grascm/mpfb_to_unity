import bpy
from bpy.types import Operator
from mpfb.services.objectservice import ObjectService
from mpfb_to_unity.utils import select_objects, change_mode_contextually


class BakeMeshForUnity(Operator):
    bl_idname = "mtu.bake_mesh_for_unity"
    bl_label = "Bake"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == "ARMATURE"

    def execute(self, context):
        bpy.ops.object.select_hierarchy(direction="CHILD", extend=True)
        original_objects = context.selected_objects
        bpy.ops.object.duplicate()
        new_objects = context.selected_objects

        self._hide_objects(original_objects)
        self._apply_shape_keys(context, new_objects)
        self._remove_joints(context, new_objects)
        mesh = self._merge_meshes(context, new_objects)
        meshes = self._extract_helpers(context, mesh)
        for mesh in meshes:
            self._remove_modifier(mesh, "Hide helpers")
            self._remove_empty_vertex_groups(mesh)

        return {"FINISHED"}

    def _hide_objects(self, objects):
        for obj in objects:
            obj.hide_set(True)

    def _apply_shape_keys(self, context, objects):
        for obj in objects:
            if obj.type != "MESH":
                continue
            context.view_layer.objects.active = obj
            bpy.ops.object.shape_key_add(from_mix=True)
            for shape_key in obj.data.shape_keys.key_blocks:
                obj.shape_key_remove(shape_key)

    def _remove_joints(self, context, objects):
        for obj in objects:
            if not ObjectService.object_is_basemesh(obj):
                continue

            group_index = self._find_group_index(obj, "JointCubes")
            vertecies = self._get_group_vertecies(obj, group_index)
            self._select_vertecies(context, obj, vertecies)

            with change_mode_contextually("EDIT"):
                bpy.ops.mesh.delete(type="VERT")

    def _merge_meshes(self, context, objects):
        meshes = []
        target_mesh = None
        for obj in objects:
            if ObjectService.object_is_basemesh(obj):
                target_mesh = obj
            elif obj.type == "MESH":
                meshes.append(obj)

        select_objects(context, meshes + [target_mesh])
        bpy.ops.object.join()
        return context.active_object

    def _extract_helpers(self, context, mesh):
        group_index = self._find_group_index(mesh, "HelperGeometry")
        vertecies = self._get_group_vertecies(mesh, group_index)
        self._select_vertecies(context, mesh, vertecies)

        with change_mode_contextually("EDIT"):
            bpy.ops.mesh.separate(type="SELECTED")
        return context.selected_objects

    def _remove_empty_vertex_groups(self, mesh):
        non_empty_groups = set()
        for vertex in mesh.data.vertices:
            for vertex_group in vertex.groups:
                non_empty_groups.add(vertex_group.group)

        empty_groups = []
        for group in mesh.vertex_groups:
            if group.index not in non_empty_groups:
                empty_groups.append(group)

        for group in empty_groups:
            mesh.vertex_groups.remove(group)

    def _remove_modifier(self, obj, name):
        modifier = obj.modifiers.get(name)
        if modifier is not None:
            obj.modifiers.remove(modifier)

    def _find_group_index(self, obj, group_name):
        for group in obj.vertex_groups:
            if group.name == group_name:
                return group.index

        raise Exception(f"Group '{group_name}' not found")

    def _get_group_vertecies(self, mesh, group_index):
        vertecies = []
        for vertex in mesh.data.vertices:
            for vertex_group in vertex.groups:
                if vertex_group.group == group_index:
                    vertecies.append(vertex.index)
        return vertecies

    def _select_vertecies(self, context, obj, vertecies):
        select_objects(context, [obj])
        with change_mode_contextually("EDIT"):
            bpy.ops.mesh.select_all(action="DESELECT")

        for i in vertecies:
            obj.data.vertices[i].select = True
