import os
import copy
import numpy as np
from PySide import QtGui
from pivy import coin
from pivy import graphics

from freecad import app
import FreeCADGui as gui
import Part as part

from freecad.airfoil import RESOURCE_PATH

class ViewProviderAirfoil(object):
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(RESOURCE_PATH, "airfoil.svg")

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

class ViewProviderParafoil(object):
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(RESOURCE_PATH, "parafoil.svg")

    def setupContextMenu(self, view_obj, menu):
        action = menu.addAction("modify parafoil") # start an task 
        action.triggered.connect(lambda f=self.modify_parafoil, arg=view_obj.Object: f(arg))

    def modify_parafoil(self, obj):
        modifier = ParafoilModifier(obj)
        gui.Control.showDialog(modifier)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

class ConstrainedMarker(graphics.Marker):
    def __init__(self, points, weight, poles, pole_index, dynamic=False):
        super(ConstrainedMarker, self).__init__(points, dynamic)
        self.poles = poles
        self.pole_index = pole_index
        self.weight = weight

    @property
    def points(self):
        return self.data.point.getValues()

    @points.setter
    def points(self, points):
        point = [points[0][0], points[0][1], 0.]
        self.data.point.setValues(0, 1, [point])
        if hasattr(self, "poles"):
            self.poles.point[self.pole_index].setValue([*(np.array(point) * self.weight), self.weight])
            self.poles.point = self.poles.point

class ConstrainedXMarker(ConstrainedMarker):
    @property
    def points(self):
        return self.data.point.getValues()

    @points.setter
    def points(self, points):
        point = [0., points[0][1], 0.]
        self.data.point.setValues(0, 1, [point]) 
        if hasattr(self, "poles"):
            self.poles.point[self.pole_index].setValue([*(np.array(point) * self.weight), self.weight])
            self.poles.point = self.poles.point


class ParafoilModifier(object):
    def __init__(self, obj):
        self.obj = obj  # self.obj.Proxy --> parafoil_proxy
        self.form = []
        self.scene = gui.activeDocument().activeView().getSceneGraph()
        self.rm = gui.activeDocument().activeView().getViewer().getSoRenderManager()

        self.base_widget = QtGui.QWidget()
        self.form.append(self.base_widget)
        self.layout = QtGui.QFormLayout(self.base_widget)
        self.base_widget.setWindowTitle("parafoil modifier")

        # scene container
        self.task_separator = coin.SoSeparator()
        self.task_separator.setName('task_seperator')
        self.scene += self.task_separator
        self.spline_sep, self.upper_poles, self.lower_poles = self._get_bspline()
        self.task_separator += self.spline_sep

        upper_array = obj.Proxy.get_upper_array(obj)
        lower_array = obj.Proxy.get_lower_array(obj)
        upper_array_1 = copy.copy(upper_array)
        upper_array_1[:3] *= upper_array_1[3]
        lower_array_1 = copy.copy(lower_array)
        lower_array_1[:3] *= lower_array_1[3]
        self.upper_poles.point.setValues(0, 9, upper_array_1.T)
        self.lower_poles.point.setValues(0, 9, lower_array_1.T)
        self.interaction_sep = graphics.InteractionSeparator(self.rm)
        for i, mat in enumerate([upper_array, lower_array]):
            if i == 0:
                poles = self.upper_poles
            else:
                poles = self.lower_poles
            for j, col in enumerate(mat.T):
                if j in [0, 8]:
                    marker = graphics.Marker([col[:-1]], dynamic=False)
                elif (j == 1 and i == 0) or (j == 1 and i == 1):
                    marker = ConstrainedXMarker([col[:-1]], col[-1], poles, j, dynamic=True)
                else:
                    marker = ConstrainedMarker([col[:-1]], col[-1], poles, j, dynamic=True)
                self.interaction_sep += marker
        self.task_separator += self.interaction_sep
        self.interaction_sep.register()


    def _get_bspline(self):
        """
        returns a coin.SoNurbsCurve and the poles seperators
        set the pole-values by poels.point.setValues(0, 9, mat.tolist())
        """
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 2
        complexity = coin.SoComplexity()
        complexity.value = 0.5
        spline_sep = coin.SoSeparator()
        upper_sep = coin.SoSeparator()
        lower_sep = coin.SoSeparator()
        knot_vector = 5 * [0] + 2 * [1] + 2 * [2] + 5 * [3]
        upper_curve = coin.SoNurbsCurve()
        lower_curve = coin.SoNurbsCurve()
        upper_curve.knotVector.setValues(0, len(knot_vector), knot_vector)
        lower_curve.knotVector.setValues(0, len(knot_vector), knot_vector)
        upper_curve.numControlPoints = 9
        lower_curve.numControlPoints = 9
        upper_poles = coin.SoCoordinate4()
        lower_poles = coin.SoCoordinate4()

        # no need to set degree. Should be computed by numControlPoints and knotvector

        upper_sep += [draw_style, complexity, upper_poles, upper_curve]
        lower_sep += [draw_style, complexity, lower_poles, lower_curve]
        spline_sep += [upper_sep, lower_sep]
        return (spline_sep, upper_poles, lower_poles)


    def setup_pivy(self):
        # create 2 spline objects
        # create a modifier seperator
        # create interactive points
        pass

    def setup_qt(self):
        # create a table of inputs (x, y, w)
        # create input for te-gap
        pass


    def accept(self):
        self.scene -= self.task_separator
        upper_array = np.array([list(point) for point in self.upper_poles.point.getValues()]).T
        lower_array = np.array([list(point) for point in self.lower_poles.point.getValues()]).T
        upper_array[:3] /= upper_array[3]
        lower_array[:3] /= lower_array[3]
        self.obj.upper_array = upper_array.tolist()
        self.obj.lower_array = lower_array.tolist()
        app.activeDocument().recompute()

        gui.SendMsgToActiveView("ViewFit")
        gui.Control.closeDialog()

    def reject(self):
        self.scene -= self.task_separator
        gui.Control.closeDialog()
