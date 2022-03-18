import errno
import glob
import os
from typing import Optional, Tuple

import attr

from .alignment import AlignmentParameters
from .cluster import Job, JobResourceRequest, make_test_job_resource_request
from .general import write_params_to_file

track_search_algorithms = ["CA", "Follow"]


@attr.s
class ReconstructionParameters:
    def _validate_track_search_algo(instance, attribute, value):
        if value not in track_search_algorithms:
            raise ValueError(f"Must be either of {track_search_algorithms}.")

    num_events_per_sample: int = attr.ib()
    num_samples: int = attr.ib()
    lab_momentum: float = attr.ib()
    low_index: int = attr.ib(default=1)
    output_dir: str = attr.ib(default="")
    lmd_geometry_filename: str = attr.ib(default="Luminosity-Detector.root")
    use_xy_cut: bool = attr.ib(default=False)
    use_m_cut: bool = attr.ib(default=False)
    track_search_algo: str = attr.ib(
        default="CA", validator=_validate_track_search_algo
    )
    reco_ip_offset: Optional[Tuple[float, float, float]] = attr.ib(
        default=None
    )


def generateRecoDirSuffix(
    reco_params: ReconstructionParameters, align_params: AlignmentParameters
):
    reco_dirname_suffix = (
        f"{reco_params.low_index}-"
        + f"{reco_params.low_index + reco_params.num_samples - 1}_"
    )
    if reco_params.use_xy_cut:
        reco_dirname_suffix += "xy_"
    if reco_params.use_m_cut:
        reco_dirname_suffix += "m_"
    if not reco_params.use_xy_cut and not reco_params.use_m_cut:
        reco_dirname_suffix += "un"
    reco_dirname_suffix += "cut"
    if reco_params.use_xy_cut:
        if reco_params.reco_ip_offset:
            reco_dirname_suffix += "_real"
    if align_params.use_point_transform_misalignment:
        if align_params.misalignment_matrices_path == "":
            reco_dirname_suffix += "_no_data_misalignment"
        else:
            reco_dirname_suffix += "_" + str(
                os.path.splitext(
                    os.path.basename(align_params.misalignment_matrices_path)
                )[0]
            )
    if align_params.alignment_matrices_path:
        reco_dirname_suffix += "/aligned-" + str(
            os.path.splitext(
                os.path.basename(align_params.alignment_matrices_path)
            )[0]
        )
    else:
        reco_dirname_suffix += "/no_alignment_correction"
    return reco_dirname_suffix


def create_reconstruction_job(
    reco_params: ReconstructionParameters,
    align_params: AlignmentParameters,
    dirname,
    application_command="runLmdReco.py",
    force_level=0,
    debug=False,
    use_devel_queue=False,
) -> Tuple[Job, str]:
    print(
        "preparing reconstruction in index range "
        + f"{reco_params.low_index} - "
        + f"{reco_params.low_index + reco_params.num_samples - 1}"
    )

    dirname_filter_suffix = generateRecoDirSuffix(reco_params, align_params)

    low_index_used = reco_params.low_index
    num_samples = reco_params.num_samples
    if debug and reco_params.num_samples > 1:
        print(
            "Warning: number of samples in debug mode is limited to 1!"
            " Setting to 1!"
        )
        num_samples = 1

    pathname_base = dirname
    path_mc_data = pathname_base + "/mc_data"
    dirname_full = dirname + "/" + dirname_filter_suffix
    pathname_full = dirname_full

    print("using output folder structure: " + pathname_full)

    try:
        os.makedirs(pathname_full)
        os.makedirs(pathname_full + "/Pairs")
        os.makedirs(path_mc_data)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            print("error: thought dir does not exists but it does...")

    write_params_to_file(reco_params, pathname_full, "reco_params.config")
    write_params_to_file(align_params, pathname_full, "align_params.config")

    resource_request = JobResourceRequest(2 * 60)
    resource_request.number_of_nodes = 1
    resource_request.processors_per_node = 1
    resource_request.memory_in_mb = 3000
    resource_request.node_scratch_filesize_in_mb = 0

    if use_devel_queue:
        resource_request = make_test_job_resource_request()

    job = Job(
        resource_request,
        application_url=application_command,
        name="lmd_reco_",
        logfile_url=pathname_full + "/reco-%a.log",
    )

    job.array_indices = list(
        range(low_index_used, low_index_used + num_samples)
    )

    job.exported_user_variables = {
        "dirname": dirname_full,
        "path_mc_data": path_mc_data,
        "pathname": pathname_full,
        "force_level": str(force_level),
    }

    if os.environ["force_cut_disable"] == "True":
        job.exported_user_variables["force_cut_disable"] = True

    return (job, pathname_full)
