from .airfoil import Airfoil
try:
	from .study import XfoilStudy, XfoilCase
except ImportError as e:
	print("xfoil disabled due to ImportError: {}".format(e))
