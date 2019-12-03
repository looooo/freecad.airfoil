from freecad import app
import FreeCADGui as gui
import Part as part

from freecad.airfoil import airfoil_proxies
from freecad.airfoil import airfoil_view_proxies


def make_airfoil(fn=None):
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "airfoil")
    airfoil_proxies.AirfoilProxy(obj, fn)
    airfoil_view_proxies.ViewProviderAirfoil(obj.ViewObject)
    obj.Label = obj.Proxy.get_name(obj)
    app.activeDocument().recompute()
    return obj

def make_joukowsky(midpoint=-0.1+0.1j, numpoints=50):
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "jukowsky-airfoil")
    airfoil_proxies.JoukowskyProxy(obj, midpoint, numpoints)
    airfoil_view_proxies.ViewProviderAirfoil(obj.ViewObject)
    app.activeDocument().recompute()
    return obj

def make_trefftz(midpoint=-0.1+0.1j, tau:float=0.05, numpoints:int=50):
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "trefftz-airfoil")
    airfoil_proxies.TrefftzProxy(obj, midpoint, tau, numpoints)
    airfoil_view_proxies.ViewProviderAirfoil(obj.ViewObject)
    app.activeDocument().recompute()
    return obj

def make_vandevooren(tau=0.05, epsilon=0.05, numpoints=50):
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "vandavooren-airfoil")
    airfoil_proxies.VandevoorenProxy(obj, tau, epsilon, numpoints)
    airfoil_view_proxies.ViewProviderAirfoil(obj.ViewObject)
    app.activeDocument().recompute()
    return obj

def make_naca(naca_digits="2412", numpoints=50):
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "naca-airfoil")
    airfoil_proxies.NacaProxy(obj, naca_digits, numpoints)
    airfoil_view_proxies.ViewProviderAirfoil(obj.ViewObject)
    app.activeDocument().recompute()
    return obj

def make_parafoil():
    obj = app.ActiveDocument.addObject("Part::FeaturePython", "parafoil")
    airfoil_proxies.ParafoilProxy(obj)
    airfoil_view_proxies.ViewProviderParafoil(obj.ViewObject)
    app.activeDocument().recompute()
    return obj

def calibrate_parafoil():
    selection = gui.Selection.getSelection()
    assert len(selection) == 2
    parafoil_obj = selection[0]
    airfoil_obj = selection[1]
    assert isinstance(parafoil_obj.Proxy, airfoil_proxies.ParafoilProxy)
    assert isinstance(airfoil_obj.Proxy, airfoil_proxies.AirfoilProxy)
    parafoil_obj.Proxy.calibrate(parafoil_obj, airfoil_obj.Proxy.get_airfoil(airfoil_obj))
    app.activeDocument().recompute()