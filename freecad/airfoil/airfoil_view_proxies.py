import os
import copy
import numpy as np
from PySide import QtGui
from pivy import coin
from pivy import graphics, utils

from freecad import app
import FreeCADGui as gui
import Part as part

from freecad.airfoil import RESOURCE_PATH
from freecad.airfoil import airfoil_proxies


class ViewProviderAirfoil(object):
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(RESOURCE_PATH, "airfoil.svg")

    def setupContextMenu(self, view_obj, menu):
        save_dat = menu.addAction("save as dat")
        save_dat.triggered.connect(lambda f=self.save_dat, arg=view_obj.Object: f(arg))

    # non-gui function
    def save_dat(self, obj):
        airfoil = obj.Proxy.get_airfoil(obj)
        fn = QtGui.QFileDialog.getSaveFileName(caption='export airfoil')
        if not fn[0]:
            return
        airfoil.export_dat(fn[0])

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
        modify = menu.addAction("modify parafoil", os.path.join(RESOURCE_PATH, "calibrate.svg")) 
        create_airfoil = menu.addAction("airfoil from parafoil", os.path.join(RESOURCE_PATH, "airfoil.svg"))

        modify.triggered.connect(lambda f=self.modify_parafoil, arg=view_obj.Object: f(arg))
        create_airfoil.triggered.connect(lambda f=self.airfoil_from_parafoil, arg=view_obj.Object: f(arg))
        try:
            import xfoil_interface_wrap
        except ImportError:
            pass
        else:
            optimize = menu.addAction("optimze parafoil", os.path.join(RESOURCE_PATH, "optimize.svg"))
            optimize.triggered.connect(lambda f=self.optimize_parafoil, arg=view_obj.Object: f(arg))

    def modify_parafoil(self, obj):
        modifier = ParafoilModifier(obj)
        gui.Control.showDialog(modifier)

    def airfoil_from_parafoil(self, parafoil):
        obj = app.ActiveDocument.addObject("Part::FeaturePython", "airfoil")
        airfoil_proxies.LinkedAirfoilProxy(obj, parafoil)
        ViewProviderAirfoil(obj.ViewObject)
        # obj.Label = obj.Proxy.get_name(obj)
        app.activeDocument().recompute()

    def optimize_parafoil(self, obj):
        modifier = ParafoilOptimizer(obj)
        gui.Control.showDialog(modifier)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

class ConstrainedMarker(graphics.Marker):
    def __init__(self, points, weight, poles, pole_index, upper, dynamic=False):
        super(ConstrainedMarker, self).__init__(points, dynamic)
        self.poles = poles
        self.pole_index = pole_index
        self.weight = weight
        self.upper = upper

    @property
    def points(self):
        return self.data.point.getValues()

    @points.setter
    def points(self, points):
        point = [points[0][0], points[0][1], 0.]
        self.data.point.setValues(0, 1, [point])
        if hasattr(self, "poles"):
           self.poles.point.setValues(self.pole_index, 1, 
                                      [[*(np.array(point) * self.weight), self.weight]])

class ConstrainedXMarker(ConstrainedMarker):
    @property
    def points(self):
        return self.data.point.getValues()

    @points.setter
    def points(self, points):
        point = [points[0][0], points[0][1], 0.]
        self.data.point.setValues(0, 1, [point])
        if hasattr(self, "poles"):
            self.poles.point.setValues(self.pole_index, 1, 
                                       [[*(np.array(point) * self.weight), self.weight]])
        if hasattr(self, "tangent_point"):
            self.tangent_point.update_by_other(point)

    def set_tangent_point(self, other):
        self.tangent_point = other

    def update_by_other(self, point):
        r = np.linalg.norm(np.array(self.points[0]))
        direction = - np.array(point)
        direction /= np.linalg.norm(direction)
        pos = (direction * r).tolist()
        self.data.point.setValues(0, 1, [pos]) 
        if hasattr(self, "poles"):
            self.poles.point.setValues(self.pole_index, 1, 
                                      [[*(np.array(pos) * self.weight), self.weight]])


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
        # add a table witht the pole-values
        self.upper_pole_table = QtGui.QTableWidget(7, 3)
        for i, dim in enumerate(["x", "y", "w"]):
            self.upper_pole_table.setHorizontalHeaderItem(i, QtGui.QTableWidgetItem(dim))
        self.layout.addWidget(self.upper_pole_table)


        self.lower_pole_table = QtGui.QTableWidget(7, 3)
        for i, dim in enumerate(["x", "y", "w"]):
            self.lower_pole_table.setHorizontalHeaderItem(i, QtGui.QTableWidgetItem(dim))
        self.layout.addWidget(self.lower_pole_table)

        # create checkboxes: x, y, w
        self.q_calibrate_x = QtGui.QCheckBox("calibrate x-values")
        self.q_calibrate_y = QtGui.QCheckBox("calibrate y-values")
        self.q_calibrate_w = QtGui.QCheckBox("calibrate weights")

        self.q_calibrate_y.setChecked(True)

        # create button calibrate
        self.q_run = QtGui.QPushButton("run")
        self.q_run.clicked.connect(self._calibrate)

        self.calibration_layout.addWidget(self.q_calibrate_x)
        self.calibration_layout.addWidget(self.q_calibrate_y)
        self.calibration_layout.addWidget(self.q_calibrate_w)
        self.calibration_layout.addWidget(self.q_run)


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
        self.interaction_sep.selection_changed = self.selection_changed

        upper_array = self.obj.Proxy.get_upper_array(self.obj)
        lower_array = self.obj.Proxy.get_lower_array(self.obj)

        upper_array_1 = copy.copy(upper_array)
        upper_array_1[:3] *= upper_array_1[3]
        lower_array_1 = copy.copy(lower_array)
        lower_array_1[:3] *= lower_array_1[3]
        self.upper_poles.point.setValues(0, 9, upper_array_1.T)
        self.lower_poles.point.setValues(0, 9, lower_array_1.T)
        self.upper_markers = []
        self.lower_markers = []
        tangent_points = []
        k = 0
        for i, mat in enumerate([upper_array, lower_array]):
            if i == 0:
                poles = self.upper_poles
                _markers = self.upper_markers
                upper = True
            else:
                poles = self.lower_poles
                _markers = self.lower_markers
                upper = False
            for j, col in enumerate(mat.T):
                if j in [0, 8]:
                    marker = graphics.Marker([col[:-1]], dynamic=False)
                elif (j == 1 and i == 0) or (j == 1 and i == 1):
                    marker = ConstrainedXMarker([col[:-1]], col[-1], poles, j, upper,  dynamic=True)
                    tangent_points.append(marker)
                else:
                    marker = ConstrainedMarker([col[:-1]], col[-1], poles, j, upper, dynamic=True)
                marker.on_drag.append(self.update_table)
                self.interaction_sep += marker
                _markers.append(marker)
                k += 1
        tangent_points[0].set_tangent_point(tangent_points[1])
        tangent_points[1].set_tangent_point(tangent_points[0])

        self.task_separator += self.interaction_sep
        self.interaction_sep.register()
        self.update_table()
        self.upper_pole_table.cellChanged.connect(self.update_upper_points_by_table)
        self.lower_pole_table.cellChanged.connect(self.update_lower_points_by_table)

    def selection_changed(self):
        self.upper_pole_table.clearSelection()
        self.lower_pole_table.clearSelection()
        for marker in self.interaction_sep.selected_objects:
            r = marker.pole_index - 1
            if marker.upper:
                self.upper_pole_table.selectRow(r)
            else:
                self.lower_pole_table.selectRow(r)


    def _get_bspline(self):
        """
        returns a coin.SoNurbsCurve and the poles seperators
        set the pole-values by poels.point.setValues(0, 9, mat.tolist())
        """
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth = 2
        complexity = coin.SoComplexity()
        complexity.value = 1.
        spline_sep = coin.SoSeparator()
        upper_sep = coin.SoSeparator()
        lower_sep = coin.SoSeparator()
        knot_vector = 5 * [0] + [0.2, 0.4, 0.6, 0.8] + 5 * [1]
        upper_curve = coin.SoNurbsCurve()
        lower_curve = coin.SoNurbsCurve()
        upper_curve.knotVector.setValues(0, len(knot_vector), knot_vector)
        lower_curve.knotVector.setValues(0, len(knot_vector), knot_vector)
        upper_curve.numControlPoints = 9
        lower_curve.numControlPoints = 9
        upper_poles = coin.SoCoordinate4()
        lower_poles = coin.SoCoordinate4()
        upper_line_set = coin.SoLineSet()
        lower_line_set = coin.SoLineSet()

        # no need to set degree. Should be computed by numControlPoints and knotvector
        upper_sep += [complexity, upper_poles, upper_line_set, draw_style, upper_curve]
        lower_sep += [complexity, lower_poles, lower_line_set, draw_style, lower_curve]
        spline_sep += [upper_sep, lower_sep]
        return (spline_sep, upper_poles, lower_poles)

    def update_table(self):
        self.upper_pole_table.blockSignals(True)
        self.lower_pole_table.blockSignals(True)
        upper_array, lower_array = self.get_mat_from_current()
        for i, row in enumerate(upper_array.T[1:-1]):
            for j, element in enumerate(row[[0,1,3]]):
                self.upper_pole_table.setItem(i, j, QtGui.QTableWidgetItem(str(round(element,5))))
        for i, row in enumerate(lower_array.T[1:-1]):
            for j, element in enumerate(row[[0,1,3]]):
                self.lower_pole_table.setItem(i, j, QtGui.QTableWidgetItem(str(round(element,5))))
        self.upper_pole_table.blockSignals(False)
        self.lower_pole_table.blockSignals(False)

    def update_upper_points_by_table(self, row, col):
        x = float(self.upper_pole_table.item(row, 0).text())
        y = float(self.upper_pole_table.item(row, 1).text())
        w = float(self.upper_pole_table.item(row, 2).text())
        self.upper_markers[row + 1].weight = w
        self.upper_markers[row + 1].points = [[x, y, 0.]]

    def update_lower_points_by_table(self, row, col):
        x = float(self.lower_pole_table.item(row, 0).text())
        y = float(self.lower_pole_table.item(row, 1).text())
        w = float(self.lower_pole_table.item(row, 2).text())
        self.lower_markers[row + 1].weight = w
        self.lower_markers[row + 1].points = [[x, y, 0.]]


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



    def get_mat_from_current(self):
        upper_array = np.array([list(point) for point in self.upper_poles.point.getValues()]).T
        lower_array = np.array([list(point) for point in self.lower_poles.point.getValues()]).T
        upper_array[:3] /= upper_array[3]
        lower_array[:3] /= lower_array[3]
        return (upper_array, lower_array)


    def set_parafoil_from_current(self):
        upper_array, lower_array = self.get_mat_from_current()
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


class ParafoilOptimizer(object):
    # draws airfoil for every new design
    # buttons for different optimons (x, y, w optimisation)
    def __init__(self, obj):
        self.obj = obj  # self.obj.Proxy --> parafoil_proxy
        self.form = []
        self.scene = gui.activeDocument().activeView().getSceneGraph()
        self.rm = gui.activeDocument().activeView().getViewer().getSoRenderManager()

        # widget for modification
        self.base_widget = QtGui.QWidget()
        self.form.append(self.base_widget)
        self.layout = QtGui.QFormLayout(self.base_widget)
        self.base_widget.setWindowTitle("optimization")

        self.setup_qt()


    def setup_qt(self):
        # create checkboxes: x, y, w
        self.q_optimize_x = QtGui.QCheckBox("optimize x-values")
        self.q_optimize_y = QtGui.QCheckBox("optimize y-values")
        self.q_optimize_w = QtGui.QCheckBox("optimize weights")

        self.q_optimize_y.setChecked(True)

        # create button optimize
        self.q_run = QtGui.QPushButton("run")
        # self.q_run.clicked.connect(self._optimize)

        self.target_table = QtGui.QTableWidget(10, 5)
        self.target_table.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem("type"))
        self.target_table.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem("cl"))
        self.target_table.setHorizontalHeaderItem(2, QtGui.QTableWidgetItem("Re"))
        self.target_table.setHorizontalHeaderItem(3, QtGui.QTableWidgetItem("weight"))
        self.target_table.setHorizontalHeaderItem(4, QtGui.QTableWidgetItem("target value"))

        self.layout.addWidget(self.target_table)
        self.layout.addWidget(self.q_optimize_x)
        self.layout.addWidget(self.q_optimize_y)
        self.layout.addWidget(self.q_optimize_w)
        self.layout.addWidget(self.q_run)

        self.q_run.clicked.connect(self.optimize)

    def table_to_function(self):
        rows = self.target_table.rowCount()
        cols = self.target_table.columnCount()
        table = []
        for i in range(rows):
            row = []
            for j in range(cols):
                value = self.target_table.item(i, j)
                if value:
                    value = value.text()
                    if value:
                        if j == 0:
                            row.append(str(value))
                        else:
                            row.append(float(value))
            if row:
                print(len(row))
                if len(row) == 4:
                    row.append(0)
                print(row)
                assert len(row) == 5
                table.append(row)
        print(table)
        # create function

        def target_function(airfoil):
            def xfoil_foo(airfoil, cl_input, re):
                from airfoil import XfoilCase
                app.activeDocument().recompute()
                gui.updateGui()
                case = XfoilCase(airfoil)
                params = XfoilCase.default_params
                params["re"] = re
                params["cl_input"] = cl_input
                response = case.compute_coefficients(params)
                print(response)
                return response["cd"], response["cm"]

            residuals = []
            for row in table:
                tp, cl, re, weight, target_value = row
                cd, cm = xfoil_foo(airfoil, cl, re)
                if row[0] == "cd_min":
                    residuals.append(weight * cd)
                elif row[0] == "glide_max":
                    residuals.append(weight * cl / cd)
                elif row[0] == "cm_target":
                    residuals.append(cm - targetvalue)

            return residuals

        return target_function

    def optimize(self):
        opt_x = self.q_optimize_x.isChecked()
        opt_y = self.q_optimize_y.isChecked()
        opt_w = self.q_optimize_w.isChecked()
        self.obj.Proxy.optimize(self.obj, self.table_to_function(), opt_x, opt_y, opt_w)

