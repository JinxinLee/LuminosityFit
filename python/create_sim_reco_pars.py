#!/usr/bin/env python3

from dotenv import load_dotenv

load_dotenv(dotenv_path="../lmdEnvFile.env", verbose=True)

import os
from pathlib import Path

import cattrs
from lumifit.alignment import AlignmentParameters
from lumifit.experiment import ClusterEnvironment, Experiment, ExperimentType
from lumifit.general import write_params_to_file
from lumifit.reconstruction import ReconstructionParameters
from lumifit.simulation import SimulationParameters, generateDirectory

# write_params_to_file(asdict(simpars), ".", "simparams.config")
# write_params_to_file(asdict(recopars), ".", "recoparams.config")
# write_params_to_file(cattrs.unstructure(experiment), ".", "experiment.config")


def genExperimentConfig(momentum: float, experimentType: Experiment):
    simpars = SimulationParameters()
    recopars = ReconstructionParameters()
    alignpars = AlignmentParameters()

    simpars.lab_momentum = momentum
    simpars.num_samples = 100
    simpars.num_events_per_sample = 100000

    recopars.lab_momentum = momentum
    recopars.num_samples = 100
    recopars.num_events_per_sample = 100000
    recopars.num_box_samples = 500
    recopars.num_events_per_box_sample = 100000

    lmdfit_data_dir = os.getenv("LMDFIT_DATA_DIR")
    dirname = generateDirectory(simpars, alignpars)

    experiment = Experiment(
        experimentType,
        ClusterEnvironment.HIMSTER,
        simpars,
        recopars,
        alignpars,
        Path(lmdfit_data_dir + "/" + dirname),
    )

    return experiment


confPathPanda = Path("expConfigs/PANDA/")
confPathPanda.mkdir(parents=True, exist_ok=True)
confPathKoala = Path("expConfigs/KOALA/")
confPathKoala.mkdir(parents=True, exist_ok=True)

for mom in (1.5, 4.06, 8.9, 11.91, 15):

    experiment = genExperimentConfig(mom, ExperimentType.LUMI)

    write_params_to_file(
        cattrs.unstructure(experiment), ".", f"{confPathPanda}/{mom}.config"
    )

    experiment = genExperimentConfig(mom, ExperimentType.KOALA)
    write_params_to_file(
        cattrs.unstructure(experiment), ".", f"{confPathKoala}/{mom}.config"
    )
