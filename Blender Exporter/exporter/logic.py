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

from ..importer.logging import Log
from ..importer import classes as uf_classes
from ..importer.classes import (
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
            self.file_version = uf_classes.EUEFormatVersion.LatestVersion
            object_name = self.get_obj_name()
            
            ar.write_string(MAGIC)
            ar.write_fstring(identifier)
            ar.write_byte(int.to_bytes(self.file_version, byteorder="big"))
            ar.write_fstring(object_name)

            Log.info(f"Exporting {object_name}")

            # TODO: maybe add compression option for the user
            is_compressed = False
            ar.write_bool(is_compressed)

            # for now, only handle UEModel
            self.export_uemodel_data(ar)
    
    def get_obj_name(self):
        # prefer armature name for now
        for armature in bpy.data.armatures:
            if self.options.export_selected_only and not armature.id_data.select_get():
                continue
            return armature.name
        
        if self.options.export_lods or self.options.export_collision:
            for mesh in bpy.data.meshes:
                if self.options.export_selected_only and not mesh.id_data.select_get():
                    continue
                return mesh.name
        
        return "NO_NAME_FOUND"
    
    def export_uemodel_data(self, ar: FArchiveWriter) -> None:
        lods: list[uf_classes.UEModelLOD] = []
        collisions: list[uf_classes.ConvexCollision] = []
        skeleton: uf_classes.UEModelSkeleton | None = None
        
        socket_idxs = []

        for obj in bpy.data.objects:
            if self.options.export_selected_only and not obj.select_get():
                continue
            with bpy.context.temp_override(selected_objects=[obj]):
                if obj.type == "MESH" \
                and (self.options.export_lods or self.options.export_collision):
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
                    
                    if obj.display_type != "WIRE" and self.options.export_lods:
                        lod = uf_classes.UEModelLOD(obj.name)
                            
                        lod.vertices = ue_verts
                        lod.indices = ue_indices
                        lod.normals = np.array([v.normal.to_4d().wxyz for v in verts], dtype=np.float32)
                        if mesh.uv_layers:
                            mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
                            lod.tangents = np.array([loop.tangent for loop in mesh.loops])
                        
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
                                        weight = uf_classes.Weight(0, 0, 0.0)
                                        
                                        weight.bone_index = armature_of_this_obj.bones.find(vgroup.name)
                                        weight.vertex_index = vert.index
                                        weight.weight = group.weight
                                        
                                        lod.weights.append(weight)
                                        break

                        lod.morphs = []
                        if mesh.shape_keys:
                            for key in mesh.shape_keys.key_blocks:
                                key: ShapeKey
                                morph = uf_classes.MorphTarget(key.name, deltas=[])
                                morphTargetNormals = np.array(key.normals_vertex_get()).reshape((-1, 3))
                                for idx in range(len(key.data)):
                                    delta = uf_classes.MorphTargetData([], (0, 0, 0), idx)
                                    
                                    keyPoint: ShapeKeyPoint = key.data[idx]
                                    delta.position = list(keyPoint.co.to_3d().to_tuple())
                                    delta.normals = morphTargetNormals[idx]
                                    
                                    morph.deltas.append(delta)
                                
                                lod.morphs.append(morph)

                        
                        lod.colors = []
                        for color_attr in mesh.color_attributes:
                            color_attr = cast(ByteColorAttribute, color_attr)
                            
                            vcolor = uf_classes.VertexColor(color_attr.name, np.array([]))
                            vcolor.data = np.array([list(c.color) for c in color_attr.data], dtype=np.float32)
                            
                            lod.colors.append(vcolor)

                        
                        bm = bmesh.new()
                        bm.from_mesh(mesh)
                        bpy.ops.object.mode_set(mode="EDIT")
                        
                        lod.uvs = []
                        uv_layer = bm.loops.layers.uv.active
                        lod_uv = [None] * len(bm.verts)
                        for v in bm.verts:
                            for l in v.link_loops:
                                # only get the first UV
                                lod_uv[v.index] = np.array(l[uv_layer].uv.to_tuple(), dtype=np.float32)
                                break
                        lod.uvs.append(np.array(lod_uv))
                        
                        bpy.ops.object.mode_set(mode="OBJECT")
                        bm.to_mesh(mesh)
                        bm.free()
                        


                        lod.materials = []
                        mat2Poly: dict[int, list[int]] = {}
                        for poly in mesh.polygons:
                            mat2Poly[poly.material_index] = mat2Poly.get(poly.material_index, []) + [poly.index]
                        
                        for i, material in enumerate(mesh.materials):
                            material: Material
                            
                            # this happens if the material isn't used by any vertex
                            try:
                                polys = mat2Poly[i]
                            except KeyError:
                                continue

                            polys.sort()

                            startPoly = 0
                            endPoly = 0
                            while endPoly < len(polys):
                                # get consecutive polys
                                while endPoly+1 < len(polys) and polys[endPoly+1] - polys[endPoly] == 1:
                                    endPoly += 1
                                lod_mat = uf_classes.Material(
                                    material.name,
                                    3 * polys[startPoly],
                                    endPoly - startPoly + 1
                                )
                                lod.materials.append(lod_mat)
                                
                                start = endPoly + 1
                                endPoly = start
                        
                        lod.name = "LOD0"
                        lods.append(lod)

                    elif self.options.export_collision:
                        collision = uf_classes.ConvexCollision(obj.name, ue_verts, ue_indices)
                        collisions.append(collision)

                elif obj.type == "ARMATURE":
                    socket_idxs = []  # reset socket idxs if more than 1 armature, TODO: more than 1 armature?
                    
                    armature = cast(Armature, obj.data)
                    skeleton = uf_classes.UEModelSkeleton()
                    sockets_exist = armature.collections.find("Sockets") != -1
                  
                    for idx, a_bone in enumerate(armature.bones):
                        if sockets_exist and a_bone.name in armature.collections["Sockets"].bones:
                            socket_idxs.append(idx)
                        
                        bone = uf_classes.Bone(a_bone.name, -1, [], (0.0, 0.0, 0.0, 0.0))
                        bone_matrix = a_bone.matrix_local

                        if a_bone.parent:
                            bone.parent_index = armature.bones.find(a_bone.parent.name)
                            # in import, BlenderMatrix = ParentBlenderMatrix x UFBoneMatrix
                            # so, UFBoneMatrix = inverted_ParentBlenderMatrix x BlenderMatrix
                            bone_matrix = armature.bones[a_bone.parent.name].matrix_local.inverted_safe() @ bone_matrix
                        
                        translation, rotation, _ = bone_matrix.decompose()
                        bone.position = list(translation.to_tuple())
                        bone.rotation = (rotation.x, rotation.y, rotation.z, rotation.w)

                        skeleton.bones.append(bone)
                        
                        
                    if armature.collections.find("Sockets") != -1 and self.options.export_sockets:
                        socket_collection: BoneCollection = armature.collections["Sockets"]
                        for socket in socket_collection.bones:
                            lod_socket: uf_classes.Socket = uf_classes.Socket(socket.name, "", [], (0,), (0,))
                            
                            bone_matrix = socket.matrix_local
                            
                            if socket.parent:
                                lod_socket.parent_name = socket.parent.name
                                bone_matrix = armature.bones[socket.parent.name].matrix_local.inverted_safe() @ bone_matrix
                            
                            translation, rotation, scale = bone_matrix.decompose()
                            lod_socket.position = list(translation.to_tuple())
                            lod_socket.rotation = (rotation.x, rotation.y, rotation.z, rotation.w)
                            lod_socket.scale = scale

                            skeleton.sockets.append(lod_socket)
                            

                    if armature.collections.find("Virtual Bones") != -1 and self.options.export_virtual_bones:

                        virtual_bone_collection: BoneCollection = armature.collections["Virtual Bones"]
                        for bone in virtual_bone_collection.bones:
                            armature_bones = armature.bones
                            lod_vbone = uf_classes.VirtualBone("", "", bone.name)

                            for source_bone in armature_bones:
                                if source_bone.tail == bone.head and source_bone.head == bone.tail:
                                    lod_vbone.source_name = source_bone.name
                                    break
                            
                            if lod_vbone.source_name == "":
                                continue
                            
                            bpy.ops.object.mode_set(mode="POSE")
                            pose_bone: PoseBone | None = obj.pose.bones[bone.name]
                            if pose_bone is None:
                                continue
                            
                            if pose_bone.constraints.find("IK") == -1:
                                continue

                            constraint = pose_bone.constraints["IK"]
                            constraint = cast(KinematicConstraint, constraint)
                            lod_vbone.target_name = constraint.subtarget

                            skeleton.virtual_bones.append(lod_vbone)

                        bpy.ops.object.mode_set(mode="OBJECT")


        for idx in sorted(socket_idxs, reverse=True):  # why does this work, it's so simple
            for bone in skeleton.bones:
                if not bone:
                    continue
                
                if bone.parent_index == idx:
                    bone.parent_index = -1
                elif bone.parent_index > idx:
                    bone.parent_index -= 1
                
                skeleton.bones[idx] = None
            
            for lod in lods:
                for widx, weight in enumerate(lod.weights.copy()):
                    if not weight:
                        continue
                    
                    if weight.bone_index == idx:
                        lod.weights[widx] = None
                    elif weight.bone_index > idx:
                        weight.bone_index -= 1
            
                lod.weights = list(filter(lambda w: w is not None, lod.weights))
        skeleton.bones = list(filter(lambda b: b is not None, skeleton.bones))
        
        
        uemodel = uf_classes.UEModel()
        if lods and len(lods) != 0:
            uemodel.lods = lods
        if collisions and len(collisions) != 0:
            uemodel.collisions = collisions
        if skeleton:
            uemodel.skeleton = skeleton
        
        if uemodel.lods or uemodel.collisions or uemodel.skeleton:
            UEModel.to_archive(uemodel, ar, self.options.scale_factor)
