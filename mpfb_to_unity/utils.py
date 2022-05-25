import json
from contextlib import contextmanager

import bpy


def edit_objects(context, obj_list):
    select_objects(context, obj_list)
    change_mode("EDIT")


def select_objects(context, obj_list):
    if context.active_object is not None:
        change_mode("OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in obj_list:
        obj.select_set(True)
        context.view_layer.objects.active = obj


def change_mode(new_mode):
    bpy.ops.object.mode_set(mode=new_mode, toggle=False)


@contextmanager
def change_mode_contextually(new_mode):
    old_mode = bpy.context.object.mode
    change_mode(new_mode)
    try:
        yield
    finally:
        change_mode(old_mode)


@contextmanager
def change_armature_layers_contextually(armature, new_layers):
    old_layers = list(armature.data.layers)
    armature.data.layers = new_layers
    try:
        yield
    finally:
        armature.data.layers = old_layers


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as json_file:
        return json.load(json_file)
