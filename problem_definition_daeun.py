import numpy as np


from constants_and_tools import *

from numpy import array, asmatrix, matrix, zeros, ones
from numpy import array, dot, stack, vstack, hstack, asmatrix, identity, cross, concatenate
from numpy.linalg import norm

from scipy.spatial import ConvexHull
from hpp_bezier_com_traj import *

from random import random as rd
from random import randint as rdi
from numpy import squeeze, asarray
import qp

#LP contact planner using inequality formulation


############### Problem definition #############


LF = 0
RF = 1

def normalize(Ab):
    A = Ab[0]
    b = Ab[1]
    Ares = zeros(A.shape)
    bres = zeros(b.shape)
    for i in range(A.shape[0]):
        n = norm(A[i,:])
        if n <= 0.000001:
            n = 1.
        Ares[i,:] = A[i,:] / n; bres[i] = b[i] / n
    return Ares, bres

# added: align foot orientation with the root orientation
def genKinematicConstraints(index, transform, normals = [z, z], min_height = None):   #assume that root transform is given in 3x3 rotation matrix
    res = [None, None]
    
    if index == 0 :
        trLF = default_transform_from_pos_normal_(transform[index], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index], zero3, normals[RF])
    elif index % 2 == LF : # left foot is moving
        trLF = default_transform_from_pos_normal_(transform[index], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index-1], zero3, normals[RF])
    elif index % 2 == RF : # right foot is moving
        #print index
        trLF = default_transform_from_pos_normal_(transform[index-1], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index], zero3, normals[RF])

    KLF = left_foot_talos_constraints  (trLF)
    KRF = right_foot_talos_constraints (trRF)
    if min_height is None:
        res [LF] = KLF
        res [RF] = KRF
    else:
        res [LF] = addHeightConstraint(KLF[0], KLF[1], min_height)
        res [RF] = addHeightConstraint(KRF[0], KRF[1], min_height)
    return res
            

# added: align foot orientation with the root orientation
def genFootRelativeConstraints(index, transform, normals = [z, z]): #assume that root transform is given in 3x3 rotation matrix
    res = [None, None]
    if index == 0 :
        trLF = default_transform_from_pos_normal_(transform[index], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index], zero3, normals[RF])
    elif index % 2 == LF : # left foot is moving
        trLF = default_transform_from_pos_normal_(transform[index], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index-1], zero3, normals[RF])
    elif index % 2 == RF : # right foot is moving
        trLF = default_transform_from_pos_normal_(transform[index-1], zero3, normals[LF])
        trRF = default_transform_from_pos_normal_(transform[index], zero3, normals[RF])
    KLF = right_foot_in_lf_frame_talos_constraints  (trLF)
    KRF = left_foot_in_rf_frame_talos_constraints (trRF)    
    res [LF] = KLF #constraints of right foot in lf frame. Same idea as COM in lf frame
    res [RF] = KRF
    return res

"""    
#TODO: replace normals with transforms
def genKinematicConstraints(normals = [z, z], min_height = None):
    res = [None, None]
    trLF = default_transform_from_pos_normal(zero3, normals[LF])
    trRF = default_transform_from_pos_normal(zero3, normals[RF])
    KLF = left_foot_hrp2_constraints  (trLF)
    KRF = right_foot_hrp2_constraints (trRF)
    if min_height is None:
        res [LF] = KLF
        res [RF] = KRF
    else:
        res [LF] = addHeightConstraint(KLF[0], KLF[1], min_height)
        res [RF] = addHeightConstraint(KRF[0], KRF[1], min_height)
    return res

#TODO: replace normals with transforms
def genFootRelativeConstraints(normals = [z, z]):
    res = [None, None]
    trLF = default_transform_from_pos_normal(zero3, normals[LF])
    trRF = default_transform_from_pos_normal(zero3, normals[RF])
    KLF = right_foot_in_lf_frame_hrp2_constraints  (trLF)
    KRF = left_foot_in_rf_frame_hrp2_constraints (trRF)    
    res [LF] = KLF #constraints of right foot in lf frame. Same idea as COM in lf frame
    res [RF] = KRF
    return res
"""

#TODO: replace normals with transforms
def genKinematicConstraintsTalos(normals = [z, z], min_height = None):
    res = [None, None]
    trLF = default_transform_from_pos_normal(zero3, normals[LF])
    trRF = default_transform_from_pos_normal(zero3, normals[RF])
    KLF = left_foot_talos_constraints  (trLF)
    KRF = right_foot_talos_constraints (trRF)
    if min_height is None:
        res [LF] = KLF
        res [RF] = KRF
    else:
        res [LF] = addHeightConstraint(KLF[0], KLF[1], min_height)
        res [RF] = addHeightConstraint(KRF[0], KRF[1], min_height)
    return res

#TODO: replace normals with transforms
def genFootRelativeConstraintsTalos(normals = [z, z]):
    res = [None, None]
    trLF = default_transform_from_pos_normal(zero3, normals[LF])
    trRF = default_transform_from_pos_normal(zero3, normals[RF])
    KLF = right_foot_in_lf_frame_talos_constraints  (trLF)
    KRF = left_foot_in_rf_frame_talos_constraints (trRF)    
    res [LF] = KLF #constraints of right foot in lf frame. Same idea as COM in lf frame
    res [RF] = KRF
    return res
    
def copyKin(kC):
    return [(Kk[0].copy(), Kk[1].copy()) for Kk in kC]
