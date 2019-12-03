from setuptools import setup
import os
# from freecad.workbench_starterkit.version import __version__
# name: this is the name of the distribution.
# Packages using the same name here cannot be installed together

version_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 
                            "freecad", "airfoil", "version.py")
with open(version_path) as fp:
    exec(fp.read())

setup(name='freecad.airfoil',
      version=str(__version__),
      packages=['airfoil', 
                'freecad',
                'freecad.airfoil_gui'],
      maintainer="looooo",
      maintainer_email="sppedflyer@gmail.com",
      url="airfoil-workbench",
      description="aifoil-module and airfoil workbench for freecad, installable with pip",
      include_package_data=True)
