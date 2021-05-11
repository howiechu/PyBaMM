#
# Class for electrolyte diffusion employing stefan-maxwell
#
import pybamm

from .base_electrolyte_diffusion import BaseElectrolyteDiffusion


class Full(BaseElectrolyteDiffusion):
    """Class for conservation of mass in the electrolyte employing the
    Stefan-Maxwell constitutive equations. (Full refers to unreduced by
    asymptotic methods)

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel
    reactions : dict
        Dictionary of reaction terms

    **Extends:** :class:`pybamm.electrolyte_diffusion.BaseElectrolyteDiffusion`
    """

    def __init__(self, param):
        super().__init__(param)

    def get_fundamental_variables(self):
        eps_c_e_n = pybamm.standard_variables.eps_c_e_n
        eps_c_e_s = pybamm.standard_variables.eps_c_e_s
        eps_c_e_p = pybamm.standard_variables.eps_c_e_p

        variables = self._get_standard_porosity_times_concentration_variables(
            eps_c_e_n, eps_c_e_s, eps_c_e_p
        )

        return variables

    def get_coupled_variables(self, variables):

        eps_n = variables["Negative electrode porosity"]
        eps_s = variables["Separator porosity"]
        eps_p = variables["Positive electrode porosity"]
        eps_c_e_n = variables["Negative electrode porosity times concentration"]
        eps_c_e_s = variables["Separator porosity times concentration"]
        eps_c_e_p = variables["Positive electrode porosity times concentration"]

        c_e_n = eps_c_e_n / eps_n
        c_e_s = eps_c_e_s / eps_s
        c_e_p = eps_c_e_p / eps_p

        variables.update(
            self._get_standard_concentration_variables(c_e_n, c_e_s, c_e_p)
        )

        eps = variables["Porosity"]
        c_e = variables["Electrolyte concentration"]
        tor = variables["Electrolyte tortuosity"]
        i_e = variables["Electrolyte current density"]
        v_box = variables["Volume-averaged velocity"]
        T = variables["Cell temperature"]

        param = self.param

        N_e_diffusion = -tor * param.D_e(c_e, T) * pybamm.grad(c_e)
        N_e_migration = param.C_e * param.t_plus(c_e, T) * i_e / param.gamma_e
        N_e_convection = param.C_e * c_e * v_box

        N_e = N_e_diffusion + N_e_migration + N_e_convection

        variables.update(self._get_standard_flux_variables(N_e))
        variables.update(self._get_total_concentration_electrolyte(c_e, eps))

        return variables

    def set_rhs(self, variables):

        param = self.param

        eps_c_e = variables["Porosity times concentration"]
        c_e = variables["Electrolyte concentration"]
        N_e = variables["Electrolyte flux"]
        div_Vbox = variables["Transverse volume-averaged acceleration"]

        sum_s_j = variables["Sum of electrolyte reaction source terms"]
        source_terms = sum_s_j / self.param.gamma_e

        self.rhs = {
            eps_c_e: -pybamm.div(N_e) / param.C_e + source_terms - c_e * div_Vbox
        }

    def set_initial_conditions(self, variables):

        eps_c_e = variables["Porosity times concentration"]

        self.initial_conditions = {
            eps_c_e: self.param.epsilon_init * self.param.c_e_init
        }

    def set_boundary_conditions(self, variables):

        c_e = variables["Electrolyte concentration"]

        self.boundary_conditions = {
            c_e: {
                "left": (pybamm.Scalar(0), "Neumann"),
                "right": (pybamm.Scalar(0), "Neumann"),
            },
        }
