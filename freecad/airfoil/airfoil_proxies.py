import os
import numpy as np

from freecad import app
import Part as part

from airfoil import Airfoil
from freecad.airfoil import RESOURCE_PATH


class AirfoilProxy(object):
    """
    A Proxy Object for an airfoil given by a path
    """
    def __init__(self, obj, fn=None):
        fn = fn or os.path.join(RESOURCE_PATH, "clark_y.dat")
        obj.addProperty("App::PropertyFile", "filename", "airfoil properties", "airfoil name")
        obj.Proxy = self
        self._airfoil  = None
        obj.filename = fn

    def get_airfoil(self, obj):
        if hasattr(self, "_airfoil") and self._airfoil:
            return self._airfoil
        else:
            self._airfoil = Airfoil.import_from_dat(obj.filename)
            return self._airfoil

    def get_name(self, obj):
        airfoil = self.get_airfoil(obj)
        return airfoil.name

    def execute(self, obj):
        airfoil = self.get_airfoil(obj)
        wire1 = part.makePolygon([app.Vector(*i, 0) for i in airfoil.coordinates])
        # wire2 = part.makePolygon([app.Vector(*i, 0) for i in airfoil.get_lower_data()])
        obj.Shape = wire1 # part.Wire([wire1, wire2])

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class JoukowskyProxy(AirfoilProxy):
    def __init__(self, obj, midpoint=-0.1+0.1j, numpoints:int=50):
        obj.addProperty("App::PropertyFloat", "real_part", "airfoil properties", "real part of complex number")
        obj.addProperty("App::PropertyFloat", "imag_part", "airfoil properties", "imaginary part of complex number")
        obj.addProperty("App::PropertyInteger", "numpoints", "airfoil properties", "number of coordiantes per side")
        obj.Proxy = self
        obj.real_part = midpoint.real
        obj.imag_part = midpoint.imag
        obj.numpoints = numpoints

    def get_airfoil(self, obj):
        return Airfoil.compute_joukowsky(obj.real_part + 1j * obj.imag_part, obj.numpoints * 2 + 1)


class TrefftzProxy(AirfoilProxy):
    def __init__(self, obj, midpoint=-0.1+0.1j, tau:float=0.05, numpoints:int=50):
        obj.addProperty("App::PropertyFloat", "real_part", "airfoil properties", "real part of complex number")
        obj.addProperty("App::PropertyFloat", "imag_part", "airfoil properties", "imaginary part of complex number")
        obj.addProperty("App::PropertyFloat", "tau", "airfoil properties", "trailing edge angle")
        obj.addProperty("App::PropertyInteger", "numpoints", "airfoil properties", "number of coordiantes per side")
        obj.Proxy = self
        obj.real_part = midpoint.real
        obj.imag_part = midpoint.imag
        obj.tau = tau
        obj.numpoints = numpoints

    def get_airfoil(self, obj):
        return Airfoil.compute_trefftz_kutta(obj.real_part + 1j * obj.imag_part, obj.tau, obj.numpoints * 2 +1)


class VandevoorenProxy(AirfoilProxy):
    def __init__(self, obj, tau:float=0.05, epsilon:float=0.05, numpoints:int=50):
        obj.addProperty("App::PropertyFloat", "tau", "airfoil properties", "trailing edge angle")
        obj.addProperty("App::PropertyFloat", "epsilon", "airfoil properties", "can't remeber this parameter")
        obj.addProperty("App::PropertyInteger", "numpoints", "airfoil properties", "number of coordiantes per side")
        obj.Proxy = self
        obj.tau = tau
        obj.epsilon = epsilon
        obj.numpoints = numpoints

    def get_airfoil(self, obj):
        return Airfoil.compute_vandevooren(obj.tau, obj.epsilon, obj.numpoints * 2 + 1)


class NacaProxy(AirfoilProxy):
    def __init__(self, obj, naca_digits:str="2412", numpoints:int=50):
        obj.addProperty("App::PropertyString", "naca_digits", "airfoil properties", "naca digits")
        obj.addProperty("App::PropertyInteger", "numpoints", "airfoil properties", "number of coordiantes per side")
        obj.Proxy = self
        obj.naca_digits = naca_digits
        obj.numpoints = numpoints

    def get_airfoil(self, obj):
        return Airfoil.compute_naca(obj.naca_digits, obj.numpoints)


class ParafoilProxy(Airfoil):
    """
    A NURBS representation of an airfoil. 
    """
    def __init__(self, obj):

        # defaulta airfoil
        upper_array = [
           [0.  , 0.  , 0.01, 0.07, 0.18, 0.36, 0.5 , 0.71, 1.  ],
           [0.  , 0.02, 0.05, 0.09, 0.1 , 0.08, 0.06, 0.04, 0.  ],
           [0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  ],
           [1.  , 1.  , 1  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  ]
           ]

        lower_array = [
           [ 0. , 0.  , 0.03, 0.1 , 0.31, 0.53, 0.71, 0.84, 1.  ],
           [ 0. ,-0.02,-0.04,-0.06,-0.07,-0.06,-0.04,-0.02, 0.  ],
           [ 0. , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  , 0.  ],
           [ 1. , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  , 1.  ]
           ]

        obj.addProperty("App::PropertyPythonObject", "upper_array", "airfoil properties", "x, y, z, w of upper poles")
        obj.addProperty("App::PropertyPythonObject", "lower_array", "airfoil properties", "x, y, z, w of lower poles")

        obj.upper_array = upper_array
        obj.lower_array = lower_array
        obj.Proxy = self

    def get_upper_array(self, obj):
        return np.array(obj.upper_array)

    def get_lower_array(self, obj):
        return np.array(obj.lower_array)

    @property
    def x_mapping(self):
        return [
            [0, 2], # x2
            [0, 3], # x3
            [0, 4], # x4
            [0, 5], # x5
            [0, 6], # x6
            [0, 7], # x7
            ]

    @property
    def y_mapping(self):
        return [
            [1, 1], # y1
            [1, 2], # y2
            [1, 3], # y3
            [1, 4], # y4
            [1, 5], # y5
            [1, 6], # y6
            [1, 7], # y7
        ]

    @property
    def w_mapping(self):
        return [
            [3, 1], # w1
            [3, 2], # w2
            [3, 3], # w3
            [3, 4], # w4
            [3, 5], # w5
            [3, 6], # w6
            [3, 7], # w7
        ]

    @staticmethod
    def _spline_from_mat(mat):
        """
        returns a FreeCAD NURBS object
        """
        additional_knots = [0., 1. / 3., 1. / 3., 2. / 3., 2. / 3., 1.]
        bs = part.BSplineCurve()
        bs.increaseDegree(4)
        for k in additional_knots:
            bs.insertKnot(k)
        i = 1
        for x, y, z, w in mat.T:
            bs.setPole(i, app.Vector(x, y, z))
            bs.setWeight(i, w)
            i += 1
        return bs


    def execute(self, obj):
        upper_array = self.get_upper_array(obj)
        lower_array = self.get_lower_array(obj)
        spline1 = self._spline_from_mat(upper_array)
        spline2 = self._spline_from_mat(lower_array)
        wire = part.Wire([spline1.toShape(), spline2.toShape()])
        obj.Shape = wire


    def _get_values(self, mapping, mat):
        """
        returns a flattened representation of all values which are allowed to be variated
        """
        values = []
        for m in mapping:
            values.append(mat[m[0]][m[1]])
        return np.array(values)

    def _set_values(self, mapping, mat, values):
        """
        sets values of mat by a flat vector of values (needs to have same length as mapping)
        """
        for i, m in enumerate(mapping):
            mat[m[0]][m[1]] = values[i]
        return mat


##### maybe externalize
    def _calibrate_one_side(self, start_mat, mapping, bounds, coordinates):
        from scipy.optimize import least_squares
        mat = start_mat

        def cost_function(values, mat, coordinates):
            mat = self._set_values(mapping, mat, values)
            spline = self._spline_from_mat(mat)
            edge = spline.toShape()
            residuals = []
            for x, y in coordinates:
                vertex = part.Vertex(x, y, 0.)
                dist = vertex.distToShape(edge)[0]
                residuals.append(dist)
            return residuals

        start_values = self._get_values(mapping, mat)
        best = least_squares(cost_function, start_values, bounds=bounds, method="dogbox", args=(mat, coordinates))
        mat = self._set_values(mapping, mat, best.x)
        return mat

    def calibrate(self, obj, airfoil:Airfoil, calibrate_x:bool=False, calibrate_y:bool=True, calibrate_w:bool=False):
        """
        calibrates the splines to match the airfoil as good as possible (lstsq)
        """
        x_lower_bounds = [0. ] * 6
        x_upper_bounds = [1. ] * 6
        y_lower_bounds = [-1.] * 7
        y_upper_bounds = [1. ] * 7
        w_lower_bounds = [0.1] * 7
        w_upper_bounds = [1.]  * 7
        upper_bounds = []
        lower_bounds = []
        mapping = []

        if calibrate_x:
            lower_bounds += x_lower_bounds
            upper_bounds += x_upper_bounds
            mpping += self.x_mapping
        if calibrate_y:
            lower_bounds += y_lower_bounds
            upper_bounds += y_upper_bounds
            mapping += self.y_mapping
        if calibrate_w:
            lower_bounds += w_lower_bounds
            upper_bounds += w_upper_bounds
            mapping += self.w_mapping

        bounds = (lower_bounds, upper_bounds)

        upper_array = obj.Proxy.get_upper_array(obj)
        lower_array = obj.Proxy.get_lower_array(obj)
        new_upper_mat = self._calibrate_one_side(upper_array, mapping, bounds, airfoil.get_upper_data()[::-1])
        new_lower_mat = self._calibrate_one_side(lower_array, mapping, bounds, airfoil.get_lower_data())
        obj.upper_array = new_upper_mat.tolist()
        obj.lower_array = new_lower_mat.tolist()

