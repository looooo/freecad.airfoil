import os

from PySide import QtGui
from PySide import QtCore

from pivy import coin

from freecad import app
import FreeCADGui as gui

from freecad.airfoil import RESOURCE_PATH
from freecad.airfoil import commands


class AirfoilCommand(object):
    def IsActive(self):
        return bool(app.activeDocument())

    def Activated(self):
        # create a task with different buttons
        tool = AirfoilTool()
        gui.Control.showDialog(tool)

    def GetResources(self):
        return {'Pixmap': os.path.join(RESOURCE_PATH, "airfoil.svg"),
                'MenuText': "create an airfoil by different methods",
                'ToolTip': "create an airfoil by different methods"}

class AirfoilTool(object):
    WIDGET_NAME = "airfoil tool"
    def __init__(self):
        self.form = []
        self.scene = gui.activeDocument().activeView().getSceneGraph()

        self.base_widget = QtGui.QWidget()
        self.form.append(self.base_widget)
        self.layout = QtGui.QFormLayout(self.base_widget)
        self.base_widget.setWindowTitle(AirfoilTool.WIDGET_NAME)

        # scene container
        self.task_separator = coin.SoSeparator()
        self.task_separator.setName('task_seperator')
        self.scene += self.task_separator
        airfoil_button = QtGui.QPushButton("import foil")
        trefftz_button = QtGui.QPushButton("create trefftz / jukowsky foil")
        vandevooren_button = QtGui.QPushButton("create VanDeVooren foil")
        naca_button = QtGui.QPushButton("create naca-foil")

        self.layout.addWidget(airfoil_button)
        self.layout.addWidget(trefftz_button)
        self.layout.addWidget(vandevooren_button)
        self.layout.addWidget(naca_button)

        airfoil_button.clicked.connect(self.airfoil_dialog)
        trefftz_button.clicked.connect(self.trefftz_dialog)
        vandevooren_button.clicked.connect(self.vandevooren_dialog)
        naca_button.clicked.connect(self.naca_dialog)


    def airfoil_dialog(self):
        fn = QtGui.QFileDialog.getOpenFileName(caption='import airfoil')
        commands.make_airfoil(fn[0])
        self.accept()

    def trefftz_dialog(self):
        dialog = QtGui.QDialog()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        layout = QtGui.QFormLayout(dialog)
        dialog.setLayout(layout)
        button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        q_real_number = QtGui.QDoubleSpinBox()
        q_real_number.setRange(-1.0, 1.0)
        q_real_number.setValue(-0.10)
        q_real_number.setSingleStep(0.01)
        q_imag_number = QtGui.QDoubleSpinBox()
        q_imag_number.setRange(-1.0, 1.0)
        q_imag_number.setValue(0.10)
        q_imag_number.setSingleStep(0.01)
        q_tau = QtGui.QDoubleSpinBox()
        q_tau.setRange(-1.0, 1.0)
        q_tau.setValue(0.0)
        q_tau.setSingleStep(0.01)
        q_numpoints = QtGui.QSpinBox()
        q_numpoints.setRange(10, 500)
        q_numpoints.setValue(50)

        def dialog_accept(*args):
            commands.make_trefftz(q_real_number.value() + \
                                  1j * q_imag_number.value(), q_tau.value(), 
                                  q_numpoints.value())
            dialog.close()
            self.accept()

        def dialog_reject(*args):
            dialog.close()

        button_box.accepted.connect(dialog_accept)
        button_box.rejected.connect(dialog_reject)

        layout.addRow(QtGui.QLabel("real number"), q_real_number)
        layout.addRow(QtGui.QLabel("imag number"), q_imag_number)
        layout.addRow(QtGui.QLabel("tau"), q_tau)
        layout.addRow(QtGui.QLabel("numpoints per side"), q_numpoints)
        layout.addRow(button_box)
        dialog.exec()

    def naca_dialog(self):
        dialog = QtGui.QDialog()
        layout = QtGui.QFormLayout(dialog)
        dialog.setLayout(layout)
        button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        q_nacadigits = QtGui.QLineEdit()
        q_nacadigits.setText("2412")
        q_numpoints = QtGui.QSpinBox()
        q_numpoints.setRange(10, 500)
        q_numpoints.setValue(50)

        def dialog_accept(*args):
            commands.make_naca(q_nacadigits.text(), q_numpoints.value())
            dialog.close()
            self.accept()

        def dialog_reject(*args):
            dialog.close()

        button_box.accepted.connect(dialog_accept)
        button_box.rejected.connect(dialog_reject)

        layout.addRow(QtGui.QLabel("naca digits [string]"), q_nacadigits)
        layout.addRow(QtGui.QLabel("numpoints per side"), q_numpoints)
        layout.addRow(button_box)
        dialog.exec()

    def vandevooren_dialog(self):
        dialog = QtGui.QDialog()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        layout = QtGui.QFormLayout(dialog)
        dialog.setLayout(layout)
        button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        q_tau = QtGui.QDoubleSpinBox()
        q_tau.setRange(-1.0, 1.0)
        q_tau.setValue(0.05)
        q_tau.setSingleStep(0.01)
        q_epsilon = QtGui.QDoubleSpinBox()
        q_epsilon.setRange(-1.0, 1.0)
        q_epsilon.setValue(0.05)
        q_epsilon.setSingleStep(0.01)
        q_numpoints = QtGui.QSpinBox()
        q_numpoints.setRange(10, 500)
        q_numpoints.setValue(50)

        def dialog_accept(*args):
            commands.make_vandevooren(q_tau.value(), q_epsilon.value(),  
                                      q_numpoints.value())
            dialog.close()
            self.accept()

        def dialog_reject(*args):
            dialog.close()

        button_box.accepted.connect(dialog_accept)
        button_box.rejected.connect(dialog_reject)

        layout.addRow(QtGui.QLabel("tau"), q_tau)
        layout.addRow(QtGui.QLabel("epsilon"), q_epsilon)
        layout.addRow(QtGui.QLabel("numpoints per side"), q_numpoints)
        layout.addRow(button_box)
        dialog.exec()

    def accept(self):
        self.scene -= self.task_separator
        gui.activeDocument().activeView().viewTop()
        gui.SendMsgToActiveView("ViewFit")
        gui.Control.closeDialog()

    def reject(self):
        self.scene -= self.task_separator
        gui.Control.closeDialog()


class ParafoilCommand(object):
    def IsActive(self):
        return bool(app.activeDocument())

    def Activated(self):
        # create a task with different buttons
        commands.make_parafoil()
        gui.activeDocument().activeView().viewTop()
        gui.SendMsgToActiveView("ViewFit")

    def GetResources(self):
        return {'Pixmap': os.path.join(RESOURCE_PATH, "parafoil.svg"),
                'MenuText': "create a parametric airfoil defined by 2 nurbs-curves",
                'ToolTip': "create a parametric airfoil defined by 2 nurbs-curves"}



class ParaFoilOptimize(object):
    def IsActive(self):
        return bool(app.activeDocument())

    def Activated(self):
        # create a task with different buttons
        pass

    def GetResources(self):
        return {'Pixmap': os.path.join(RESOURCE_PATH, "optimize.svg"),
                'MenuText': "optimize an airfoil for a given target function",
                'ToolTip': "optimize an airfoil for a given target function"}