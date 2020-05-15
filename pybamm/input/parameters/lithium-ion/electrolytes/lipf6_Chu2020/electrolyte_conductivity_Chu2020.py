from pybamm import exp, constants


def electrolyte_conductivity_Chu2020(T):
    """
    Conductivity of LiPF6 in EC:DMC as a function of ion concentration. The original
    data is from [1]. The fit is from Dualfoil [2].

    References
    ----------
    .. [1] Chu, Howie N., et al. "Parameterization of prismatic lithium–iron–phosphate cells 
    through a streamlined thermal/electrochemical model." Journal of Power Sources 453 (2020): 227787.

    Parameters
    ----------
    T: :class:`pybamm.Symbol`
        Dimensional temperature

    Returns
    -------
    :class:`pybamm.Symbol`
        Solid diffusivity
    """

    sigma_e = 0.022

    a_k_e = 0.002
    lin = a_k_e * (T - 298.15)

    return sigma_e + lin
