from typing import TYPE_CHECKING, Optional
import numpy as np
import pint
import plotly.graph_objects as go  # Import Plotly for plotting
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

    neb_energy_plot = Quantity(
        type=PlotlyFigure,
        description='Plotly figure showing energy vs. path for NEB workflow.',
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

    import plotly.express as px  # Use Plotly Express instead of go.Figure

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        try:
            self.total_energy_differences = self.extract_total_energy_differences(
                logger=logger
            )
        except Exception:
            logger.error('Could not set NEBWorkflow.total_energy_differences.')

        try:
            # Extract system name from input structure (first task input path)
            # if self.tasks and self.tasks[0].inputs:
            #     input_path = self.tasks[0].inputs[0].section
            #     print(input_path)
            #     # Example: '../upload/archive/mainfile/AlCo2S4/neb/00/OUTCAR#/run/0/system/-1'
            #     system_name = input_path.split('/')[-5]  # Extract "AlCo2S4" from path
            #     print(system_name)
            # else:
            #     system_name = "Unknown System"

            # Dynamically set entry name
            archive.metadata.entry_type = 'NEB'
            archive.metadata.entry_name = 'NEB Calculation'
        except Exception:
            logger.error(
                'Could not set archive.metadata quantities entry_type and entry_name.'
            )

        # Generate NEB energy plot using Plotly Express and store it in `neb_energy_plot`
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

                # Create positions as 1, 2, 3, ..., based on the number of energy entries
                positions = list(range(1, len(magnitudes) + 1))

                # Use Plotly Express to create the plot
                fig = px.scatter(
                    x=positions,
                    y=magnitudes,
                    labels={'x': 'Image Position', 'y': f'Energy Difference ({unit})'},
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
