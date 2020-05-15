from pybamm import exp, constants, standard_parameters_lithium_ion


def graphite_elyte_exchange_current_density_Chu2020(c_e, c_s_surf, T):
    """
    Exchange-current density for Butler-Volmer reactions between lfp and LiPF6

    References
    ----------
    .. [2] http://www.cchem.berkeley.edu/jsngrp/fortran.html

    Parameters
    ----------
    c_e : :class:`pybamm.Symbol`
        Electrolyte concentration [mol.m-3]
    c_s_surf : :class:`pybamm.Symbol`
        Particle concentration [mol.m-3]
    T : :class:`pybamm.Symbol`
        Temperature [K]

    Returns
    -------
    :class:`pybamm.Symbol`
        Exchange-current density [A.m-2]
    """
    i0_ref = 14.31  # (A/m2)
    E_i0 = 30.81
    arrhenius = exp(E_i0 / constants.R * (1 / 298.15 - 1 / T))

    return (
        i0_ref * arrhenius
    )
