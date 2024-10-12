from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np
import bmesh
import bpy
from bpy.types import Mesh, Armature, ShapeKey, ByteColorAttribute, Material, BoneCollection, PoseBone, KinematicConstraint, ArmatureModifier, ShapeKeyPoint, MeshVertex
from mathutils import Vector, Quaternion

from .classes import UEModel
from .writer import FArchiveWriter
from ..options import UEFormatOptions

from io_scene_ueformat.logging import Log
import io_scene_ueformat.importer as importer
from io_scene_ueformat.importer.classes import (
    ANIM_IDENTIFIER,
    MAGIC,
    MODEL_IDENTIFIER,
)


class UEFormatExport:
    def __init__(self, options: UEFormatOptions) -> None:
        self.options = options
    
    def export_file(self, path: str | Path) -> None:
        path = path if isinstance(path, Path) else Path(path)

        Log.time_start(f"Export {path}")

        self.export_data(path)
        
        Log.time_end(f"Export {path}")


    def export_data(self, path: Path) -> None:
        with FArchiveWriter(path) as ar:
            ar: FArchiveWriter
            
            # for now, only handle models
            identifier = MODEL_IDENTIFIER
            self.file_version = importer.classes.EUEFormatVersion.LatestVersion
            object_name = "object1"  # TODO: correct object name
            
            ar.write_string(MAGIC)
            ar.write_fstring(identifier)
            ar.write_byte(int.to_bytes(self.file_version, byteorder="big"))
            ar.write_fstring(object_name)

            Log.info(f"Exporting {object_name}")

            # TODO: maybe add compression option for the user
            is_compressed = False
            ar.write_bool(is_compressed)

            # for now, only handle UEModel
            if True: #isinstance(obj, importer.classes.UEModel):
                self.export_uemodel_data(ar)
    
    def export_uemodel_data(self, ar: FArchiveWriter) -> None:
        lods: list[importer.classes.UEModelLOD] = []
        collisions: list[importer.classes.ConvexCollision] = []
        skeleton: importer.classes.UEModelSkeleton | None = None

        
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                mesh: Mesh = cast(Mesh, obj.data)
                
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bpy.ops.object.mode_set(mode="EDIT")
                bmesh.ops.triangulate(bm, faces=bm.faces)
                bpy.ops.object.mode_set(mode="OBJECT")
                bm.to_mesh(mesh)
                bm.free()
                
                verts = [v for v in mesh.vertices]
                ue_verts = np.array([v.co for v in verts], dtype=np.float32)
                ue_indices = np.array([list(poly.vertices) for poly in mesh.polygons], dtype=np.int32)
                
                if obj.display_type != "WIRE":
                    lod = importer.classes.UEModelLOD(obj.name)
                        
                    lod.vertices = ue_verts
                    lod.indices = ue_indices
                    lod.normals = np.array([v.normal.to_4d().wxyz for v in verts], dtype=np.float32)
                    
                    lod.weights = []
                    armature_of_this_obj: Armature = None
                    for modifier in obj.modifiers:
                        if isinstance(modifier, ArmatureModifier):
                            armature_of_this_obj = modifier.object.data
                            break

                    for vgroup in obj.vertex_groups:
                        for vert in verts:
                            for group in vert.groups:
                                if group.group == vgroup.index:
                                    weight = importer.classes.Weight(0, 0, 0.0)
                                    
                                    weight.bone_index = armature_of_this_obj.bones.find(vgroup.name)
                                    weight.vertex_index = vert.index
                                    weight.weight = group.weight
                                    
                                    lod.weights.append(weight)
                                    break

                    lod.morphs = []
                    if mesh.shape_keys:
                        for key in mesh.shape_keys.key_blocks:
                            key: ShapeKey
                            morph = importer.classes.MorphTarget(key.name, deltas=[])
                            morphTargetNormals = np.array(key.normals_vertex_get()).reshape((-1, 3))
                            for idx in range(len(key.data)):
                                delta = importer.classes.MorphTargetData([], (0, 0, 0), idx)
                                
                                keyPoint: ShapeKeyPoint = key.data[idx]
                                delta.position = list(keyPoint.co.to_3d().to_tuple())
                                delta.normals = morphTargetNormals[idx]
                                
                                morph.deltas.append(delta)
                            
                            lod.morphs.append(morph)

                    
                    lod.colors = []
                    for color_attr in mesh.color_attributes:
                        color_attr = cast(ByteColorAttribute, color_attr)
                        
                        vcolor = importer.classes.VertexColor(color_attr.name, np.array([]))
                        vcolor.data = np.array([list(c.color) for c in color_attr.data], dtype=np.float32)
                        
                        lod.colors.append(vcolor)

                    
                    lod.uvs = []
                    for uv_layer in mesh.uv_layers:
                        lod_uv = []
                        for uv in uv_layer.uv:
                            lod_uv.append(np.array(uv.vector.to_tuple(), dtype=np.float32))
                        lod.uvs.append(np.array(lod_uv))

                    lod.materials = []
                    mat2Poly: dict[int, list[int]] = {}
                    for poly in mesh.polygons:
                        mat2Poly[poly.material_index] = mat2Poly.get(poly.material_index, []) + [poly.index]
                    for i, material in enumerate(mesh.materials):
                        material: Material
                        
                        try:
                            polys = mat2Poly[i]
                        except KeyError:
                            continue
                        polys.sort()
                        start = 0
                        end = 1
                        while end < len(polys):
                            # expand  the window [start, end] as long as these are consecutive faces
                            while end < len(polys) and polys[end] - polys[start] == end - start:
                                end += 1

                            lod_mat = importer.classes.Material(material.name, 0, 0)
                            lod_mat.first_index = polys[start]
                            lod_mat.num_faces = end - start
                            lod.materials.append(lod_mat)
                            
                            start = end
                    
                    lods.append(lod)
                else:
                    collision = importer.classes.ConvexCollision(obj.name, ue_verts, ue_indices)
                    collisions.append(collision)

            elif obj.type == "ARMATURE":
                armature = cast(Armature, obj.data)
                skeleton = importer.classes.UEModelSkeleton()

                bpy.ops.object.mode_set(mode="EDIT")
                edit_bones = armature.bones
                for edit_bone in edit_bones:
                    bone = importer.classes.Bone(edit_bone.name, -1, [], (0.0, 0.0, 0.0, 0.0))
                    translation, rotation, _ = edit_bone.matrix.to_4x4().decompose()
                    bone.position = list(translation.to_tuple())
                    bone.rotation = (rotation.w, rotation.x, rotation.y, rotation.z)

                    if edit_bone.parent:
                        bone.parent_index = armature.bones.find(edit_bone.parent.name)
                    
                    skeleton.bones.append(bone)
                    
                bpy.ops.object.mode_set(mode="OBJECT")

                # TODO: sockets

                if armature.collections.find("Virtual Bones") != -1:

                    virtual_bone_collection: BoneCollection = armature.collections[armature.collections.find("Virtual Bones")]
                    for bone in virtual_bone_collection.bones:
                        bpy.ops.object.mode_set(mode="EDIT")
                        edit_bones = armature.edit_bones
                        lod_vbone = importer.classes.VirtualBone("", "", bone.name)

                        for source_bone in edit_bones:
                            if source_bone.tail == bone.head and source_bone.head == bone.tail:
                                lod_vbone.source_name = source_bone.name
                                break
                        
                        if lod_vbone.source_name == "":
                            continue
                        
                        bpy.ops.object.mode_set(mode="POSE")
                        pose_bone: PoseBone | None = obj.pose.bones.get(bone.name)
                        if pose_bone is None:
                            continue
                        
                        if pose_bone.constraints.find("IK") != -1:
                            constraint = pose_bone.constraints[pose_bone.constraints.find("IK")]
                            constraint = cast(KinematicConstraint, constraint)
                            lod_vbone.target_name = constraint.subtarget

                        skeleton.virtual_bones.append(lod_vbone)
                    
                    bpy.ops.object.mode_set(mode="OBJECT")
            
        
        uemodel = importer.classes.UEModel()
        if lods and len(lods) != 0:
            uemodel.lods = lods
        if collisions and len(collisions) != 0:
            uemodel.collisions = collisions
        if skeleton:
            uemodel.skeleton = skeleton
        
        if uemodel.lods or uemodel.collisions or uemodel.skeleton:
            UEModel.to_archive(uemodel, ar)
