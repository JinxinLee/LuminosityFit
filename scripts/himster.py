from .slurm import SlurmJobHandler
from .cluster import Job


def create_himster_job_handler(
    partition: str, account="m2_him_exp"
) -> SlurmJobHandler:
    def job_preprocessor(job: Job) -> Job:
        # hyperthreading on himster2 virtually increases cpu count by a
        # factor of 2. we want to allocate only real cpus, hence the
        # factors of 2 in the code below
        job.resource_request.processors_per_node *= 2
        job.resource_request.memory_in_mb = int(
            job.resource_request.memory_in_mb / 2
        )
        return job

    return SlurmJobHandler(
        partition=partition,
        account=account,
        constraints="skylake,mhz-2101",
        job_preprocessor=job_preprocessor,
    )
