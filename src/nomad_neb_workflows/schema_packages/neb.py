from typing import TYPE_CHECKING, Optional
import numpy as np
import pint
import plotly.express as px

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Quantity
from simulationworkflowschema.general import SimulationWorkflow
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure

configuration = config.get_plugin_entry_point(
    'nomad_neb_workflows.schema_packages:nomad_neb_workflows_plugin'
)

m_package = SchemaPackage()


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

    total_energy_differences = Quantity(
        type=np.float64,
        shape=['*'],
        unit='eV',
        description="""
        Total energy differences of the system for each of the images in the path. These quantities are
        defined positive.
        """,
    )

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
        ref_image_task = self.tasks[0]
        if ref_image_task.m_xpath('outputs[0].section.energy.total.value') is None:
            logger.error(
                'Could not resolve the initial value of the total energy for referencing.'
            )
            return None

        energy_reference = ref_image_task.outputs[0].section.energy.total.value.m
        energy_units = ref_image_task.outputs[0].section.energy.total.value.u

        # Append the energy differences of the images w.r.t. the reference of energies
        tot_energies = []
        for output in self.outputs:
            if output.section.energy.total.value is not None:
                tot_energies.append(
                    output.section.energy.total.value.m - energy_reference
                )
            else:
                tot_energies.append(None)  # Handle missing values safely

        # Return a pint.Quantity (list of magnitudes with associated unit)
        return tot_energies * energy_units

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        try:
            self.total_energy_differences = self.extract_total_energy_differences(
                logger=logger
            )
        except Exception:
            logger.error('Could not set NEBWorkflow.total_energy_differences.')

        # Extract system name from input structure (chemical composition of first image)
        try:
            system_name = self.tasks[0].inputs[0].section.chemical_composition_hill
        except (KeyError, IndexError, AttributeError):
            system_name = None

        # Dynamically set entry name
        archive.metadata.entry_type = 'NEB Workflow'
        if system_name is not None:
            archive.metadata.entry_name = f'{system_name} NEB Calculation'
        else:
            archive.metadata.entry_name = 'NEB Calculation'

        # Generate NEB energy plot using Plotly Express and store it in self.figures
        try:
            if (
                self.total_energy_differences is not None
                and len(self.total_energy_differences) > 0
            ):
                # If energies are stored as pint.Quantity, extract magnitude and unit
                if hasattr(self.total_energy_differences, 'm'):
                    magnitudes = self.total_energy_differences.m
                    unit = str(self.total_energy_differences.u)
                else:
                    magnitudes = self.total_energy_differences
                    unit = 'eV'  # Default unit if missing

                # Custom unit mapping
                unit_mapping = {
                    'electron_volt': 'eV',
                    'joule': 'J',
                    # Add more mappings as needed
                }

                # Use pint to format the unit in a pretty way
                ureg = pint.UnitRegistry(system='short')
                pretty_unit = ureg(unit).units.format_babel()
                pretty_unit = unit_mapping.get(
                    pretty_unit, pretty_unit
                )  # Apply custom mapping

                logger.info(f'Formatted unit: {pretty_unit}')

                # Create positions as 1, 2, 3, ..., based on the number of energy entries
                positions = list(range(1, len(magnitudes) + 1))

                # Use Plotly Express to create the plot
                fig = px.scatter(
                    x=positions,
                    y=magnitudes,
                    labels={
                        'x': 'Reaction Coordinates',
                        'y': f'Energy Difference ({pretty_unit})',
                    },
                )
                fig.add_scatter(
                    x=positions, y=magnitudes, mode='lines', line=dict(shape='linear')
                )

                fig.update_layout(title='NEB Energy Profile', template='plotly_white')

                # Convert to NOMAD-compatible PlotlyFigure
                self.figures.append(
                    PlotlyFigure(label='NEB Workflow', figure=fig.to_plotly_json())
                )
        except Exception as e:
            logger.error(f'Error while generating NEB energy plot: {e}')


m_package.__init_metainfo__()
