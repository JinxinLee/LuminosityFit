#!/usr/bin/env python3

from dotenv import load_dotenv

load_dotenv(dotenv_path="../lmdEnvFile.env", verbose=True)

import math
import argparse
import os
from pathlib import Path

import cattrs
from lumifit.alignment import AlignmentParameters
from lumifit.experiment import ClusterEnvironment, Experiment, ExperimentType
from lumifit.general import write_params_to_file
#from lumifit.reconstruction import ReconstructionParameters,ReconstructionType
#from lumifit.simulation import SimulationParameters, generateDirectory, SimulationType
from lumifit.reconstruction import ReconstructionParameters
from lumifit.simulation import SimulationParameters, generateDirectory
from lumifit.simulationTypes import SimulationType

# write_params_to_file(asdict(simpars), ".", "simparams.config")
# write_params_to_file(asdict(recopars), ".", "recoparams.config")
# write_params_to_file(cattrs.unstructure(experiment), ".", "experiment.config")


def genExperimentConfig(
    momentum: float,
    theta_min: float,
    theta_max: float,
    phi_min: float,
    phi_max: float,
    ipx: float,
    ipy: float,
    ipz: float,
    experimentType: ExperimentType,
    #simulationType: SimulationType,
    sim_type_for_resAcc: SimulationType,
) -> Experiment:
    simpars = SimulationParameters()
    recopars = ReconstructionParameters()
    alignpars = AlignmentParameters()

    simpars.lab_momentum = momentum
    simpars.num_samples = 100
    simpars.num_events_per_sample = 10000
    simpars.theta_min_in_mrad = theta_min
    simpars.theta_max_in_mrad = theta_max
    simpars.phi_min_in_rad = phi_min
    simpars.phi_max_in_rad = phi_max
    simpars.ip_offset_x = ipx
    simpars.ip_offset_y = ipy
    simpars.ip_offset_z = ipz
    #simpars.sim_type = simulationType

    recopars.lab_momentum = momentum
    recopars.num_samples = 100
    recopars.num_events_per_sample = 10000
    recopars.num_box_samples = 500
    recopars.num_events_per_box_sample = 10000
    recopars.sim_type_for_resAcc = sim_type_for_resAcc
    recopars.reco_ip_offset = (
            ipx,
            ipy,
            ipz,
            )
    recopars.use_xy_cut = False
    recopars.use_m_cut = False

    lmdfit_data_dir = os.getenv("LMDFIT_DATA_DIR")

    if lmdfit_data_dir is None:
        raise ValueError('Please set $LMDFIT_DATA_DIR!')

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


parser = argparse.ArgumentParser()
parser.add_argument(
    "-b", dest="inBetweenMomenta", action=argparse._StoreTrueAction
)


args = parser.parse_args()

confPathPanda = Path("expConfigs/PANDA/8.9_lumi")
confPathPanda.mkdir(parents=True, exist_ok=True)
confPathKoala = Path("expConfigs/KOALA/")
confPathKoala.mkdir(parents=True, exist_ok=True)


theta_min = (2.7, 4.8)
theta_max = (13.0, 20.0)
phi_min = (0.0, 0.0)
phi_max = (6.28318531718, 6.28318531718)
#ip_x = (-1.0, -0.8, -0.6, -0.45, -0.3, -0.15, 0.0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0)
#ip_x = (-0.15, -0.3, -0.45, -0.6)
#ip_x = (-0.8, -1.0, 0)
#ip_x = (0.15, 0.3, 0.45)
#ip_x = (-0.3, 0.0 , 0.3)
#ip_y = (-0.3, 0.0 , 0.3)
#ip_y = (-1.0, -0.8, -0.6, -0.45, -0.3, -0.15, 0.0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0)
#ip_z = (-10.0, -7.5, -5.0, -2.5, 0.0, 2.5, 5.0, 7.5, 10.0)
ip_x =  (0.0, 0.5)
ip_y = (0.0, 0.5)
ip_z = (0.0, 0.5)

if args.inBetweenMomenta:
    momenta = [1.75, 3.5, 9.5, 13.0]
else:
    momenta = [1.5, 4.06, 8.9, 11.91, 15.0]

#for mom in momenta:
for x in ip_x:
    for y in ip_y:
        for z in ip_z:
            max_xy_shift = math.sqrt(
                    x ** 2
                    + y ** 2
                    )
            max_xy_shift = float(
                    "{0:.2f}".format(round(float(max_xy_shift), 2))
                    )
            experiment = genExperimentConfig(
                    8.9,
                    theta_min[0] - max_xy_shift,
                    theta_max[0] + max_xy_shift,
                    phi_min[0],
                    phi_max[0],
                    x,
                    y,
                    z,
                    ExperimentType.LUMI,
                    #SimulationType.BOX,
                    SimulationType.RESACCBOX,
                    )

            write_params_to_file(
                    cattrs.unstructure(experiment), ".", f"{confPathPanda}/test_{x}_{y}_{z}.config"
                    )

#    experiment = genExperimentConfig(
#        mom,
#        theta_min[1],
#        theta_max[1],
#        phi_min[1],
#        phi_max[1],
#        0,
#        0,
#        0,
#        ExperimentType.KOALA,
#        ReconstructionType.PBARP_ELASTIC,
#    )
#
#    write_params_to_file(
#        cattrs.unstructure(experiment), ".", f"{confPathKoala}/{mom}.config"
#    )
