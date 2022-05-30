from bpy.types import TOPBAR_MT_file_export
from bpy.utils import register_class, unregister_class

bl_info = {
    "name": "mpfb_to_unity",
    "author": "GRascm",
    "blender": (2, 93, 0),
    "version": (0, 0, 1),
    "description": "MPFB tweaks and utils for better support in Unity",
    "category": "MakeHuman",
}

REGISTERED_DEPS = []


def register():
    deps = import_dependencies()
    for dep in deps:
        register_class(dep)
        REGISTERED_DEPS.append(dep)

    TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for dep in REGISTERED_DEPS:
        unregister_class(dep)


def import_dependencies():
    from .operators import ExportUnityFbx, NewUnityHuman, ConvertToRigify, BakeMeshForUnity
    from .panels import NewUnityHumanPanel, ConvertToRigifyPanel, BakeMeshForUnityPanel

    return (
        ExportUnityFbx,
        NewUnityHuman,
        ConvertToRigify,
        BakeMeshForUnity,
        NewUnityHumanPanel,
        ConvertToRigifyPanel,
        BakeMeshForUnityPanel,
    )


def menu_func_export(self, context):
    self.layout.operator("mtu.export_unity_fbx", text="Unity FBX (.fbx)")
