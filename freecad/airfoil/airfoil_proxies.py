import os
import numpy as np
from scipy.interpolate import interp1d

from freecad import app
import FreeCADGui as gui
import Part as part

from airfoil import Airfoil, XfoilStudy
from freecad.airfoil import RESOURCE_PATH


class AirfoilProxy(object):
    """
    A Proxy Object for an airfoil given by a path
    """
    def __init__(self, obj, fn=None):
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

class LinkedAirfoilProxy(AirfoilProxy):
    def __init__(self, obj, parafoil, numpoints:int=50, curvature_factor:float=0.5):
        obj.addProperty("App::PropertyLink", "parafoil", "airfoil properties", "link to parafoil")
        obj.addProperty("App::PropertyInteger", "numpoints", "airfoil properties", "number of coordiantes per side")
        obj.addProperty("App::PropertyFloat", "curvature_factor", "airfoil properties", "0: const length, 1: fine at curvature")
        obj.parafoil = parafoil
        obj.numpoints = numpoints
        obj.curvature_factor = curvature_factor
        obj.Proxy = self

    def get_airfoil(self, obj):
        return obj.parafoil.Proxy.get_airfoil(obj.parafoil, obj.numpoints, obj.curvature_factor)


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
            [0.   , 0.   , 0.01 , 0.07 , 0.2  , 0.5  , 0.7  , 0.85 , 1.   ],
            [0.   , 0.011, 0.029, 0.05 , 0.082, 0.083, 0.051, 0.034, 0.   ],
            [0.   , 0.   , 0.   , 0.   , 0.   , 0.   , 0.   , 0.   , 0.   ],
            [1.   , 1.   , 1.   , 1.   , 1.   , 1.   , 1.   , 1.   , 1.   ]
            ]

        lower_array = [
            [ 0.   ,  0.   ,  0.01 ,  0.07 ,  0.2  ,  0.5  ,  0.7  ,  0.85 ,  1.   ],
            [ 0.   , -0.008, -0.022, -0.038, -0.046, -0.036, -0.021, -0.012,  0.   ],
            [ 0.   ,  0.   ,  0.   ,  0.   ,  0.   ,  0.   ,  0.   ,  0.   ,  0.   ],
            [ 1.   ,  1.   ,  1.   ,  1.   ,  1.   ,  1.   ,  1.   ,  1.   ,  1.   ]
            ]

        obj.addProperty("App::PropertyPythonObject", "upper_array", "airfoil properties", "x, y, z, w of upper poles")
        obj.addProperty("App::PropertyPythonObject", "lower_array", "airfoil properties", "x, y, z, w of lower poles")

        obj.upper_array = upper_array
        obj.lower_array = lower_array
        obj.Proxy = self

    def get_airfoil(self, obj, numpoints=50, curvature_factor=0.5):
        coordinates = self.discretize(obj, numpoints, curvature_factor)
        return Airfoil(coordinates)

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
        additional_knots = [0., 0.2, 0.4, 0.6, 0.8, 1.]
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

    def discretize(self, obj, numpoints=300, curvature_factor=1):
        """returns an Airfoil"""
        upper_spline = self._spline_from_mat(self.get_upper_array(obj))
        lower_spline = self._spline_from_mat(self.get_lower_array(obj))

        def compute_dist(spline):
            import matplotlib.pyplot as plt
            std_dist = np.linspace(0, 1, 1000)
            length = np.array([spline.length(0, i) for i in std_dist])
            length /= length[-1]


            curvature = np.array([0.] + [spline.curvature(i) for i in std_dist])[:-1]
            curvature = np.cumsum(curvature) 
            curvature /= curvature[-1]
            curvature = curvature * curvature_factor + std_dist * (1 - curvature_factor)
            curvature /= curvature[-1]

            length_int = interp1d(length, std_dist)
            curvature_int = interp1d(curvature, std_dist)
            plt.plot(std_dist, curvature_int(length_int(std_dist)))
            plt.show()
            std_dist = np.linspace(0, 1, numpoints)
            return curvature_int(length_int(std_dist))

        upper_dist = compute_dist(upper_spline)
        lower_dist = compute_dist(lower_spline)
        upper_points = [upper_spline.value(i) for i in upper_dist]
        lower_points = [lower_spline.value(i) for i in lower_dist]
        upper_points = [[i[0], i[1]] for i in upper_points]
        lower_points = [[i[0], i[1]] for i in lower_points]
        coordinates = upper_points[::-1] + lower_points[1:]
        return np.array(coordinates)


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
            if m == [1, 1]:
                # compute the corresponsing x-value
                x, y, z, w = mat.T[1]
                mat[0][1] = x * values[i] / y
                mat[1][1] = values[i]
            else:
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
        best = least_squares(cost_function, start_values, bounds=bounds, method="dogbox",
                             args=(mat, coordinates), gtol=1e-6, xtol=1e-6, verbose=2)
        mat = self._set_values(mapping, mat, best.x)
        return mat

    def calibrate(self, obj, airfoil:Airfoil, calibrate_x:bool=False, calibrate_y:bool=True, calibrate_w:bool=False):
        """
        calibrates the splines to match the airfoil as good as possible (lstsq)
        """
        mapping, lower_bounds_upper_spline, upper_bounds_upper_spline = self._get_bounds_and_mapping(calibrate_x, calibrate_y, calibrate_w, upper=True)
        mapping, lower_bounds_lower_spline, upper_bounds_lower_spline = self._get_bounds_and_mapping(calibrate_x, calibrate_y, calibrate_w, upper=False)
        bounds_upper_spline = (lower_bounds_upper_spline, upper_bounds_upper_spline)
        bounds_lower_spline = (lower_bounds_lower_spline, upper_bounds_lower_spline)

        upper_array = obj.Proxy.get_upper_array(obj)
        lower_array = obj.Proxy.get_lower_array(obj)
        new_upper_mat = self._calibrate_one_side(upper_array, mapping, bounds_upper_spline, airfoil.get_upper_data()[::-1])
        new_lower_mat = self._calibrate_one_side(lower_array, mapping, bounds_lower_spline, airfoil.get_lower_data())
        obj.upper_array = new_upper_mat.tolist()
        obj.lower_array = new_lower_mat.tolist()

    def _get_bounds_and_mapping(self, calibrate_x:bool=False, calibrate_y:bool=True, calibrate_w:bool=False, upper=True):
        x_lower_bounds = [0. ] * 6
        x_upper_bounds = [1. ] * 6
        y_lower_bounds = [-1.] * 7
        y_upper_bounds = [1. ] * 7
        w_lower_bounds = [0.1] * 7
        w_upper_bounds = [1.]  * 7
        if upper:
            y_lower_bounds[0] = 0
        else:
            y_upper_bounds[0] = 0
        upper_bounds = []
        lower_bounds = []
        mapping = []

        if calibrate_x:
            lower_bounds += x_lower_bounds
            upper_bounds += x_upper_bounds
            mapping += self.x_mapping
        if calibrate_y:
            lower_bounds += y_lower_bounds
            upper_bounds += y_upper_bounds
            mapping += self.y_mapping
        if calibrate_w:
            lower_bounds += w_lower_bounds
            upper_bounds += w_upper_bounds
            mapping += self.w_mapping
        return mapping, lower_bounds, upper_bounds


    def optimize(self, obj, target_function, optimize_x, optimize_y, optimize_w, numpoints=50):
        from scipy.optimize import least_squares
        mapping, lower_bounds_upper_spline, upper_bounds_upper_spline = self._get_bounds_and_mapping(optimize_x, optimize_y, optimize_w, upper=True)
        mapping, lower_bounds_lower_spline, upper_bounds_lower_spline = self._get_bounds_and_mapping(optimize_x, optimize_y, optimize_w, upper=False)

        bounds = (lower_bounds_upper_spline + lower_bounds_lower_spline, 
                  upper_bounds_upper_spline + upper_bounds_lower_spline)

        upper_array = obj.Proxy.get_upper_array(obj)
        lower_array = obj.Proxy.get_lower_array(obj)

        upper_start_values = self._get_values(mapping, upper_array)
        lower_start_values = self._get_values(mapping, lower_array)
        start_values = np.array(upper_start_values.tolist() + lower_start_values.tolist())

        def cost_function(values):
            upper_mat = self._set_values(mapping, upper_array, values[:int(len(values) / 2)])
            lower_mat = self._set_values(mapping, lower_array, values[int(len(values) / 2):])
            obj.upper_array = upper_mat.tolist()
            obj.lower_array = lower_mat.tolist()
            airfoil = self.get_airfoil(obj, numpoints)
            try:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
                residuals = target_function(airfoil)
            except Exception:
                return 1.  # return a high value
            return sum(residuals)
            
        best = least_squares(cost_function, start_values, bounds=bounds, method="dogbox",
                             gtol=1e-6, xtol=1e-7, verbose=2)
        return best



class AerodynamicsStudy(object):
    def __init__(self, obj, airfoil):
        obj.addProperty("App::PropertyLink", "airfoil", "group", "the foil which is analyzed")
        obj.addProperty("App::PropertyPythonObject", "data", "group", "data is stored in this table")
        obj.airfoil = airfoil
        obj.Proxy = self