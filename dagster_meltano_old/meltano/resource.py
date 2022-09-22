import os
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Union

from dagster import JobDefinition, ScheduleDefinition, resource
from meltano.core.db import project_engine
from meltano.core.logging.utils import setup_logging
from meltano.core.plugin import PluginDefinition, PluginType
from meltano.core.project import Project
from meltano.core.project_plugins_service import ProjectPluginsService
from meltano.core.schedule import Schedule
from meltano.core.schedule_service import ScheduleService
from meltano.core.task_sets import TaskSets
from meltano.core.task_sets_service import TaskSetsService

from dagster_meltano.utils import Singleton

from .extractor import Extractor
from .job import Job


class MeltanoResource(metaclass=Singleton):
    def __init__(self, project_dir: Optional[str] = os.getenv("MELTANO_PROJECT_ROOT")):
        self.project = Project(project_dir)
        setup_logging(self.project)

    @property
    def environment(self) -> str:
        # TODO: replace with dynamic value
        return "dev"

    @property
    @lru_cache
    def session(self):
        return project_engine(self.project)[1]

    @property
    def plugins_service(self) -> ProjectPluginsService:
        return ProjectPluginsService(self.project)

    @property
    def tasks_service(self) -> List[TaskSetsService]:
        return TaskSetsService(self.project)

    @property
    def schedule_service(self) -> ScheduleService:
        return ScheduleService(self.project)

    @property
    def plugins(self) -> Dict[PluginType, List[PluginDefinition]]:
        return self.plugins_service.plugins_by_type()

    @property
    def extractors(self) -> List[Extractor]:
        return [Extractor(extractor, self) for extractor in self.plugins.get(PluginType.EXTRACTORS)]

    @property
    def task_sets(self) -> List[TaskSets]:
        return self.tasks_service.list()

    @property
    def schedules(self) -> Dict[str, Schedule]:
        """
        Returns a dictionary with Meltano job names mapped to Meltano schedules
        """
        return {schedule.job: schedule for schedule in self.schedule_service.schedules()}

    @property
    def jobs(self) -> Iterable[Union[JobDefinition, ScheduleDefinition]]:
        for task_set in self.task_sets:
            job = Job(task_set, meltano=self)
            yield job.dagster_job

            if job.dagster_schedule:
                yield job.dagster_schedule


@resource
def meltano_resource():
    return MeltanoResource()