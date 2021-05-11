#
# Tests for the base battery model class
#
from pybamm.models.full_battery_models.base_battery_model import Options
import pybamm
import unittest
import io
from contextlib import redirect_stdout

OPTIONS_DICT = {
    "surface form": "differential",
    "loss of active material": "negative",
    "thermal": "x-full",
}

PRINT_OPTIONS_OUTPUT = """\
'operating mode': 'current' (possible: ['current', 'voltage', 'power'])
'dimensionality': 0 (possible: [0, 1, 2])
'surface form': 'differential' (possible: ['false', 'differential', 'algebraic'])
'convection': 'none' (possible: ['none', 'uniform transverse', 'full transverse'])
'side reactions': []
'interfacial surface area': 'constant' (possible: ['constant', 'varying'])
'current collector': 'uniform' (possible: ['uniform', 'potential pair', 'potential pair quite conductive'])
'particle': 'Fickian diffusion' (possible: ['Fickian diffusion', 'fast diffusion', 'uniform profile', 'quadratic profile', 'quartic profile'])
'particle shape': 'spherical' (possible: ['spherical', 'user', 'no particles'])
'electrolyte conductivity': 'default' (possible: ['default', 'full', 'leading order', 'composite', 'integrated'])
'thermal': 'x-full' (possible: ['isothermal', 'lumped', 'x-lumped', 'x-full'])
'cell geometry': 'pouch' (possible: ['arbitrary', 'pouch'])
'external submodels': []
'SEI': 'none' (possible: ['none', 'constant', 'reaction limited', 'solvent-diffusion limited', 'electron-migration limited', 'interstitial-diffusion limited', 'ec reaction limited'])
'lithium plating': 'none' (possible: ['none', 'reversible', 'irreversible'])
'SEI porosity change': 'false' (possible: ['true', 'false'])
'lithium plating porosity change': 'false' (possible: ['true', 'false'])
'loss of active material': 'negative' (possible: ['none', 'negative', 'positive', 'both'])
'working electrode': 'none'
'particle cracking': 'none' (possible: ['none', 'no cracking', 'negative', 'positive', 'both'])
'total interfacial current density as a state': 'false' (possible: ['true', 'false'])
'SEI film resistance': 'none' (possible: ['none', 'distributed', 'average'])
"""  # noqa: E501


class TestBaseBatteryModel(unittest.TestCase):
    def test_process_parameters_and_discretise(self):
        model = pybamm.lithium_ion.SPM()
        # Set up geometry and parameters
        geometry = model.default_geometry
        parameter_values = model.default_parameter_values
        parameter_values.process_geometry(geometry)
        # Set up discretisation
        mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)
        disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
        # Process expression
        c = pybamm.Parameter("Negative electrode thickness [m]") * pybamm.Variable(
            "X-averaged negative particle concentration",
            domain="negative particle",
            auxiliary_domains={"secondary": "current collector"},
        )
        processed_c = model.process_parameters_and_discretise(c, parameter_values, disc)
        self.assertIsInstance(processed_c, pybamm.Multiplication)
        self.assertIsInstance(processed_c.left, pybamm.Scalar)
        self.assertIsInstance(processed_c.right, pybamm.StateVector)
        # Process flux manually and check result against flux computed in particle
        # submodel
        c_n = model.variables["X-averaged negative particle concentration"]
        T = pybamm.PrimaryBroadcast(
            model.variables["X-averaged negative electrode temperature"],
            ["negative particle"],
        )
        D = model.param.D_n(c_n, T)
        N = -D * pybamm.grad(c_n)

        flux_1 = model.process_parameters_and_discretise(N, parameter_values, disc)
        flux_2 = model.variables["X-averaged negative particle flux"]
        param_flux_2 = parameter_values.process_symbol(flux_2)
        disc_flux_2 = disc.process_symbol(param_flux_2)
        self.assertEqual(flux_1.id, disc_flux_2.id)

    def test_default_geometry(self):
        var = pybamm.standard_spatial_vars

        model = pybamm.BaseBatteryModel({"dimensionality": 0})
        self.assertEqual(
            model.default_geometry["current collector"][var.z]["position"], 1
        )
        model = pybamm.BaseBatteryModel({"dimensionality": 1})
        self.assertEqual(model.default_geometry["current collector"][var.z]["min"], 0)
        model = pybamm.BaseBatteryModel({"dimensionality": 2})
        self.assertEqual(model.default_geometry["current collector"][var.y]["min"], 0)

    def test_default_submesh_types(self):
        model = pybamm.BaseBatteryModel({"dimensionality": 0})
        self.assertTrue(
            issubclass(
                model.default_submesh_types["current collector"].submesh_type,
                pybamm.SubMesh0D,
            )
        )
        model = pybamm.BaseBatteryModel({"dimensionality": 1})
        self.assertTrue(
            issubclass(
                model.default_submesh_types["current collector"].submesh_type,
                pybamm.Uniform1DSubMesh,
            )
        )
        model = pybamm.BaseBatteryModel({"dimensionality": 2})
        self.assertTrue(
            issubclass(
                model.default_submesh_types["current collector"].submesh_type,
                pybamm.ScikitUniform2DSubMesh,
            )
        )

    def test_default_var_pts(self):
        var = pybamm.standard_spatial_vars
        var_pts = {
            var.x_n: 20,
            var.x_s: 20,
            var.x_p: 20,
            var.r_n: 30,
            var.r_p: 30,
            var.y: 10,
            var.z: 10,
        }
        model = pybamm.BaseBatteryModel({"dimensionality": 0})
        self.assertDictEqual(var_pts, model.default_var_pts)

        var_pts.update({var.x_n: 10, var.x_s: 10, var.x_p: 10})
        model = pybamm.BaseBatteryModel({"dimensionality": 2})
        self.assertDictEqual(var_pts, model.default_var_pts)

    def test_default_spatial_methods(self):
        model = pybamm.BaseBatteryModel({"dimensionality": 0})
        self.assertTrue(
            isinstance(
                model.default_spatial_methods["current collector"],
                pybamm.ZeroDimensionalSpatialMethod,
            )
        )
        model = pybamm.BaseBatteryModel({"dimensionality": 1})
        self.assertTrue(
            isinstance(
                model.default_spatial_methods["current collector"], pybamm.FiniteVolume
            )
        )
        model = pybamm.BaseBatteryModel({"dimensionality": 2})
        self.assertTrue(
            isinstance(
                model.default_spatial_methods["current collector"],
                pybamm.ScikitFiniteElement,
            )
        )

    def test_options(self):
        with self.assertRaisesRegex(pybamm.OptionError, "Option"):
            pybamm.BaseBatteryModel({"bad option": "bad option"})
        with self.assertRaisesRegex(pybamm.OptionError, "current collector model"):
            pybamm.BaseBatteryModel({"current collector": "bad current collector"})
        with self.assertRaisesRegex(pybamm.OptionError, "thermal"):
            pybamm.BaseBatteryModel({"thermal": "bad thermal"})
        with self.assertRaisesRegex(pybamm.OptionError, "cell geometry"):
            pybamm.BaseBatteryModel({"cell geometry": "bad geometry"})
        with self.assertRaisesRegex(pybamm.OptionError, "dimensionality"):
            pybamm.BaseBatteryModel({"dimensionality": 5})
        with self.assertRaisesRegex(pybamm.OptionError, "current collector"):
            pybamm.BaseBatteryModel(
                {"dimensionality": 1, "current collector": "bad option"}
            )
        with self.assertRaisesRegex(pybamm.OptionError, "surface form"):
            pybamm.BaseBatteryModel({"surface form": "bad surface form"})
        with self.assertRaisesRegex(pybamm.OptionError, "convection"):
            pybamm.BaseBatteryModel({"convection": "bad convection"})
        with self.assertRaisesRegex(
            pybamm.OptionError, "cannot have transverse convection in 0D model"
        ):
            pybamm.BaseBatteryModel({"convection": "full transverse"})
        with self.assertRaisesRegex(pybamm.OptionError, "particle"):
            pybamm.BaseBatteryModel({"particle": "bad particle"})
        with self.assertRaisesRegex(NotImplementedError, "The 'fast diffusion'"):
            pybamm.BaseBatteryModel({"particle": "fast diffusion"})
        with self.assertRaisesRegex(pybamm.OptionError, "particle shape"):
            pybamm.BaseBatteryModel({"particle shape": "bad particle shape"})
        with self.assertRaisesRegex(pybamm.OptionError, "operating mode"):
            pybamm.BaseBatteryModel({"operating mode": "bad operating mode"})
        with self.assertRaisesRegex(pybamm.OptionError, "electrolyte conductivity"):
            pybamm.BaseBatteryModel(
                {"electrolyte conductivity": "bad electrolyte conductivity"}
            )

        # SEI options
        with self.assertRaisesRegex(pybamm.OptionError, "SEI"):
            pybamm.BaseBatteryModel({"SEI": "bad sei"})
        with self.assertRaisesRegex(pybamm.OptionError, "SEI film resistance"):
            pybamm.BaseBatteryModel({"SEI film resistance": "bad SEI film resistance"})
        with self.assertRaisesRegex(pybamm.OptionError, "SEI porosity change"):
            pybamm.BaseBatteryModel({"SEI porosity change": "bad SEI porosity change"})
        with self.assertRaisesRegex(
            pybamm.OptionError, "SEI porosity change must now be given in string format"
        ):
            pybamm.BaseBatteryModel({"SEI porosity change": True})
        # changing defaults based on other options
        model = pybamm.BaseBatteryModel()
        self.assertEqual(model.options["SEI film resistance"], "none")
        model = pybamm.BaseBatteryModel({"SEI": "constant"})
        self.assertEqual(model.options["SEI film resistance"], "distributed")
        self.assertEqual(
            model.options["total interfacial current density as a state"], "true"
        )
        with self.assertRaisesRegex(pybamm.OptionError, "must be 'true'"):
            model = pybamm.BaseBatteryModel(
                {
                    "SEI film resistance": "distributed",
                    "total interfacial current density as a state": "false",
                }
            )

        # loss of active material model
        with self.assertRaisesRegex(pybamm.OptionError, "loss of active material"):
            model = pybamm.BaseBatteryModel(
                {"loss of active material": "bad LAM model"}
            )

        # crack model
        with self.assertRaisesRegex(pybamm.OptionError, "particle cracking"):
            pybamm.BaseBatteryModel({"particle cracking": "bad particle cracking"})

        # plating model
        with self.assertRaisesRegex(pybamm.OptionError, "lithium plating"):
            pybamm.BaseBatteryModel({"lithium plating": "bad plating"})

        with self.assertRaisesRegex(
            pybamm.OptionError, "lithium plating porosity change"
        ):
            pybamm.BaseBatteryModel(
                {
                    "lithium plating porosity change": "bad lithium "
                    "plating porosity change"
                }
            )

    def test_build_twice(self):
        model = pybamm.lithium_ion.SPM()  # need to pick a model to set vars and build
        with self.assertRaisesRegex(pybamm.ModelError, "Model already built"):
            model.build_model()

    def test_get_coupled_variables(self):
        model = pybamm.lithium_ion.BaseModel()
        model.submodels["current collector"] = pybamm.current_collector.Uniform(
            model.param
        )
        with self.assertRaisesRegex(pybamm.ModelError, "Missing variable"):
            model.build_model()


class TestOptions(unittest.TestCase):
    def test_print_options(self):
        with io.StringIO() as buffer, redirect_stdout(buffer):
            Options(OPTIONS_DICT).print_options()
            output = buffer.getvalue()
        self.assertEqual(output, PRINT_OPTIONS_OUTPUT)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    pybamm.settings.debug_mode = True
    unittest.main()
