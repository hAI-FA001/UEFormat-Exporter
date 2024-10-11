from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

import io_scene_ueformat.importer as importer
from .utils import write_byte_size_wrapper

if TYPE_CHECKING:
    from io_scene_ueformat.exporter.writer import FArchiveWriter


class UEModel:
    @classmethod
    def to_archive(
        cls,
        model: importer.classes.UEModel,
        ar: FArchiveWriter,
    ) -> None:
        ar.write_fstring("LODS")
        ar.write_int(len(model.lods))
        write_byte_size_wrapper(ar, lambda ar: sum([UEModelLOD.to_archive(lod ,ar) for lod in model.lods]))

        if model.skeleton is not None:
            ar.write_fstring("SKELETON")
            ar.write_int(1)
            not_none_skel: importer.classes.UEModelSkeleton = model.skeleton
            write_byte_size_wrapper(ar, lambda ar: UEModelSkeleton.to_archive(not_none_skel, ar))
            
        ar.write_fstring("COLLISION")
        ar.write_int(len(model.collisions))
        write_byte_size_wrapper(ar, lambda ar: sum([ConvexCollision.to_archive(collision, ar) for collision in model.collisions]))


class UEModelLOD:
    @classmethod
    def to_archive(
        cls,
        lod: importer.classes.UEModelLOD,
        ar: FArchiveWriter,
    ) -> int:
        number_bytes_in_lod_name = ar.write_fstring(lod.name)
        pos_before = ar.tell()
        ar.pad(4)


        number_bytes_for_vertices = ar.write_fstring("VERTICES")
        flattened_verts = lod.vertices.flatten()
        number_bytes_for_vertices += ar.write_int(flattened_verts.shape[0] // 3)
        number_bytes_for_vertices += write_byte_size_wrapper(ar, lambda ar: ar.write_float_vector(flattened_verts))

        number_bytes_for_indices = ar.write_fstring("INDICES")
        flattened_indices = lod.indices.flatten()
        number_bytes_for_indices += ar.write_int(flattened_indices.shape[0])
        number_bytes_for_indices += write_byte_size_wrapper(ar, lambda ar: ar.write_int_vector(flattened_indices))

        number_bytes_for_normals = ar.write_fstring("NORMALS")
        # TODO: lod.normals has xyz instead of wxyz, need to handle that
        flattened_normals = lod.normals.flatten()
        number_bytes_for_normals += ar.write_int(flattened_normals.shape[0] // 4)
        number_bytes_for_normals += write_byte_size_wrapper(ar, lambda ar: ar.write_float_vector(flattened_normals))
        
        # TODO: TANGENTS section

        number_bytes_for_vertex_colors = ar.write_fstring("VERTEXCOLORS")
        number_bytes_for_vertex_colors += ar.write_int(len(lod.colors))
        number_bytes_for_vertex_colors += write_byte_size_wrapper(ar, lambda ar: sum([VertexColor.to_archive(vcol, ar) for vcol in lod.colors]))
        
        number_bytes_for_texcoords = ar.write_fstring("TEXCOORDS")
        number_bytes_for_texcoords += ar.write_int(len(lod.uvs))
        def write_uvs(ar: FArchiveWriter, uv: npt.NDArray):
            flattened_uv = uv.reshape(-1)
            total_bytes_written = ar.write_int(flattened_uv.shape[0] // 2)
            total_bytes_written += ar.write_float_vector(tuple(flattened_uv))
            return total_bytes_written
        number_bytes_for_texcoords += write_byte_size_wrapper(ar, lambda ar: sum([write_uvs(ar, uv) for uv in lod.uvs]))
        
        number_bytes_for_materials = ar.write_fstring("MATERIALS")
        number_bytes_for_materials += ar.write_int(len(lod.materials))
        number_bytes_for_materials += write_byte_size_wrapper(ar, lambda ar: sum([Material.to_archive(mat, ar) for mat in lod.materials]))

        number_bytes_for_weights = ar.write_fstring("WEIGHTS")
        number_bytes_for_weights += ar.write_int(len(lod.weights))
        number_bytes_for_weights += write_byte_size_wrapper(ar, lambda ar: sum([Weight.to_archive(weight, ar) for weight in lod.weights ]))

        number_bytes_for_morphs_targets = ar.write_fstring("MORPHTARGETS")
        number_bytes_for_morphs_targets += ar.write_int(len(lod.morphs))
        number_bytes_for_morphs_targets += write_byte_size_wrapper(ar, lambda ar: sum([MorphTarget.to_archive(morph, ar) for morph in lod.morphs]))


        total_bytes_for_lod_data = number_bytes_for_vertices + number_bytes_for_indices + number_bytes_for_normals \
        +  number_bytes_for_vertex_colors + number_bytes_for_texcoords + number_bytes_for_materials + number_bytes_for_weights + number_bytes_for_morphs_targets
        
        pos_after = ar.tell()
        ar.seek(pos_before)
        ar.write_int(total_bytes_for_lod_data)
        ar.seek(pos_after)
        
        return total_bytes_for_lod_data + number_bytes_in_lod_name + 4  # add 4 cuz lod_size itself takes 4 bytes


class UEModelSkeleton:
    @classmethod
    def to_archive(cls, skel: importer.classes.UEModelSkeleton, ar: FArchiveWriter) -> int:
        number_bytes_for_bones = ar.write_fstring("BONES")
        number_bytes_for_bones += ar.write_int(len(skel.bones))
        number_bytes_for_bones += write_byte_size_wrapper(ar, lambda ar: sum([Bone.to_archive(bone, ar) for bone in skel.bones]))

        number_bytes_for_sockets = ar.write_fstring("SOCKETS")
        number_bytes_for_sockets += ar.write_int(len(skel.sockets))
        number_bytes_for_sockets += write_byte_size_wrapper(ar, lambda ar: sum([Socket.to_archive(socket, ar) for socket in skel.sockets]))
        
        number_bytes_for_virtual_bones = ar.write_fstring("VIRTUALBONES")
        number_bytes_for_virtual_bones += ar.write_int(len(skel.virtual_bones))
        number_bytes_for_virtual_bones += write_byte_size_wrapper(ar, lambda ar: sum([VirtualBone.to_archive(vbone, ar) for vbone in skel.virtual_bones]))
        
        return number_bytes_for_bones + number_bytes_for_sockets + number_bytes_for_virtual_bones


class ConvexCollision:
    @classmethod
    def to_archive(cls, coll: importer.classes.ConvexCollision, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(coll.name)
        
        flattened = coll.vertices.reshape(-1)  # TODO: maybe use scale to undo scale
        vertices_count = flattened.shape[0]
        number_bytes_written += ar.write_int( vertices_count // 3)
        number_bytes_written += ar.write_float_vector(tuple(flattened))

        flattened = coll.indices.reshape(-1)
        indices_count = flattened.shape[0]
        number_bytes_written += ar.write_int(indices_count)
        number_bytes_written += ar.write_int_vector(tuple(flattened))

        return number_bytes_written


class VertexColor:
    @classmethod
    def to_archive(cls, vcol: importer.classes.VertexColor, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(vcol.name)

        original_array = (vcol.data.astype(np.int32) * 255)
        flattened = original_array.reshape(-1)
        count = flattened.shape[0]
        
        number_bytes_written += ar.write_int(count // 4)
        number_bytes_written += ar.write_byte_vector(tuple(flattened))

        return number_bytes_written


class Material:
    @classmethod
    def to_archive(cls, mat: importer.classes.Material, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(mat.material_name)
        number_bytes_written += ar.write_int(mat.first_index)
        number_bytes_written += ar.write_int(mat.num_faces)

        return number_bytes_written


class Bone:
    @classmethod
    def to_archive(cls, bone: importer.classes.Bone, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(bone.name)
        number_bytes_written += ar.write_int(bone.parent_index)
        number_bytes_written += ar.write_float_vector(tuple(bone.position))  # TODO: maybe use scale to undo scale
        number_bytes_written += ar.write_float_vector(tuple(bone.rotation))

        return number_bytes_written


class Weight:
    @classmethod
    def to_archive(cls, weight: importer.classes.Weight, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_short(weight.bone_index)
        number_bytes_written += ar.write_int(weight.vertex_index)
        number_bytes_written += ar.write_float(weight.weight)

        return number_bytes_written


class MorphTarget:
    @classmethod
    def to_archive(cls, morphTarget: importer.classes.MorphTarget, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(morphTarget.name)
        for morphTargetData in morphTarget.deltas:
            number_bytes_written += MorphTargetData.to_archive(morphTargetData, ar)
        return number_bytes_written


class MorphTargetData:
    @classmethod
    def to_archive(cls, morphTargetData: importer.classes.MorphTargetData, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_float_vector(tuple(morphTargetData.position))  # TODO: maybe use scale to undo scale
        number_bytes_written += ar.write_float_vector(morphTargetData.normals)
        number_bytes_written += ar.write_int(morphTargetData.vertex_index)

        return number_bytes_written


class Socket:
    @classmethod
    def to_archive(cls, socket: importer.classes.Socket, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(socket.name)
        number_bytes_written += ar.write_fstring(socket.parent_name)
        number_bytes_written += ar.write_float_vector(tuple(socket.position))  # TODO: maybe use scale to undo scale
        number_bytes_written += ar.write_float_vector(socket.rotation)
        number_bytes_written += ar.write_float_vector(socket.scale)
        
        return number_bytes_written


class VirtualBone:
    @classmethod
    def to_archive(cls, vbone: importer.classes.VirtualBone, ar: FArchiveWriter) -> int:
        number_bytes_written = ar.write_fstring(vbone.source_name)
        number_bytes_written += ar.write_fstring(vbone.target_name)
        number_bytes_written += ar.write_fstring(vbone.virtual_name)
        
        return number_bytes_written
