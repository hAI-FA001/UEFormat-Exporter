from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

MAGIC = "UEFORMAT"
MODEL_IDENTIFIER = "UEMODEL"
ANIM_IDENTIFIER = "UEANIM"


class EUEFormatVersion(IntEnum):
    BeforeCustomVersionWasAdded = 0
    SerializeBinormalSign = 1
    AddMultipleVertexColors = 2
    AddConvexCollisionGeom = 3
    LevelOfDetailFormatRestructure = 4
    SerializeVirtualBones = 5

    VersionPlusOne = auto()
    LatestVersion = VersionPlusOne - 1


@dataclass(slots=True)
class UEModel:
    lods: list[UEModelLOD] = field(default_factory=list)
    collisions: list[ConvexCollision] = field(default_factory=list)
    skeleton: UEModelSkeleton | None = None


@dataclass(slots=True)
class UEModelLOD:
    name: str
    vertices: npt.NDArray[np.floating] = field(default_factory=lambda: np.zeros(0))
    indices: npt.NDArray[np.int32] = field(default_factory=lambda: np.zeros(0, dtype=np.int32))
    normals: npt.NDArray[np.floating] = field(default_factory=lambda: np.zeros(0))
    tangents: list = field(default_factory=list)
    colors: list[VertexColor] = field(default_factory=list)
    uvs: list[npt.NDArray[Any]] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    morphs: list[MorphTarget] = field(default_factory=list)
    weights: list[Weight] = field(default_factory=list)


@dataclass(slots=True)
class UEModelSkeleton:
    bones: list[Bone] = field(default_factory=list)
    sockets: list[Socket] = field(default_factory=list)
    virtual_bones: list[VirtualBone] = field(default_factory=list)


@dataclass(slots=True)
class ConvexCollision:
    name: str
    vertices: npt.NDArray[np.floating[Any]]
    indices: npt.NDArray[np.int32]


@dataclass(slots=True)
class VertexColor:
    name: str
    data: npt.NDArray[np.float32]


@dataclass(slots=True)
class Material:
    material_name: str
    first_index: int
    num_faces: int


@dataclass(slots=True)
class Bone:
    name: str
    parent_index: int
    position: list[float]
    rotation: tuple[float, float, float, float]


@dataclass(slots=True)
class Weight:
    bone_index: int
    vertex_index: int
    weight: float


@dataclass(slots=True)
class MorphTarget:
    name: str
    deltas: list[MorphTargetData]


@dataclass(slots=True)
class MorphTargetData:
    position: list[float]
    normals: tuple[float, float, float]
    vertex_index: int


@dataclass(slots=True)
class Socket:
    name: str
    parent_name: str
    position: list[float]
    rotation: tuple[float, float, float, float]
    scale: tuple[float, float, float]


@dataclass(slots=True)
class VirtualBone:
    source_name: str
    target_name: str
    virtual_name: str
