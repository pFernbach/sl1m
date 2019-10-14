import numpy as np

from constants_and_tools import *

from hpp_centroidal_dynamics import *
from hpp_spline import *
from numpy import array, asmatrix, matrix, zeros, ones
from numpy import array, dot, stack, vstack, hstack, asmatrix, identity, cross, concatenate
from numpy.linalg import norm

from scipy.spatial import ConvexHull
from hpp_bezier_com_traj import *
#~ from qp import solve_lp

import eigenpy
import cdd
from curves import bezier3
from random import random as rd
from random import randint as rdi
from numpy import squeeze, asarray
from cwc_qhull import compute_CWC

eigenpy.switchToNumpyArray()



def ineqFromCdata(cData):
    (H, h) = cData.contactPhase_.getPolytopeInequalities()
    return (-H, h)


def quasi_flat(P):
    aPmin = [ array(p[:2] + [-1])  for p in P]
    aPmax = [ array(p[:2] + [3 ])  for p in P]
    hull = ConvexHull(array(aPmin + aPmax))
    return ineqQHull(hull)

def staticEquilirium3DPolytopeQHull(cData, P, N):
    m = cData.contactPhase_.getMass()
    #~ #get 6D polytope
    #~ (H, h) = ineqFromCdata(cData)
    (H,h) = compute_CWC(array(P),array(N), {'mass' : m, 'g': g, 'mu':mu})
    
    #project to the space where aceleration is 0
    # see icra 16 paper, Del Prete et al.
    D = zeros((6,3))
    D[3:,:] = m * gX
    
    d = zeros((6,))
    d[:3] = -m * g
    
    A =     H.dot(D)
    b = h.reshape((-1,)) - H.dot(d)    
    
    #~ A, b = quasi_flat(P)
    
    plot_polytope_H_rep(A,b.reshape((-1,1)))
    
    #add kinematic polytope
    (K,k) = (cData.Kin_[0], cData.Kin_[1].reshape(-1,))
    
    resA = vstack([A, K])
    resb = concatenate([b, k]).reshape((-1,1))
    
    #DEBUG
    allpts = generators(resA,resb)[0]
    error = False
    for pt in allpts:
        #~ print "pt ", pt
        assert (resA.dot(pt.reshape((-1,1))) - resb).max() <0.001, "antecedent point not in End polytope"  + str((resA.dot(pt.reshape((-1,1))) - resb).max())
        #~ if (H.dot(w(m,pt).reshape((-1,1))) - h).max() > 0.001:
            #~ error = True
            #~ print "antecedent point not in End polytope"  + str((H.dot(w(m,pt).reshape((-1,1))) - h).max())
    assert not error, str (len(allpts))
    
    return (resA, resb)


def staticEquilirium3DPolytope(cData):
    m = cData.contactPhase_.getMass()
    #~ #get 6D polytope
    (H, h) = ineqFromCdata(cData)
    #project to the space where aceleration is 0
    # see icra 16 paper, Del Prete et al.
    D = zeros((6,3))
    D[3:,:] = m * gX
    
    d = zeros((6,))
    d[:3] = -m * g
    
    A =     H.dot(D)
    b = h.reshape((-1,)) - H.dot(d)    
    #add kinematic polytope
    (K,k) = (cData.Kin_[0], cData.Kin_[1].reshape(-1,))
    
    resA = vstack([A, K])
    resb = concatenate([b, k]).reshape((-1,1))
    
    #DEBUG
    allpts = generators(resA,resb)[0]
    error = False
    for pt in allpts:
        #~ print "pt ", pt
        assert (resA.dot(pt.reshape((-1,1))) - resb).max() <0.001, "antecedent point not in End polytope"  + str((resA.dot(pt.reshape((-1,1))) - resb).max())
        if (H.dot(w(m,pt).reshape((-1,1))) - h).max() > 0.001:
            error = True
            print "antecedent point not in End polytope"  + str((H.dot(w(m,pt).reshape((-1,1))) - h).max())
    assert not error, str (len(allpts))
    
    return (resA, resb)
    #~ return (A, b)
    #~ return (vstack([A, K]), None)



def IdZero63(TT):
    res = zeros((6,3))    
    res[:3,:] = identity(3) / TT
    return res
    
def zero6():
    return zeros((6,1))
    
# TODO acceleration constraints
#~ def antecedant(p0, cDataEnd, cDataFrom, T, projectToKinematicConstraints = True):
def antecedant(p0, cDataEnd, cDataFrom, T, projectToKinematicConstraints = True, maxAcc = 10.):
    dim = 3
    m = cDataEnd.contactPhase_.getMass()
    (HEnd, hEnd)   = ineqFromCdata(cDataEnd)
    (HFrom, hFrom) = ineqFromCdata(cDataFrom)
    HEnd  = m * HEnd 
    HFrom = m * HFrom
    hFrom =  hFrom + HFrom.dot(g6).reshape((-1,1))
    hEnd  =  hEnd + HEnd.dot(g6).reshape((-1,1))
    
    #now for the wrench control points:
    TT = T * T
    p0TT = p0 / TT
    p0X = skew(p0)
    p0XTT = p0X / TT
    gXp0 = gX.dot(p0)
    temp_wy = IdZero63(TT)
    ##w0
    w0y = temp_wy * 6
    w0y[3:,:] = gX  + 6* p0XTT
    w0c = zero6(); w0c[:3,0] = -6 * p0TT
    
    ##w1
    w1y = temp_wy * 4
    w1y[3:,:] = 4* p0XTT
    w1c = zero6(); 
    w1c[:3,0] = -4 * p0TT
    w1c[3:,0] = gXp0
    
    ##w2
    #~ w2y = temp_wy * 2
    #~ w2y[3:,:] = 2* p0XTT
    #~ w2c = zero6(); 
    #~ w2c[:3,0] = -2 * p0TT
    #~ w2c[3:,0] = gXp0
    
            
    #now for inequalities:
    #w1 and w2 belong to cDataFrom, and w0 must belong to cDataEnd
    
    HERows  =  HEnd.shape[0] 
    HFRows  =  HFrom.shape[0] 
    
    #~ numrows = HERows + HFRows *2
    numrows = HERows + HFRows
    A = zeros((numrows, dim))
    b = zeros((numrows,1))
    
    A[:HERows]              =          HEnd.dot(w0y)
    b[:HERows]              = hEnd  -  HEnd.dot(w0c)
    
    #~ A[HERows:HERows+HFRows] =         HFrom.dot(w1y)
    #~ b[HERows:HERows+HFRows] = hFrom - HFrom.dot(w1c)
    A[HERows:] =         HFrom.dot(w1y)
    b[HERows:] = hFrom - HFrom.dot(w1c)
    
    #~ A[-HFRows:]             =         HFrom.dot(w2y)
    #~ b[-HFRows:]             = hFrom - HFrom.dot(w2c)
    
    if projectToKinematicConstraints:
        # TODO check that the good constraints are considered (in theory intesection is required)
        (K,k) = (cDataFrom.Kin_[0], cDataFrom.Kin_[1])
        A = vstack([A, K])
        b = concatenate([b, k]).reshape((-1,1))
        
        #now canonicalize
        #~ A, b = canon(A, b)
        
    #DEBUG
    assert (A.dot(p0).reshape((-1,1)) - b).max() < 0.000001, "p0 not in antecedent " + str((A.dot(p0).reshape((-1,1)) - b).max())
    
    if maxAcc is not None:
        #bound acceleration
        #init acceleration is enough
        # [6*(-p0 + y)/T**2, 0] => 6*(-p0 + y)/T**2 <= maxAcc, sixTT = 6/ T**2
        # sixTT * y <= maxAcc + sixTT * p0
        sixTT = 6 / TT
        Acc = zeros((6,dim)); bcc = zeros((6,1))
        Acc[:3,:3]  =  identity(3) * sixTT
        bcc[:3,0 ]  = p0 * sixTT + ones(3) * maxAcc
        Acc[3:,:3]  =  - Acc[:3,:3]
        bcc[3:,0 ]  = bcc[:3,0 ]
        #~ print ""
        A = vstack([A, Acc])
        b = concatenate([b, bcc]).reshape((-1,1))
        
    return (A,b)
    
def antecedant(p0, cDataEnd, cDataFrom, T, projectToKinematicConstraints = True, maxAcc = 10.):
    dim = 3
    m = cDataEnd.contactPhase_.getMass()
    (HEnd, hEnd)   = ineqFromCdata(cDataEnd)
    (HFrom, hFrom) = ineqFromCdata(cDataFrom)
    HEnd  = m * HEnd 
    HFrom = m * HFrom
    hFrom =  hFrom + HFrom.dot(g6).reshape((-1,1))
    hEnd  =  hEnd + HEnd.dot(g6).reshape((-1,1))
    
    #now for the wrench control points:
    TT = T * T
    p0TT = p0 / TT
    p0X = skew(p0)
    p0XTT = p0X / TT
    gXp0 = gX.dot(p0)
    temp_wy = IdZero63(TT)
    ##w0
    w0y = temp_wy * 6
    w0y[3:,:] = gX  + 6* p0XTT
    w0c = zero6(); w0c[:3,0] = -6 * p0TT
    
    ##w1
    w1y = temp_wy * 4
    w1y[3:,:] = 4* p0XTT
    w1c = zero6(); 
    w1c[:3,0] = -4 * p0TT
    w1c[3:,0] = gXp0
    
    ##w2
    #~ w2y = temp_wy * 2
    #~ w2y[3:,:] = 2* p0XTT
    #~ w2c = zero6(); 
    #~ w2c[:3,0] = -2 * p0TT
    #~ w2c[3:,0] = gXp0
    
            
    #now for inequalities:
    #w1 and w2 belong to cDataFrom, and w0 must belong to cDataEnd
    
    HERows  =  HEnd.shape[0] 
    HFRows  =  HFrom.shape[0] 
    
    #~ numrows = HERows + HFRows *2
    numrows = HERows + HFRows
    A = zeros((numrows, dim))
    b = zeros((numrows,1))
    
    A[:HERows]              =          HEnd.dot(w0y)
    b[:HERows]              = hEnd  -  HEnd.dot(w0c)
    
    #~ A[HERows:HERows+HFRows] =         HFrom.dot(w1y)
    #~ b[HERows:HERows+HFRows] = hFrom - HFrom.dot(w1c)
    A[HERows:] =         HFrom.dot(w1y)
    b[HERows:] = hFrom - HFrom.dot(w1c)
    
    #~ A[-HFRows:]             =         HFrom.dot(w2y)
    #~ b[-HFRows:]             = hFrom - HFrom.dot(w2c)
    
    if projectToKinematicConstraints:
        # TODO check that the good constraints are considered (in theory intesection is required)
        (K,k) = (cDataFrom.Kin_[0], cDataFrom.Kin_[1])
        A = vstack([A, K])
        b = concatenate([b, k]).reshape((-1,1))
        
        #now canonicalize
        #~ A, b = canon(A, b)
        
    #DEBUG
    assert (A.dot(p0).reshape((-1,1)) - b).max() < 0.000001, "p0 not in antecedent " + str((A.dot(p0).reshape((-1,1)) - b).max())
    
    if maxAcc is not None:
        #bound acceleration
        #init acceleration is enough
        # [6*(-p0 + y)/T**2, 0] => 6*(-p0 + y)/T**2 <= maxAcc, sixTT = 6/ T**2
        # sixTT * y <= maxAcc + sixTT * p0
        sixTT = 6 / TT
        Acc = zeros((6,dim)); bcc = zeros((6,1))
        Acc[:3,:3]  =  identity(3) * sixTT
        bcc[:3,0 ]  = p0 * sixTT + ones(3) * maxAcc
        Acc[3:,:3]  =  - Acc[:3,:3]
        bcc[3:,0 ]  = bcc[:3,0 ]
        #~ print ""
        A = vstack([A, Acc])
        b = concatenate([b, bcc]).reshape((-1,1))
        
    return (A,b)
    
    
# TODO acceleration constraints

def antecedant6D(p0, cDataEnd, cDataFrom, T, projectToKinematicConstraints = True, maxAcc = 10.):
#~ def antecedant6D(p0, cDataEnd, cDataFrom, T, projectToKinematicConstraints = True, maxAcc = None):
    dim = 6
    m = cDataEnd.contactPhase_.getMass()
    (HEnd, hEnd)   = ineqFromCdata(cDataEnd)
    (HFrom, hFrom) = ineqFromCdata(cDataFrom)
    HEnd  = m * HEnd 
    HFrom = m * HFrom
    hFrom =  hFrom + HFrom.dot(g6).reshape((-1,1))
    hEnd  =  hEnd + HEnd.dot(g6).reshape((-1,1))
    
    #now for the wrench control points:
    TT = T * T
    p0TT = p0 / TT
    p0X = skew(p0)
    p0XTT = p0X / TT
    gXp0 = gX.dot(p0)
    temp_wy = IdZero63(TT)
    ##w0
    w0y = temp_wy * 6
    w0y[3:,:] = gX  + 6* p0XTT
    w0c = zero6(); w0c[:3,0] = -6 * p0TT
    
    ##w1
    w1y = temp_wy * 4
    w1y[3:,:] = 4* p0XTT
    w1c = zero6(); 
    w1c[:3,0] = -4 * p0TT
    w1c[3:,0] = gXp0
    
    ##w2
    #~ w2y = temp_wy * 2
    #~ w2y[3:,:] = 2* p0XTT
    #~ w2c = zero6(); 
    #~ w2c[:3,0] = -2 * p0TT
    #~ w2c[3:,0] = gXp0
    
            
    #now for inequalities:
    #w1 and w2 belong to cDataFrom, and w0 must belong to cDataEnd
    
    HERows  =  HEnd.shape[0] 
    HFRows  =  HFrom.shape[0] 
    
    #~ numrows = HERows + HFRows *2
    numrows = HERows + HFRows
    A = zeros((numrows, dim))
    b = zeros((numrows,1))
    
    A[:HERows, :3]   =          HEnd.dot(w0y)
    b[:HERows]       = hEnd  -  HEnd.dot(w0c)
    
    A[HERows:, :3]   =         HFrom.dot(w1y)
    b[HERows:]       = hFrom - HFrom.dot(w1c)
    
    #~ A[-HFRows:]             =         HFrom.dot(w2y)
    #~ b[-HFRows:]             = hFrom - HFrom.dot(w2c)
    
    
    if projectToKinematicConstraints:
        # TODO check that the good constraints are considered (in theory intesection is required)
        (K,k) = (cDataFrom.Kin_[0], cDataFrom.Kin_[1])
        A = vstack([A, hstack([K,zeros((K.shape[0],3))])])
        b = concatenate([b, k]).reshape((-1,1))
        
        #now canonicalize
        #~ A, b = canon(A, b)
        
    if maxAcc is not None:
        #bound acceleration
        #init acceleration is enough
        # [6*(-p0 + y)/T**2, 0] => 6*(-p0 + y)/T**2 <= maxAcc, sixTT = 6/ T**2
        # sixTT * y <= maxAcc + sixTT * p0
        sixTT = 6 / TT
        Acc = zeros((6,dim)); bcc = zeros((6,1))
        Acc[:3,:3]  =  identity(3) * sixTT
        bcc[:3,0 ]  = p0 * sixTT + ones(3) * maxAcc
        Acc[3:,:3]  =  - Acc[:3,:3]
        bcc[3:,0 ]  = bcc[:3,0 ]
        #~ print ""
        A = vstack([A, Acc])
        b = concatenate([b, bcc]).reshape((-1,1))
        
    #DEBUG
    #~ assert (A.dot(p0).reshape((-1,1)) - b).max() < 0.000001, "p0 not in antecedent " + str((A.dot(p0).reshape((-1,1)) - b).max())
    #adding equality constraints
    
    n = 3.
    beta = p0
    alpha = T / n 
    Aeq = zeros((3,dim))
    Aeq[:,:3]   =  identity(3)
    Aeq[:,3:]   =  identity(3) * alpha
    beq = p0.reshape((-1,1))
    
    #directly create polytope
            
    return generators(A,b, Aeq, beq)[0]



def genPol6DFrom3DReachabilitySet(p0, pts, T):
    #~ pts = [zeros(3) for _ in range(100)]
    def fun(pt):
        res = zeros((6,))
        res[:3] = pt[:]
        res[3:] = getCrocBackward(pt,p0,p0,p0, T)[1]
        return res
    #~ print (pts.shape)
    pts6 = [fun(p) for p in pts]
    #~ pts6 = [zeros((6,)) for p in pts]
    return pts6

def centroid(pts):
    return sum([array(pt) for pt in pts]) / float(len(pts))

def findIntermediateContactPhase(phase1, phase2):
    keys = phase1.keys() 
    assert phase1.keys() == phase2.keys()
    res = {}
    for k,v in phase1.iteritems():
        if norm(centroid(v[0]) - centroid(phase2[k][0])) < 0.01:
            res[k] = v
    return res
            

def genIntermediateContactPhases(contacts):
    res = []
    for i, contact in enumerate(contacts[:-1]):
        nContact = contacts[i+1]
        res += [contact, findIntermediateContactPhase(contact,nContact)]
    res += [contacts[-1]]
    return res
        
from hpp.corbaserver.rbprm.hrp2 import Robot
from cPickle import load
def loadContactPhases(filename='./data/contacts_plateformes_dic.txt'):    
    f = open(filename,'r')
    contacts = load(f)
    f.close()
    #TODO FIX FIRST PHASE
    contacts[0][Robot.lLegId] = contacts[1][Robot.lLegId]
    allContacts = genIntermediateContactPhases(contacts)
    return allContacts

def ContactPhase(contacts, phaseId, pD, addToPlan = True):    
    contact = contacts[phaseId]

    P = []
    N = []
    Kin = zeros((0,3))
    kin = zeros(0)
    
    print "phase  ", phaseId
    
    if contact.has_key(rLeg):
        print "right"
        PR = contact[rLeg][0]
        NR = contact[rLeg][1]
        P += PR
        N += NR
        tr = default_transform_from_pos_normal(centroid(PR),NR[0])
        KinR,kinR = right_foot_hrp2_constraints(tr)
        Kin =  vstack([Kin,KinR])
        kin =  concatenate([kin, kinR])
        
    if contact.has_key(lLeg):
        PL = contact[lLeg][0]
        NL = contact[lLeg][1]
        P += PL
        N += NL
        tl = default_transform_from_pos_normal(centroid(PL),NL[0])
        KinL,kinL = left_foot_hrp2_constraints(tl)
        Kin =  vstack([Kin,KinL])
        kin =  concatenate([kin, kinL])
        
    #~ P = array(PR + PL) 
    #~ N = array(NR + NL) 
    
    #~ tr = default_transform_from_pos_normal(centroid(PR),NR[0])
    #~ KinR,kinR = right_foot_hrp2_constraints(tr) 
    #~ tl = default_transform_from_pos_normal(centroid(PL),NL[0])
    #~ KinL,kinL = left_foot_hrp2_constraints(tl) 
    
    cData0 = ContactData(Equilibrium("test", 55.88363633, 4, SOLVER_LP_QPOASES, True, 10, False))
    cData0.contactPhase_.setNewContacts(array(P), array(N), mu, EquilibriumAlgorithm.EQUILIBRIUM_ALGORITHM_PP)
    cData0.setKinematicConstraints(matrix(Kin), matrix(kin).T)
    if addToPlan:
        pD.addContact(cData0)
    return cData0, P, N, Kin, kin

if __name__ == '__main__':
    
    
    import time
    contacts = loadContactPhases()
    from hpp.corbaserver.rbprm.hrp2 import Robot
    
    from plot_plytopes import *
    rLeg = Robot.rLegId
    lLeg = Robot.lLegId
    #contact data from platform scenario


    #TODO make sure constraints associated to right leg and orientation

    pD = ProblemData()
    #~ pD.flag_ = ConstraintFlag.INIT_POS

    phaseId = 0
    cData0, P0, N0, K0, k0 = ContactPhase(contacts, phaseId, pD)
    
    
    phaseId = 1
    cData1, P1, N1, K1, k1 = ContactPhase(contacts, phaseId, pD)
    
    phaseId = 2
    cData2, P2, N2, K2, k2 = ContactPhase(contacts, phaseId, pD, False)
    N2 = [[0., 0., 1.] for _ in range(8)]
    
    
    #~ cData0 = ContactData(Equilibrium("test", 54., 4, SOLVER_LP_QPOASES, True, 10, True))
    #~ cData0.contactPhase_.setNewContacts(array(P0.tolist() + P1.tolist()), array(N0.tolist() + N1.tolist()), 0.3, EquilibriumAlgorithm.EQUILIBRIUM_ALGORITHM_PP)
    #~ cData0.setKinematicConstraints(matrix(vstack([Kin,Kin1])), matrix(concatenate([kin, kin1])).T)
    #~ pD.addContact(cData0)
    
    
    #~ cData1 = ContactData(Equilibrium("test", 54., 4, SOLVER_LP_QPOASES, True, 10, True))
    #~ cData1.contactPhase_.setNewContacts(array(P0.tolist()), array(N0.tolist()), 0.3, EquilibriumAlgorithm.EQUILIBRIUM_ALGORITHM_PP)
    #~ cData1.setKinematicConstraints(matrix(Kin), matrix(kin).T)
    #~ pD.addContact(cData1)
    
    
    #~ sId = 1
    #~ P0 = array(contacts[sId][0][:4])
    #~ P1 = array(contacts[sId][0][4:])
    #~ N0 = array(contacts[sId][1][:4])
    #~ N1 = array(contacts[sId][1][4:])
    #~ cData2 = ContactData(Equilibrium("test", 54., 4, SOLVER_LP_QPOASES, True, 10, True))
    #~ cData2.contactPhase_.setNewContacts(array(P0.tolist() + P1.tolist()), array(N0.tolist() + N1.tolist()), 0.3, EquilibriumAlgorithm.EQUILIBRIUM_ALGORITHM_PP)
    #~ cData2.setKinematicConstraints(matrix(vstack([Kin,Kin1])), matrix(concatenate([kin, kin1])).T)
    #~ pD.addContact(cData2)

    #~ print "HEO"

    #~ (H, h) = cData0.contactPhase_.getPolytopeInequalities()
    #~ plot_polytope_H_rep(H, h.reshape((-1,1))) 
    #~ plot_polytope_H_rep(K2, k2.reshape((-1,1)), color="v") 
    #~ plot_polytope_V_rep(P2) 

    (A,b) = staticEquilirium3DPolytope(cData0)
    #~ (A,b) = staticEquilirium3DPolytopeQHull(cData2,P2, N2)
    #~ plt.show()
    
    #~ plt.show()
    

    #try to plot antecedant
    hull, pts0, apts, H = genPolytope(A,b)
    plot_hull(hull, pts0, apts, color = "r", just_pts = False)
    #~ plot_polytope_H_rep(A,b.reshape((-1,1)))
    plt.show()  

        
    allpts   = []
    #~ allpts6D = [vec3to6(pt) for pt in pts0]
    allpts6D = []

    T = .5
    t0 = time.clock()
    maxnpts = 0
    kl = 0
    for i, p0 in enumerate(pts0):
        i += 1
        allpts6D += [vec3to6(p0)]
        #~ if i%12 == 0 and i < 20:
        if True:
            kl += 1
            print "kl ", kl
            
        
            #6D version
            #~ npts6D = antecedant6D(p0, cData0, cData0, T)
            #~ allpts6D += npts6D
            
            #3D version
            (antA, antb) = antecedant(p0, cData0, cData0, T, maxAcc = None)
            npts = generators(antA,antb)[0]               
            allpts += npts
            if len(npts) >0:
                print "npts ", len(npts)
                npts6D = genPol6DFrom3DReachabilitySet(p0, npts, T)
                allpts6D += npts6D
            
    #~ respt = []
    #~ skip = False
    #~ for i, pt in enumerate (allpts6D):
        #~ skip = False
        #~ for pt2 in allpts6D[i+1:]:
            #~ if norm(pt[:3]-pt2[:3]) < 0.04 and norm(pt[3:]) < norm(pt2[3:]):
                #~ skip = True
                #~ pass
        #~ if not skip:
            #~ respt += [pt]

    #~ print "len allpts6D", len(allpts6D)
    #~ print "len respt", len(respt)


    #~ allpts6D = respt

    #~ pts2 = [pt[3:] for pt in allpts6D]
    #~ hull = ConvexHull(pts2, qhull_options='Qx Q12 Qs A0.99 C0.05 W0.05')
    #~ hull = ConvexHull(pts2, qhull_options='Qx Q12 Qs A0.99 C0.05 W0.05')
    #~ hull = ConvexHull(allpts6D, qhull_options='Qx Q12 C0.05 W0.05')
    #~ hull = ConvexHull(allpts6D, qhull_options='Qx Q12 C0.05')
    #~ print "len allpts", len(allpts6D)
    hull = ConvexHull(allpts6D, qhull_options='Qx Q12')
    #~ hull = ConvexHull(allpts6D, qhull_options='Q12')

    #~ filterpts = [pts2[i] for i in hull.vertices.tolist()]
    filterpts = [allpts6D[i] for i in hull.vertices.tolist()]
    #~ print "num pts ", len(filterpts)
    #~ A,b = ineq(allpts6D, False)
    A,b = ineqQHull(hull)
    t1 = time.clock()
    print "time ", (t1 - t0) * 1000.
    #~ plot_polytope_H_rep(A,b.reshape((-1,1)))
    #~ filterpts = [allpts6D[i] for i in hull.vertices.tolist()]

    print "lendiff ", len(allpts6D) - len(filterpts), len(filterpts)


    #~ A,b = ineq(filterpts, False)
    print "num ineq", b.shape

    print "Done with one step approach (qhull) in (ms): ", (t1 - t0) * 1000
    #~ plot_hull(hull, allpts6D, array(allpts6D), color = "r", just_pts = False)

    plot_polytope_V_rep(filterpts  , color = "r", just_pts = False)
    plot_polytope_V_rep([pt[3:] for pt in  filterpts] , color = "r", just_pts = False)
    plt.show()
    #~ plot_polytope_V_rep([pt[3:] for pt in filterpts]  , color = "r", just_pts = False)
    #~ plot_hull(hull, allpts6D, array(allpts6D), color = "r", just_pts = False)

    #~ plot_polytope_V_rep(allpts  , color = "r", just_pts = False)
    #~ plot_polytope_V_rep(allpts6D, color = "r", just_pts = False)
        
    #~ for p0 in pts0:
        #~ (antA, antb) = antecedant(p0, cData0, cData0, T = 1., projectToKinematicConstraints = True)
        #~ allpts += generators(antA,antb)[0]
        #~ allpts6D += genPol6DFrom3DReachabilitySet(p0, antA, antb, T)
        
        
    #check convexity
    #~ A2,b2 = ineq(allpts1, True)
    #~ for pt in pts0:
        #~ if not (A2.dot(pt) - b2).max() <= 0.001:
            #~ print str((A2.dot(pt) - b2).max())
        
    #~ plot_polytope_V_rep(allpts, color = "r", just_pts = False)
    plt.show()


    print "what takes most time is: vertex enumeration for computing previous states, final convex hull"
    print "It seems a little bit faster to compute antecedant state in 3D and then map it back to 6D than calling antecedant6D"
    print "Adding acceleration constraints does not seem to help a lot"
    print "Only select a few points in the static equilibrium case does help a lot too"
    
    #trying to compute CROC with all this:
    
    c = Constraints()
    c.flag_ = ConstraintFlag.INIT_POS | ConstraintFlag.INIT_VEL
    pD.constraints_.flag_
    
    startCOM = [1.059490164244322, 0.25000237362450967, 0.7522584665645766]
    pD.c0_ = matrix(startCOM).T
