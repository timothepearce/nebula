from abc import abstractmethod

from sqlmodel import Session

from synda.model.run import Run
from synda.model.step import Step, StepStatus
from synda.model.node import Node


class Executor:
    def __init__(self, session: Session, run: Run, step_model: Step):
        self.session = session
        self.run = run
        self.step_model = step_model
        self.config = step_model.get_step_config()

    def execute_and_update_step(self, input_nodes: list[Node], restarted: bool=False) -> list[Node]:
        try:
            self.step_model.set_running(self.session, input_nodes, restarted=restarted)

            output_nodes = self.execute(input_nodes)

            self.step_model.set_completed(self.session, input_nodes, output_nodes)

            return output_nodes
        except Exception as e:
            self.step_model.set_status(self.session, StepStatus.ERRORED)
            raise e

    @abstractmethod
    def execute(self, input_data: list[Node]):
        pass
