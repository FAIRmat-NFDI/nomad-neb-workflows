from typing import TYPE_CHECKING, Optional
import numpy as np
import pint
import plotly.express as px

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Quantity, SubSection
from simulationworkflowschema.general import SimulationWorkflow
from nomad.datamodel.data import ArchiveSection
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad.datamodel.metainfo.workflow import TaskReference, Link
from nomad.units import ureg


configuration = config.get_plugin_entry_point(
    'nomad_neb_workflows.schema_packages:nomad_neb_workflows_plugin'
)

m_package = SchemaPackage()


class NEBWorkflowResults(ArchiveSection):
    """
    A section used to define the results of a Nudged Elastic Band (NEB) workflow. This section contains
    information about the total energy differences and the path of configurations in the NEB workflow.
    """

    total_energy_differences = Quantity(
        type=np.float64,
        shape=['*'],
        unit='eV',
        description="""
        Total energy differences of the system for each of the images in the path relative to the first (initial) image.
        """,
    )
    path = Quantity(
        type=np.float64,
        shape=['*'],
        unit='angstrom',
        description="""
        Path of configurations (reaction coordinate) in the NEB workflow. This is a list of distances
        between the images in the path.
        """,
    )
    reaction_energy = Quantity(
        type=np.float64,
        shape=[],
        unit='eV',
        description="""
        Reaction energy of the system. This is the energy difference between the initial and final images.
        """,
    )
    activation_energy = Quantity(
        type=np.float64,
        shape=[],
        unit='eV',
        description="""
        Activation energy of the reaction. This is the energy difference between the initial image and the highest point of the path.
        """,
    )

    activation_energy_fitted = Quantity(
        type=np.float64,
        shape=[],
        unit='eV',
        description="""
        Activation energy of the reaction determined from the fit to the NEB path. This is the energy difference between the initial image and the highest point of the fitted path.
        """,
    )


class NEBWorkflow(SimulationWorkflow, PlotSection):
    """
    A base section used to define Nudged Elastic Band (NEB) workflows. These workflows are used to find the
    minimum energy path and transition states between two stable states in a system. It involves interpolating
    a series of intermediate configurations (or images) between the initial and final states, and then optimize
    these images to trace the most energetically favorable path.

    This workflow is useful to extract reactivities and catalytic properties, energy barriers, etc.
    """

    name = Quantity(
        type=str,
        default='NEB',
        description='Name of the workflow. Default set to `NEB`.',
    )

    neb_workflow_results = SubSection(
        section_def=NEBWorkflowResults,
        repeats=False,
        description='Results of the NEB workflow.',
    )

    def extend_workflow(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Extend the workflow file with tasks and output from the input.
        Args:
            archive (EntryArchive): The archive to extend.
            logger (BoundLogger): The logger to log messages.
        """

        if self.inputs and len(self.inputs) > 3:
            if self.tasks is None or self.tasks == []:
                # Initialize the tasks list if it is None
                self.tasks = []
                for i in range(len(self.inputs)):
                    # Create a new task for each image
                    task = TaskReference()
                    input = Link()
                    output = Link()
                    output_system = Link()

                    if i == 0:
                        task.name = 'Initial Image Simulation'
                        input.section = self.inputs[0].section.system[-1]
                        task.inputs.append(input)
                        output.section = self.inputs[0].section.calculation[-1]
                        task.outputs.append(output)
                    elif i < len(self.inputs) - 1:
                        task.name = f'Image {i} Simulation'
                        input.section = self.inputs[i - 1].section.system[-1]
                        task.inputs.append(input)
                        output.section = self.inputs[i].section.calculation[-1]
                        task.outputs.append(output)
                        output_system.section = self.inputs[i].section.system[-1]
                        task.outputs.append(output_system)
                    elif i == len(self.inputs) - 1:
                        task.name = 'Final Image Simulation'
                        input.section = self.inputs[-1].section.system[0]
                        task.inputs.append(input)
                        output.section = self.inputs[-1].section.calculation[-1]
                        task.outputs.append(output)
                    self.tasks.append(task)
            if self.outputs == []:
                output = Link()
                output.section = self.neb_workflow_results
                output.name = 'NEB Workflow Results'
                self.outputs.append(output)

    def extract_total_energy_differences(
        self, logger: 'BoundLogger'
    ) -> Optional[pint.Quantity]:
        """
        Extracts the total energy differences from the task outputs of the NEB workflow.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            Optional[pint.Quantity]: The total energy differences of the system for each of the images in the path
            of configurations in units of energy.
        """
        # Resolve the reference of energies from the first NEB task
        if self.inputs[0].section.calculation[-1].energy.total.value is None:
            logger.error(
                'Could not resolve the initial value of the total energy for referencing.'
            )
            return None

        energy_reference = self.inputs[0].section.calculation[-1].energy.total.value.m
        energy_units = self.inputs[0].section.calculation[-1].energy.total.value.u

        # Append the energy differences of the images w.r.t. the reference of energies
        tot_energies = []
        for input in self.inputs:
            if input.section.calculation[-1].energy.total.value is not None:
                tot_energies.append(
                    input.section.calculation[-1].energy.total.value.m
                    - energy_reference
                )
            else:
                tot_energies.append(None)  # Handle missing values safely

        # Return a pint.Quantity (list of magnitudes with associated unit)
        return tot_energies * energy_units

    def extract_path(self, logger: 'BoundLogger') -> Optional[pint.Quantity]:
        """
        Extracts the path of configurations from the NEB workflow.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            Optional[pint.Quantity]: The path of configurations (reaction coordinate)
            in the NEB workflow.
        """

        path = []
        initial_position = self.inputs[0].section.system[-1].atoms.positions.m
        path_unit = self.inputs[0].section.system[-1].atoms.positions.u
        cell = self.inputs[0].section.system[-1].atoms.lattice_vectors
        pbc = self.inputs[0].section.system[-1].atoms.periodic
        for input in self.inputs:
            if input.section.system[-1].atoms.positions is not None:
                dR = input.section.system[-1].atoms.positions.m - initial_position
                # if cell is not None and pbc is not None:
                #     from ase.geometry import find_mic
                #     dR, _ = find_mic(dR, cell, pbc)
                path.append(np.sqrt((dR**2).sum()))
            else:
                logger.error(
                    'Could not resolve the path of configurations in the NEB workflow.'
                )
                return None
        return path * path_unit

    def get_ase_forces(self, logger: 'BoundLogger') -> Optional[Quantity]:
        ase_forces = []
        for input in self.inputs:
            if input.section.calculation[-1].forces.total.value is not None:
                force = input.section.calculation[-1].forces.total.value.to(
                    'eV/angstrom'
                )
                ase_force = np.transpose(force.m)
                ase_forces.append(ase_force)
            else:
                ase_forces.append(None)  # Handle missing values safely
        return ase_forces

    def get_ase_positions(self, logger: 'BoundLogger') -> Optional[Quantity]:
        ase_positions = []
        for input in self.inputs:
            if input.section.system[-1].atoms.positions is not None:
                position = input.section.system[-1].atoms.positions.to('angstrom')
                ase_position = np.transpose(position.m)
                ase_positions.append(ase_position)
            else:
                ase_positions.append(None)
        return ase_positions

    def plot_energy_vs_position(self, logger: 'BoundLogger') -> None:
        if (
            self.neb_workflow_results.total_energy_differences is not None
            and len(self.neb_workflow_results.total_energy_differences) > 0
        ):
            # If energies are stored as pint.Quantity, extract magnitude and unit
            if hasattr(self.neb_workflow_results.total_energy_differences, 'm'):
                magnitudes = self.neb_workflow_results.total_energy_differences.m
                unit = str(self.neb_workflow_results.total_energy_differences.u)
            else:
                magnitudes = self.neb_workflow_results.total_energy_differences
                unit = 'eV'  # Default unit if missing

            # Custom unit mapping
            unit_mapping = {
                'electron_volt': 'eV',
                'joule': 'J',
                'angstrom': 'Å',
                'nanometer': 'nm',
                # Add more mappings as needed
            }

            if hasattr(self.neb_workflow_results.path, 'u'):
                path_values = self.neb_workflow_results.path.m
                unit_path = str(self.neb_workflow_results.path.u)

            # Use pint to format the unit in a pretty way
            ureg = pint.UnitRegistry(system='short')
            pretty_unit = ureg(unit).units.format_babel()
            pretty_unit = unit_mapping.get(
                pretty_unit, pretty_unit
            )  # Apply custom mapping
            pretty_unit_path = ureg(unit_path).units.format_babel()
            pretty_unit_path = unit_mapping.get(
                pretty_unit_path, pretty_unit_path
            )  # Apply custom mapping

            logger.info(f'Formatted unit: {pretty_unit}, {pretty_unit_path}')

            # Use Plotly Express to create the plot
            fig = px.scatter(
                x=path_values,
                y=magnitudes,
                labels={
                    'x': f'Reaction Coordinate ({pretty_unit_path})',
                    'y': f'Energy Difference ({pretty_unit})',
                },
            )
            fig.add_scatter(
                x=path_values, y=magnitudes, mode='lines', line=dict(shape='linear')
            )

            fig.update_layout(title='NEB Energy Profile', template='plotly_white')

            # Convert to NOMAD-compatible PlotlyFigure
            self.figures.append(
                PlotlyFigure(label='NEB Workflow', figure=fig.to_plotly_json())
            )

    def fit_and_plot_energy_vs_position_ase(self, logger: 'BoundLogger') -> Quantity:
        forces_ase = self.get_ase_forces(logger=logger)
        positions = self.get_ase_positions(logger=logger)
        magnitudes = self.neb_workflow_results.total_energy_differences.m

        pretty_unit = 'eV'
        pretty_unit_path = 'Å'

        from ase.utils.forcecurve import fit_raw, ForceFit

        ForceFit = fit_raw(magnitudes, forces_ase, positions)
        fig1 = px.scatter(
            x=ForceFit.path,
            y=ForceFit.energies,
            labels={
                'x': f'Reaction Coordinate ({pretty_unit_path})',
                'y': f'Energy Difference ({pretty_unit})',
            },
        )
        for x, y in ForceFit.lines:
            fig1.add_scatter(x=x, y=y, mode='lines', line=dict(shape='linear'))
        fig1.add_scatter(
            x=ForceFit.fit_path,
            y=ForceFit.fit_energies,
            mode='lines',
            line=dict(shape='linear'),
        )
        Ef = max(ForceFit.energies)
        index_max = np.argmax(ForceFit.energies)
        path_max = ForceFit.path[index_max]
        Ef_fit = max(ForceFit.fit_energies)
        index_max_fit = np.argmax(ForceFit.fit_energies)
        path_max_fit = ForceFit.fit_path[index_max_fit]
        if Ef_fit - Ef < 0.05 and (path_max_fit - path_max) < 0.05:
            fig1.add_annotation(
                x=ForceFit.path[index_max],
                y=Ef,
                text=f'E<sub>A</sub> {Ef:.2f} eV',
                showarrow=True,
                arrowhead=1,
                xanchor='left',
            )
        else:
            fig1.add_annotation(
                x=ForceFit.fit_path[index_max_fit],
                y=Ef_fit,
                text=f'E<sub>A</sub> (fit) {Ef_fit:.2f} eV',
                showarrow=True,
                arrowhead=1,
                xanchor='left',
            )

        fig1.update_layout(title='NEB Energy Profile ASE', template='plotly_white')

        self.figures.append(
            PlotlyFigure(label='NEB Workflow ASE Fit', figure=fig1.to_plotly_json())
        )

        return Ef_fit

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        try:
            if self.neb_workflow_results is None:
                # Initialize the NEB workflow results section if it doesn't exist
                self.neb_workflow_results = NEBWorkflowResults()
            self.neb_workflow_results.total_energy_differences = (
                self.extract_total_energy_differences(logger=logger)
            )
        except Exception:
            logger.error('Could not set NEBWorkflow.total_energy_differences.')

        # Extract system name from input structure (chemical composition of first image)
        try:
            system_name = self.inputs[0].section.system[-1].chemical_composition_hill
        except (KeyError, IndexError, AttributeError):
            logger.warning(
                'Could not extract system name from the first image in the NEB workflow.'
            )
            system_name = None

        # Dynamically set entry name
        archive.metadata.entry_type = 'NEB Workflow'
        if system_name is not None:
            archive.metadata.entry_name = f'{system_name} NEB Calculation'
        else:
            archive.metadata.entry_name = 'NEB Calculation'

        self.neb_workflow_results.reaction_energy = (
            self.neb_workflow_results.total_energy_differences[-1]
        )
        self.neb_workflow_results.activation_energy = (
            max(self.neb_workflow_results.total_energy_differences)
            - self.neb_workflow_results.total_energy_differences[0]
        )
        try:
            path_distance = self.extract_path(logger=logger)
            self.neb_workflow_results.path = path_distance
        except Exception as e:
            logger.error(f'Could not set NEBWorkflow.path: {e}')

        # Generate NEB energy plot using Plotly Express and store it in self.figures
        try:
            Ef_fit = self.fit_and_plot_energy_vs_position_ase(logger=logger)
            self.neb_workflow_results.activation_energy_fitted = Ef_fit

        except Exception as e:
            logger.error(f'Error while generating NEB energy plot with fit: {e}')
            try:
                self.plot_energy_vs_position(logger=logger)
            except Exception as e:
                logger.error(
                    'Could not generate NEB figure. Error while generating NEB'
                    f'energy plot: {e}'
                )

        self.extend_workflow(archive=archive, logger=logger)


m_package.__init_metainfo__()
