import os
import math
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.interpolate import interp1d
from airfoil import Airfoil


import Part
import FreeCAD as App

def get_values(mapping, mat):
    values = []
    for m in mapping:
        values.append(mat[m[0]][m[1]])
    return np.array(values)

def set_values(mapping, mat, values):
    for i, m in enumerate(mapping):
        mat[m[0]][m[1]] = values[i]
    return mat

def create_spline(mat):
    """returns a FreeCAD NURBS object"""
    additional_knots = [0., 1. / 3., 1. / 3., 1. / 6., 1. / 6., 1.]
    bs = Part.BSplineCurve()
    bs.increaseDegree(4)
    for k in additional_knots:
        bs.insertKnot(k)
    i = 1
    for x, y, z, w in mat.T:
        bs.setPole(i, App.Vector(x, y, z))
        bs.setWeight(i, w)
        i += 1
    return bs


def calibration(start_mat, mapping, bounds, coordinates):
    mat = start_mat

    def cost_function(values, mat, coordinates):
        print(coordinates)
        mat = set_values(mapping, mat, values)
        spline = create_spline(mat)
        edge = spline.toShape()
        residuals = []
        for x, y in coordinates:
            vertex = Part.Vertex(x, y, 0.)
            dist = vertex.distToShape(edge)[0]
            residuals.append(dist)
        return residuals

    start_values = get_values(mapping, mat)
    best = least_squares(cost_function, start_values, bounds=bounds, method="dogbox", args=(mat, coordinates))
    mat = set_values(mapping, mat, best.x)
    return mat


def test(fn):
    import Part
    airfoil = Airfoil.import_from_dat(fn)
    # create upper and lower 0-spline
    xyzw1 = np.array(
          [[0.  , 0.  , 0.01, 0.07, 0.18, 0.36, 0.5 , 0.71, 1.  ],
           [0.  , 0.02, 0.05, 0.09, 0.1 , 0.08, 0.06, 0.04, 0.  ],
           [0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  ],
           [1.  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  ]])

    xyzw2 = np.array(
          [[ 0.  ,  0.  ,  0.03,  0.1 ,  0.31,  0.53,  0.71,  0.84,  1.  ],
           [ 0.  , -0.02, -0.04, -0.06, -0.07, -0.06, -0.04, -0.02,  0.  ],
           [ 0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ,  0.  ],
           [ 1.  ,  1.  ,  1.  ,  1.  ,  1.  ,  1.  ,  1.  ,  1.  ,  1.  ]])

    # create a mapping from vector of input to arrays
    mapping = [
        [0, 2], # x2
        [0, 3], # x3
        [0, 4], # x4
        [0, 5], # x5
        [0, 6], # x6
        [0, 7], # x7
        [1, 1], # y1
        [1, 2], # y2
        [1, 3], # y3
        [1, 4], # y4
        [1, 5], # y5
        [1, 6], # y6
        [1, 7], # y7
        [3, 1], # w1
        [3, 2], # w2
        [3, 3], # w3
        [3, 4], # w4
        [3, 5], # w5
        [3, 6], # w6
        [3, 7], # w7
    ]
    points = [Part.Vertex(*pnt, 0) for pnt in airfoil.coordinates]
    Part.show(Part.Compound(points))

    bounds = ([0.] * 6 + [-np.inf] * 7 + [0.1] * 7, [1.] * 6 + [np.inf] * 7 + [1.] * 7)
    new_upper_mat = calibration(xyzw1, mapping, bounds, airfoil.get_upper_data()[::-1])
    new_lower_mat = calibration(xyzw2, mapping, bounds, airfoil.get_lower_data())
    Part.show(create_spline(new_upper_mat).toShape())
    Part.show(create_spline(new_lower_mat).toShape())