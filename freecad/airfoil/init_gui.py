import os
import FreeCADGui as Gui
import FreeCAD as App
from freecad.airfoil import RESOURCE_PATH
from freecad.airfoil import tasks


class AirfoilWorkbench(Gui.Workbench):
    """
    class which gets initiated at starup of the gui
    """

    MenuText = "airfoil workbench"
    ToolTip = "workbench for airfoil design, analysis and optimization"
    Icon = os.path.join(RESOURCE_PATH, "airfoil-workbench.svg")
    toolbox = ["AirfoilCommand", "ParafoilCommand", "ParafoilCalibrate", "ParaFoilOptimize"]

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    def Initialize(self):
        """
        This function is called at the first activation of the workbench.
        here is the place to import all the commands
        """
        Gui.addCommand('AirfoilCommand', tasks.AirfoilCommand())
        Gui.addCommand('ParafoilCommand', tasks.ParafoilCommand())
        Gui.addCommand('ParafoilCalibrate', tasks.ParaFoilCalibrate())
        Gui.addCommand('ParaFoilOptimize', tasks.ParaFoilOptimize())

        self.appendToolbar("Airfoil", self.toolbox)
        self.appendMenu("Airfoil", self.toolbox)

    def Activated(self):
        '''
        code which should be computed when a user switch to this workbench
        '''
        pass

    def Deactivated(self):
        '''
        code which should be computed when this workbench is deactivated
        '''
        pass


Gui.addWorkbench(AirfoilWorkbench())
