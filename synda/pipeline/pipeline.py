from typing import TYPE_CHECKING
from jsonschema.exceptions import ValidationError
from sqlmodel import Session, select

from synda.database import engine
from synda.model.run import Run, RunStatus
from synda.model.step import Step, StepStatus
from synda.utils.env import is_debug_enabled

if TYPE_CHECKING:
    from synda.config import Config


class Pipeline:
    def __init__(self, config: "Config"):
        self.config = config
        self.session = Session(engine)
        self.input_loader = config.input.get_loader()
        self.output_saver = config.output.get_saver()
        self.pipeline = config.pipeline
        self.run = None

    def execute(self):
        self.run = Run.create_with_steps(self.session, self.config)
        try:
            input_nodes = self.input_loader.load(self.session)

            for step in self.run.steps:
                if is_debug_enabled():
                    print(step)

                executor = step.get_step_config().get_executor(
                    self.session, self.run, step
                )
                input_nodes = executor.execute_and_update_step(input_nodes)

            self.output_saver.save(input_nodes)

            self.run.update(self.session, RunStatus.FINISHED)
        except Exception as e:
            self.run.update(self.session, RunStatus.ERRORED)
            raise e

    def execute_from_last_failed_step(self):
        try:
            last_failed_step: Step = self.session.exec(
                select(Step).where(Step.status==StepStatus.ERRORED).order_by(Step.id.desc())
            ).first()
            self.run, input_nodes, remaining_steps = Run.restart_from_step(self.session, self.config, last_failed_step)

            for step_ in remaining_steps:
                if is_debug_enabled():
                    print(step_)

                executor = step_.get_step_config().get_executor(
                    self.session, self.run, step_
                )
                input_nodes = executor.execute_and_update_step(input_nodes, restarted=True)

                self.output_saver.save(input_nodes)

            self.run.update(self.session, RunStatus.FINISHED)
        except Exception as e:
            self.run.update(self.session, RunStatus.ERRORED)
            raise e