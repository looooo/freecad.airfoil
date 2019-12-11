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
        self.obj.ViewObject.hide()
        self.form = []
        self.scene = gui.activeDocument().activeView().getSceneGraph()
        self.rm = gui.activeDocument().activeView().getViewer().getSoRenderManager()

        # widget for modification
        self.base_widget = QtGui.QWidget()
        self.form.append(self.base_widget)
        self.layout = QtGui.QFormLayout(self.base_widget)
        self.base_widget.setWindowTitle("modifier")

        # widget for calibration
        self.calibration_widget = QtGui.QWidget()
        self.form.append(self.calibration_widget)
        self.calibration_layout = QtGui.QFormLayout(self.calibration_widget)
        self.calibration_widget.setWindowTitle("calibration")

        self.setup_qt()
        self.setup_pivy()

    def setup_qt(self):
        # create checkboxes: x, y, w
        self.q_calibrate_x = QtGui.QCheckBox("calibrate x-values")
        self.q_calibrate_y = QtGui.QCheckBox("calibrate y-values")
        self.q_calibrate_w = QtGui.QCheckBox("calibrate weights")

        self.q_calibrate_y.setChecked(True)

        # create button calibrate
        self.q_run = QtGui.QPushButton("run")
        self.q_run.clicked.connect(self._calibrate)

        self.layout.addWidget(self.q_calibrate_x)
        self.layout.addWidget(self.q_calibrate_y)
        self.layout.addWidget(self.q_calibrate_w)
        self.layout.addWidget(self.q_run)


    def setup_pivy(self):
        # scene container
        self.task_separator = coin.SoSeparator()
        self.task_separator.setName('task_seperator')
        self.scene += self.task_separator
        self.spline_sep, self.upper_poles, self.lower_poles = self._get_bspline()
        self.task_separator += self.spline_sep
        self.setup_bspline()


    def setup_bspline(self):
        # create a new interaction seperator
        if hasattr(self, "interaction_sep"):
            self.interaction_sep.unregister()
            self.task_separator -= self.interaction_sep
        self.interaction_sep = graphics.InteractionSeparator(self.rm)

        upper_array = self.obj.Proxy.get_upper_array(self.obj)
        lower_array = self.obj.Proxy.get_lower_array(self.obj)

        upper_array_1 = copy.copy(upper_array)
        upper_array_1[:3] *= upper_array_1[3]
        lower_array_1 = copy.copy(lower_array)
        lower_array_1[:3] *= lower_array_1[3]
        self.upper_poles.point.setValues(0, 9, upper_array_1.T)
        self.lower_poles.point.setValues(0, 9, lower_array_1.T)
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


    def _calibrate(self):
        from freecad.airfoil import commands
        selection = gui.Selection.getSelection()
        assert len(selection) == 1
        other_foil = selection[0]
        upper_array_temp = self.obj.upper_array
        lower_array_temp = self.obj.lower_array
        self.set_parafoil_from_current()
        if self.q_calibrate_x.isChecked() or self.q_calibrate_y.isChecked() or self.q_calibrate_w.isChecked():
            commands.calibrate_parafoil(self.q_calibrate_x.isChecked(), 
                                        self.q_calibrate_y.isChecked(), 
                                        self.q_calibrate_w.isChecked(),
                                        self.obj, other_foil)

        # set the poles of the coin bspline
        self.setup_bspline()
        
        # reset the poles of the freecad object (parafoil)
        self.obj.upper_array = upper_array_temp
        self.obj.lower_array = lower_array_temp
        app.activeDocument().recompute()


    def set_parafoil_from_current(self):
        upper_array = np.array([list(point) for point in self.upper_poles.point.getValues()]).T
        lower_array = np.array([list(point) for point in self.lower_poles.point.getValues()]).T
        upper_array[:3] /= upper_array[3]
        lower_array[:3] /= lower_array[3]
        self.obj.upper_array = upper_array.tolist()
        self.obj.lower_array = lower_array.tolist()


    def accept(self):
        self.scene -= self.task_separator
        self.set_parafoil_from_current()
        app.activeDocument().recompute()
        self.obj.ViewObject.show()
        gui.SendMsgToActiveView("ViewFit")
        gui.Control.closeDialog()

    def reject(self):
        self.scene -= self.task_separator
        self.obj.ViewObject.show()
        gui.Control.closeDialog()
