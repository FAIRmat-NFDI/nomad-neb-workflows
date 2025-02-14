from typing import TYPE_CHECKING, Optional
import numpy as np
import pint
import plotly.graph_objects as go  # Import Plotly for plotting

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage, Quantity
from simulationworkflowschema import SimulationWorkflow

configuration = config.get_plugin_entry_point(
    'nomad_neb_workflows.schema_packages:nomad_neb_workflows_plugin'
)

m_package = SchemaPackage()


class NEBWorkflow(SimulationWorkflow):
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
            # Something to add: add condition here to check if output.section.energy.total.value.m exists or not
            tot_energies.append(output.section.energy.total.value.m - energy_reference)

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

        try:
            # TODO: improve this naming
            archive.metadata.entry_type = 'NEB'
            archive.metadata.entry_name = 'NEB test'
        except Exception:
            logger.error(
                'Could not set archive.metadata quantities entry_type and entry_name.'
            )

    def plot_energy_vs_position(self, logger: 'BoundLogger') -> None:
        """
        Creates an interactive Plotly plot of the energy differences vs. the image positions.
        The x-axis corresponds to the image positions (1, 2, 3, ...) and the y-axis to the energy differences.

        Args:
            logger (BoundLogger): The logger to log messages.
        """
        if self.total_energy_differences is None:
            logger.error(
                'No energy differences available to plot. Make sure normalization has been run.'
            )
            return

        try:
            # If the energies are stored as a pint.Quantity, extract magnitude and unit
            if hasattr(self.total_energy_differences, 'm'):
                magnitudes = self.total_energy_differences.m
                unit = self.total_energy_differences.u
            else:
                magnitudes = self.total_energy_differences
                unit = ''

            # Create positions as 1, 2, 3, ..., based on the number of energy entries
            positions = list(range(1, len(magnitudes) + 1))

            # Create the interactive plot using Plotly
            fig = go.Figure(
                data=go.Scatter(
                    x=positions, y=magnitudes, mode='lines+markers', marker=dict(size=8)
                )
            )
            fig.update_layout(
                title='NEB Energy Profile',
                xaxis_title='Image Position',
                yaxis_title=f'Energy Difference ({unit})'
                if unit
                else 'Energy Difference',
                template='plotly_white',
            )
            fig.show()
        except Exception as e:
            logger.error('Error while plotting energy vs. position: ' + str(e))


m_package.__init_metainfo__()
