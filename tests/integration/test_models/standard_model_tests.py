#
# Standard basic tests for any model
#
import pybamm
import tests

import copy
import numpy as np
from collections import defaultdict


class StandardModelTest(object):
    """ Basic processing test for the models. """

    def __init__(
        self,
        model,
        parameter_values=None,
        geometry=None,
        submesh_types=None,
        var_pts=None,
        spatial_methods=None,
        solver=None,
    ):
        self.model = model
        # Set parameters, geometry, spatial methods etc
        # The code below is equivalent to:
        #    if parameter_values is None:
        #       self.parameter_values = model.default_parameter_values
        #    else:
        #       self.parameter_values = parameter_values
        self.parameter_values = parameter_values or model.default_parameter_values
        geometry = geometry or model.default_geometry
        submesh_types = submesh_types or model.default_submesh_types
        var_pts = var_pts or model.default_var_pts
        spatial_methods = spatial_methods or model.default_spatial_methods
        self.solver = solver or model.default_solver
        # Process geometry
        self.parameter_values.process_geometry(geometry)
        # Set discretisation
        mesh = pybamm.Mesh(geometry, submesh_types, var_pts)
        self.disc = pybamm.Discretisation(mesh, spatial_methods)

    def test_processing_parameters(self, parameter_values=None):
        # Overwrite parameters if given
        if parameter_values is not None:
            self.parameter_values = parameter_values
        self.parameter_values.process_model(self.model)
        # Model should still be well-posed after processing
        self.model.check_well_posedness()
        # No Parameter or FunctionParameter nodes in the model
        for eqn in {**self.model.rhs, **self.model.algebraic}.values():
            if any(
                [
                    isinstance(x, (pybamm.Parameter, pybamm.FunctionParameter))
                    for x in eqn.pre_order()
                ]
            ):
                raise TypeError(
                    "Not all Parameter and FunctionParameter objects processed"
                )

    def test_processing_disc(self, disc=None):
        # Overwrite discretisation if given
        if disc is not None:
            self.disc = disc
        self.disc.process_model(self.model)

        # Model should still be well-posed after processing
        self.model.check_well_posedness(post_discretisation=True)

    def test_solving(self, solver=None, t_eval=None):
        # Overwrite solver if given
        if solver is not None:
            self.solver = solver
        if t_eval is None:
            t_eval = np.linspace(0, 1, 100)

        self.solver.solve(self.model, t_eval)

    def test_outputs(self):
        # run the standard output tests
        std_out_test = tests.StandardOutputTests(
            self.model, self.parameter_values, self.disc, self.solver
        )
        std_out_test.test_all()

    def test_all(
        self, param=None, disc=None, solver=None, t_eval=None, skip_output_tests=False
    ):
        self.model.check_well_posedness()
        self.test_processing_parameters(param)
        self.test_processing_disc(disc)
        self.test_solving(solver, t_eval)

        if (
            isinstance(
                self.model, (pybamm.LithiumIonBaseModel, pybamm.LeadAcidBaseModel)
            )
            and not skip_output_tests
        ):
            self.test_outputs()

    def test_update_parameters(self, param):
        # check if geometry has changed, throw error if so (need to re-discretise)
        if any(
            [
                length in param.keys()
                and param[length] != self.parameter_values[length]
                for length in [
                    "Negative electrode width [m]",
                    "Separator width [m]",
                    "Positive electrode width [m]",
                ]
            ]
        ):
            raise ValueError(
                "geometry has changed, the orginal model needs to be re-discretised"
            )
        # otherwise update self.param and change the parameters in the discretised model
        self.param = param
        param.update_model(self.model, self.disc)
        # Model should still be well-posed after processing
        self.model.check_well_posedness()


class OptimisationsTest(object):
    """ Test that the optimised models give the same result as the original model. """

    def __init__(self, model, parameter_values=None, disc=None):
        # Set parameter values
        if parameter_values is None:
            parameter_values = model.default_parameter_values
        # Process model and geometry
        parameter_values.process_model(model)
        parameter_values.process_geometry(model.default_geometry)
        geometry = model.default_geometry
        # Set discretisation
        if disc is None:
            mesh = pybamm.Mesh(
                geometry, model.default_submesh_types, model.default_var_pts
            )
            disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
        # Discretise model
        disc.process_model(model)

        self.model = model

    def evaluate_model(self, simplify=False, use_known_evals=False):
        result = np.empty((0, 1))
        for eqn in [self.model.concatenated_rhs, self.model.concatenated_algebraic]:
            if simplify:
                eqn = eqn.simplify()

            y = self.model.concatenated_initial_conditions
            if use_known_evals:
                eqn_eval, known_evals = eqn.evaluate(0, y, known_evals={})
            else:
                eqn_eval = eqn.evaluate(0, y)
            if eqn_eval.shape == (0,):
                eqn_eval = eqn_eval[:, np.newaxis]

            result = np.concatenate([result, eqn_eval])

        return result


def get_manufactured_solution_errors(model, ns):
    """
    Compute the error from solving the model with manufactured solution

    Parameters
    ----------
    model : :class:`pybamm.BaseModel`
        The model to solve
    ns : iter of int
        The grid size(s) for which to calculate the error(s)

    """
    # Process model and geometry
    param = model.default_parameter_values
    param.process_model(model)
    geometry = model.default_geometry
    param.process_geometry(geometry)
    # Add manufactured solution to model
    ms = pybamm.ManufacturedSolution()
    ms.process_model(model)
    # Set up solver
    t_eval = np.linspace(0, 1)
    solver = model.default_solver

    # Function for convergence testing
    def get_approx_exact(n):
        model_copy = copy.deepcopy(model)
        # Set up discretisation
        var = pybamm.standard_spatial_vars
        submesh_pts = {var.x_n: n, var.x_s: n, var.x_p: n, var.r_n: n, var.r_p: n}
        mesh = pybamm.Mesh(geometry, model_copy.default_submesh_types, submesh_pts)
        disc = pybamm.Discretisation(mesh, model_copy.default_spatial_methods)

        # Discretise and solve
        disc.process_model(model_copy)
        solver.solve(model_copy, t_eval)
        t, y = solver.t, solver.y
        # Process model and exact solutions
        all_approx_exact = {}
        for (
            var_string,
            manufactured_variable,
        ) in ms.manufactured_variable_strings.items():
            # Approximate solution from solving the model
            approx = pybamm.ProcessedVariable(
                model_copy.variables[var_string], t, y, mesh=disc.mesh
            )
            # Exact solution from manufactured solution
            exact = pybamm.ProcessedVariable(
                disc.process_symbol(manufactured_variable), t, y, mesh=disc.mesh
            )
            all_approx_exact[var_string] = (approx, exact)
            import ipdb

            ipdb.set_trace()

        # error
        return all_approx_exact

    # Calculate the errors for each variable for each n (nested dictionary)
    ns_approx_exact_dict = {n: get_approx_exact(int(n)) for n in ns}

    # Reverse the nested dict for easier testing
    approx_exact_ns_dict = defaultdict(dict)
    for n, all_approx_exact_n in ns_approx_exact_dict.items():
        for var, approx_exact in all_approx_exact_n.items():
            approx_exact_ns_dict[var][n] = approx_exact
    return approx_exact_ns_dict
