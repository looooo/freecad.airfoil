import numpy as np
import pandas as pd
import xfoil_interface_wrap as xiw
from xfoil_interface import xfoil_options_type, xfoil_geom_options_type, \
                            xfoil_data_group
import copy

# TODO:
# add other computations like pressure study, flow, boundary-layer ...
# if needed


def shuffled(values):
    """

    Args:
      values: list of values

    Returns:
      : copy of values with random order

    """
    copy_values = list(values)
    np.random.shuffle(copy_values)
    return copy_values


def lhd(samples, dimensions):
    """

    Args:
      samples: number of samples
      dimensions: number of dimensions (eg. number of parameters)

    Returns:
      : latin-hyper-cube array with shape samples x dimensions

    """
    values = list(range(samples))
    return np.array([shuffled(values) for _ in range(dimensions)])


def lhs(samples, dimensions, min_values, max_values):
    """

    Args:
      samples:
      min_values:
      dimensions:
      max_values:

    Returns:
      : latin-hyper-cube-sampling array with shape samples x dimensions

    """
    lhd_values = lhd(samples, dimensions).T
    lhs_values = lhd_values + np.random.rand(samples, dimensions)
    scale = (max_values - min_values) / samples
    return lhs_values * scale  + min_values



class XfoilCase(object):
    """
    Compute aerodynamics coefficients of an airfoil.
    """
    default_params = {
        "re": 10000000,
        "mach": 0.1,
        "ncrit": 9.0,
        "cl_input": 0.0,
        "alpha_input": None  # use either cl_input or alpha_input
    }
    def __init__(self, airfoil):
        self.airfoil = airfoil

    @property
    def _x_z_npoint(self):
        return (*self.airfoil.coordinates.T, len(self.airfoil))
        
        
    def compute_coefficients(self, params=None, max_iterations=100):
        params = params or XfoilCase.default_params
        x, z, npoint = self._x_z_npoint

        opts = xfoil_options_type()
        opts.ncrit = params["ncrit"]
        opts.xtript = 1.
        opts.xtripb = 1.
        opts.viscous_mode = True
        opts.silent_mode = True
        opts.maxit = max_iterations
        opts.vaccel = 0.01   # TODO: where is this parameter used?

        geom_opts = xfoil_geom_options_type()
        geom_opts.npan = len(self.airfoil)
        geom_opts.cvpar = 1.
        geom_opts.cterat = 0.15
        geom_opts.ctrrat = 0.2
        geom_opts.xsref1 = 1.
        geom_opts.xsref2 = 1.
        geom_opts.xpref1 = 1.
        geom_opts.xpref2 = 1.

        # Xfoil data
        xdg = xfoil_data_group()
        xiw.xfoil_init(xdg)
        xiw.xfoil_defaults(xdg, opts)
        xiw.xfoil_set_buffer_airfoil(xdg, x, z, npoint)
        xiw.xfoil_set_paneling(xdg, geom_opts)
        if (xiw.xfoil_smooth_paneling(xdg) != 0):
            raise RuntimeError("libxfoil: Err 1")
        xnew, znew, stat = xiw.xfoil_get_current_airfoil(xdg, geom_opts.npan)
        if (stat != 0):
            raise RuntimeError("libxfoil: Err 1")

        xiw.xfoil_set_reynolds_number(xdg, params["re"])
        xiw.xfoil_set_mach_number(xdg, params["mach"])
        if "cl_input" in params.keys():
            alpha, cl, cd, cm, converged, stat = xiw.xfoil_speccl(xdg, params["cl_input"])
        elif "alpha_input" in params.keys():
            alpha, cl, cd, cm, converged, stat = xiw.xfoil_specal(xdg, params["alpha_input"])
        else:
            raise RuntimeError("you need to either set cl or alpha in params-dictionary")

        if (stat != 0):
            raise RuntimeError("libxfoil: Err 3")

        # xiw.xfoil_cleanup(xdg)
        response = {
            "alpha": alpha,
            "cl": cl,
            "cd": cd,
            "cm": cm,
            "converged": converged
        }
        response.update(params)
        return response


class XfoilStudy(object):
    def __init__(self, airfoil):
        self.df = self._empty_df
        self.case = XfoilCase(airfoil)

    @property
    def _empty_df(self):
        return pd.DataFrame(columns=["re", "mach", "ncrit", "cl_input", "alpha_input", \
                                        "alpha", "cl", "cd", "cm", "converged"])

    def run_study(self, params_df):
        """
        run a parameter study and add output to the studie's dataframe (df)
        in addition the output is also returned as a DataFrame object
        """
        study_df = self._empty_df
        for _, params in params_df.iterrows():
            response = self.case.compute_coefficients(dict(params))
            study_df = study_df.append(response, ignore_index=True)
        self.df = self.df.append(study_df)
        return study_df

    def _check_bounds(self, lower_bounds, upper_bounds):
        """
        check if boundary specification is correct and return the disabled
        key (either cl_input or alpha_input)
        """
        assert bool(lower_bounds["cl_input"]) == bool(upper_bounds["cl_input"])
        assert bool(lower_bounds["alpha_input"]) == bool(upper_bounds["alpha_input"])
        assert bool(lower_bounds["cl_input"]) != bool(lower_bounds["alpha_input"])
        if bool(lower_bounds["cl_input"]):
            return "alpha_input"
        else:
            return "cl_input"

    @property
    def _ordered_keys(self):
        return ["re", "mach", "ncrit", "cl_input", "alpha_input"]

    def _bounds_to_list(self, bounds):
        return [bounds[i] for i in self._ordered_keys if bounds[i]]

    def lhs_parameters(self, lower_bounds, upper_bounds, num_samples):
        disabled_param = self._check_bounds(lower_bounds, upper_bounds)
        lower_bounds_array = np.array(self._bounds_to_list(lower_bounds))
        upper_bounds_array = np.array(self._bounds_to_list(upper_bounds))
        assert len(lower_bounds) == len(upper_bounds)

        lhs_sampling = lhs(num_samples, len(lower_bounds_array), lower_bounds_array, upper_bounds_array)
        parameters_list = []
        for lhs_i in lhs_sampling:
            params = copy.copy(lower_bounds)
            i = 0
            for _, key in enumerate(self._ordered_keys):
                if key != disabled_param:
                    params[key] = lhs_i[i]
                    i += 1
            parameters_list.append(params)
        return pd.DataFrame(parameters_list)
            

    def centered_parameter_study(self, lower_bounds, upper_bounds, steps_vector):
        disabled_param = self._check_bounds(lower_bounds, upper_bounds)
        steps_vector_list = []
        for key in self._ordered_keys:
            if key != disabled_param and key in steps_vector.keys():
                steps_vector_list.append(steps_vector[key])
        lower_bounds_array = np.array(self._bounds_to_list(lower_bounds))
        upper_bounds_array = np.array(self._bounds_to_list(upper_bounds))
        center = (lower_bounds_array + upper_bounds_array) / 2
        diff = upper_bounds_array - lower_bounds_array
        diff_dict = {}
        center_params = copy.copy(lower_bounds)
        for i, key in enumerate(self._ordered_keys):
            if key != disabled_param:
                center_params[key] = center[i]
                diff_dict[key] = diff[i]
        parameters_list = [center_params]
        for key, value in steps_vector.items():
            if value > 0 and key != disabled_param:
                steps_per_side = (value + 1)
                for i in range(1, steps_per_side)[::-1]:
                    params = copy.copy(center_params)
                    params[key] -= diff_dict[key] / 2 * i / steps_per_side
                    parameters_list.append(params)
                for i in range(1, steps_per_side):
                    params = copy.copy(center_params)
                    params[key] += diff_dict[key] / 2 * i / steps_per_side
                    parameters_list.append(params)
        return pd.DataFrame(parameters_list)


    def vector_parameters(self, lower_bounds, upper_bounds, num_steps):
        disabled_param = self._check_bounds(lower_bounds, upper_bounds)
        parameters_list = []
        lower_bounds_array = np.array(self._bounds_to_list(lower_bounds))
        upper_bounds_array = np.array(self._bounds_to_list(upper_bounds))
        diff = upper_bounds_array - lower_bounds_array
        for i in range(num_steps):
            factor = i / (num_steps - 1)
            params = copy.copy(lower_bounds)
            params_array = lower_bounds_array + diff * factor
            for j, key in enumerate(self._ordered_keys):
                if key != disabled_param:
                    params[key] = params_array[j]
            parameters_list.append(params)
        return pd.DataFrame(parameters_list)