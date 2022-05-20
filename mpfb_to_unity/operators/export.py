from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, axis_conversion

_UNITY_AXIS_UP = "Y"
_UNITY_AXIS_FORWARD = "-Z"


class ExportUnityFbx(Operator, ExportHelper):
    bl_idname = "mtu.export_unity_fbx"
    bl_label = "Export Unity FBX"
    bl_options = {"UNDO", "PRESET"}

    # Export helper options
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={"HIDDEN"})

    # User controlled options
    object_types: EnumProperty(
        name="Object Types",
        options={"ENUM_FLAG"},
        items=(
            ("EMPTY", "Empty", ""),
            ("CAMERA", "Camera", ""),
            ("LIGHT", "Lamp", ""),
            ("ARMATURE", "Armature", "WARNING: not supported in dupli/group instances"),
            ("MESH", "Mesh", ""),
            (
                "OTHER",
                "Other",
                "Other geometry types, like curve, metaball, etc. (converted to meshes)",
            ),
        ),
        description="Which kind of object to export",
        default={"EMPTY", "ARMATURE", "MESH", "OTHER"},
    )

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=False,
    )
    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects from the active collection (and its children)",
        default=False,
    )

    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")

        from io_scene_fbx import export_fbx_bin

        kwargs = {
            "filepath": self.filepath,
            "global_matrix": axis_conversion(
                to_forward=_UNITY_AXIS_FORWARD,
                to_up=_UNITY_AXIS_UP,
            ).to_4x4(),
            "axis_up": _UNITY_AXIS_UP,
            "axis_forward": _UNITY_AXIS_FORWARD,
            "bake_space_transform": True,
            "context_objects": self.get_context_objects(context),
            "object_types": self.object_types,
            "use_mesh_edges": False,
            "use_tspace": False,  # Questionable
            "use_custom_props": True,
            "use_armature_deform_only": True,
        }

        depsgraph = context.evaluated_depsgraph_get()
        return export_fbx_bin.save_single(self, context.scene, depsgraph, **kwargs)

    def get_context_objects(self, context):
        if self.use_active_collection:
            if self.use_selection:
                return tuple(
                    obj
                    for obj in context.view_layer.active_layer_collection.collection.all_objects
                    if obj.select_get()
                )
            else:
                return context.view_layer.active_layer_collection.collection.all_objects
        else:
            if self.use_selection:
                return context.selected_objects
            else:
                return context.view_layer.objects
