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
from typing import List, Optional

configuration = config.get_plugin_entry_point(
    'nomad_neb_workflows.schema_packages:nomad_neb_workflows_plugin'
)

m_package = SchemaPackage()


class NEBWorkflowResults(ArchiveSection):
    """
    A section used to define the results of a Nudged Elastic Band (NEB) workflow. This section contains
    information about the total energy differences and the path of configurations in the NEB workflow
    and will be filled automatically during the workflow normalization based on the linked inputs and tasks calculations.
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
    tasks: Optional[List[TaskReference]] = None
    """
    A base section used to define Nudged Elastic Band (NEB) workflows. These workflows are used to find the
    minimum energy path and transition states between two stable states in a system. It involves interpolating
    a series of intermediate configurations (or images) between the initial and final states, and then optimize
    these images to trace the most energetically favorable path.

    This workflow is useful to extract reaction barriers and energies from a given list
    of images with energy calculations. The workflow yaml should contain a list of entries for initial and final
    states as inputs and references to the image entries in the path between as tasks, ideally containing the
    transition state as well. We currently have also implemented an ase functionality that tries to perform a fit
    if the forces are available from the calculation.


    """

    name = Quantity(
        type=str,
        default='NEB',
        description='Name of the workflow. Default set to `NEB Calculation`.',
    )

    results = SubSection(
        section_def=NEBWorkflowResults,
        repeats=False,
        description='Results of the NEB workflow.',
    )

    def create_workflow_tasks_input_output_and_output(
        self, archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> None:
        for i,task in enumerate(self.tasks):
            input = Link()
            output = Link()
            if i == 0:
                input.section = self.inputs[0].section.run[0]
                input.name = self.inputs[0].name
                task.inputs.append(input)
                self._systems.append(self.inputs[0].section.run[0].system[-1])
                self._systems.append(self.tasks[0].section.run[0].system[-1])
                self._calculations.append(self.inputs[0].section.run[0].calculation[-1])
                self._calculations.append(self.tasks[0].section.run[0].calculation[-1])
                output.section = self.tasks[0].section
                output.name = self.tasks[0].name
                task.outputs.append(output)
            elif i > 0 and i < len(self.tasks) - 1:
                input.section = self.tasks[i-1].section
                input.name = self.tasks[i-1].name
                task.inputs.append(input)
                output.section = self.tasks[i].section
                output.name = self.tasks[i].name
                task.outputs.append(output)
                self._systems.append(self.tasks[i].section.run[0].system[-1])
                self._calculations.append(self.tasks[i].section.run[0].calculation[-1])
            elif i == len(self.tasks) - 1:
                input.section = self.tasks[-2].section
                input.name = self.tasks[-2].name
                task.inputs.append(input)
                output.section = self.inputs[-1].section.run[0]
                output.name = self.inputs[-1].name
                task.outputs.append(output)
                self._systems.append(self.tasks[-1].section.run[0].system[-1])
                self._calculations.append(self.tasks[-1].section.run[0].calculation[-1])
                self._systems.append(self.inputs[-1].section.run[0].system[-1])
                self._calculations.append(self.inputs[-1].section.run[0].calculation[-1])
        
        assert len(self._systems) == len(self._calculations)
        assert len(self._systems) == len(self.tasks)+2
        logger.info('successfully created NEB workflow tasks and outputs.')

        if self.outputs == []:
            output = Link()
            output.section = self.results
            output.name = 'NEB Workflow Results'
            self.outputs.append(output)

    def extract_total_energy_differences(
        self, logger: 'BoundLogger'
    ) -> Optional[pint.Quantity]:
        """
        Extracts the total energy differences from the input and task  sections of the NEB workflow.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            Optional[pint.Quantity]: The total energy differences of the system for each of the images in the path
            of configurations in units of energy.
        """
        # Resolve the reference of energies from the first NEB task
        if self.inputs[0].section.run[0].calculation[-1].energy.total.value is None:
            logger.error(
                'Could not resolve the initial value of the total energy for referencing.'
            )
            return None

        energy_reference = self._calculations[0].energy.total.value.m
        energy_units = self._calculations[0].energy.total.value.u

        # Append the energy differences of the images w.r.t. the reference of energies
        tot_energies = []
        for calculation in self._calculations:
            if calculation.energy.total.value is not None:
                tot_energies.append(
                    calculation.energy.total.value.m
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
        initial_position = self._systems[0].atoms.positions.m
        path_unit = self._systems[0].atoms.positions.u
        
        cell = self._systems[0].atoms.lattice_vectors
        for i in range(1, len(self._systems)):
            assert (cell == self._systems[i].atoms.lattice_vectors).all(), (
                'The lattice vectors of the systems in the NEB workflow are not consistent.'
            )
        pbc = self._systems[0].atoms.periodic
        for system in self._systems:
            if system.atoms.positions is not None:
                dR = system.atoms.positions.m - initial_position
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
        for calculation in self._calculations:
            if calculation.forces.total.value is not None:
                force = calculation.forces.total.value.to(
                    'eV/angstrom'
                )
                ase_force = np.transpose(force.m)
                ase_forces.append(ase_force)
            else:
                ase_forces.append(None)  # Handle missing values safely
        return ase_forces

    def get_ase_positions(self, logger: 'BoundLogger') -> Optional[Quantity]:
        ase_positions = []
        for system in self._systems:
            if system.atoms.positions is not None:
                position = system.atoms.positions.to('angstrom')
                ase_position = np.transpose(position.m)
                ase_positions.append(ase_position)
            else:
                ase_positions.append(None)
        return ase_positions

    def plot_energy_vs_position(self, logger: 'BoundLogger') -> None:
        if (
            self.results.total_energy_differences is not None
            and len(self.results.total_energy_differences) > 0
        ):
            # If energies are stored as pint.Quantity, extract magnitude and unit
            if hasattr(self.results.total_energy_differences, 'm'):
                magnitudes = self.results.total_energy_differences.m
                unit = str(self.results.total_energy_differences.u)
            else:
                magnitudes = self.results.total_energy_differences
                unit = 'eV'  # Default unit if missing

            # Custom unit mapping
            unit_mapping = {
                'electron_volt': 'eV',
                'joule': 'J',
                'angstrom': 'Å',
                'nanometer': 'nm',
                # Add more mappings as needed
            }

            if hasattr(self.results.path, 'u'):
                path_values = self.results.path.m
                unit_path = str(self.results.path.u)

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
        magnitudes = self.results.total_energy_differences.m

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

        fig1.update_layout(title='NEB plot with ASE fit', template='plotly_white')

        self.figures.append(
            PlotlyFigure(label='NEB plot with ASE fit', figure=fig1.to_plotly_json())
        )

        return Ef_fit

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        if self.inputs and len(self.inputs) >= 2:
            # Check if the inputs are a list of NEB images
            if not all(
                isinstance(input, Link) and input.section.run[0].system[-1] is not None
                for input in self.inputs
            ):
                logger.error('Inputs are not a list of NEB images.')
                return
            if not self.tasks or len(self.tasks) == 0:
                logger.warning(
                    'No tasks found in the NEB workflow.'
                )
            elif len(self.tasks) >= 1 and len(self.inputs) == 2:
                self.create_workflow_tasks_input_output_and_output(
                    archive=archive, logger=logger
                )

        # try:
        if self.results is None:
            # Initialize the NEB workflow results section if it doesn't exist
            self.results = NEBWorkflowResults()
        self.results.total_energy_differences = (
            self.extract_total_energy_differences(logger=logger)
        )
        # except Exception:
        #     logger.error('Could not set NEBWorkflow.total_energy_differences.')

        # Extract system name from input structure (chemical composition of first image)
        try:
            system_name = self._systems[0].chemical_composition_hill
        except (KeyError, IndexError, AttributeError):
            logger.warning(
                'Could not extract system name from the first image in the NEB workflow.'
            )
            system_name = None

        # Dynamically set entry name
        archive.metadata.entry_type = 'NEB Workflow'
        if self.inputs[0].name is not ["Input for initial image"]:
            new_entry_name = self.inputs[0].name.replace('Input','').replace('for','')
            archive.metadata.entry_name = new_entry_name
        # elif system_name is not None:
        #     archive.metadata.entry_name = f'{system_name} NEB Calculation'
        # else:
        #     archive.metadata.entry_name = 'NEB Calculation'

        self.results.reaction_energy = (
            self.results.total_energy_differences[-1]
        )
        self.results.activation_energy = (
            max(self.results.total_energy_differences)
            - self.results.total_energy_differences[0]
        )
        try:
            path_distance = self.extract_path(logger=logger)
            self.results.path = path_distance
        except Exception as e:
            logger.error(f'Could not set NEBWorkflow.path: {e}')

        # Generate NEB energy plot using Plotly Express and store it in self.figures
        try:
            Ef_fit = self.fit_and_plot_energy_vs_position_ase(logger=logger)
            self.results.activation_energy_fitted = Ef_fit

        except Exception as e:
            logger.error(f'Error while generating NEB energy plot with fit: {e}')
            try:
                self.plot_energy_vs_position(logger=logger)
            except Exception as e:
                logger.error(
                    'Could not generate NEB figure. Error while generating NEB'
                    f'energy plot: {e}'
                )
        # Add run section from initial input in order to allow automatic visualization of system
        if not archive.run:
            from runschema.run import Run, Program
            run = Run(program=Program())
            try:
                run.system.extend([self.inputs[0].section.run[0].system[-1]])
                run.calculation.extend([self.inputs[0].section.run[0].calculation[-1]])
                run.method = self.inputs[0].section.run[0].method
            except Exception as e:
                logger.warning(f'Failed to link structure from first input archive. Error: {e}')
            archive.run.append(run)

m_package.__init_metainfo__()
