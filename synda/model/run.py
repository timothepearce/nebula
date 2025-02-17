from datetime import datetime
from enum import Enum
from jsonschema.exceptions import ValidationError
from typing import TYPE_CHECKING

from sqlmodel import Column, Relationship, SQLModel, Session, Field, JSON, select

from synda.model.step import Step, StepStatus
from synda.model.step_node import StepNode
from synda.model.node import Node

if TYPE_CHECKING:
    from synda.config import Config


class RunStatus(str, Enum):
    RUNNING = "running"
    FINISHED = "finished"
    ERRORED = "errored"


class Run(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: RunStatus = Field(default=RunStatus.RUNNING, index=True)
    config: "Config" = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)

    steps: list[Step] = Relationship(back_populates="run")

    @staticmethod
    def create_with_steps(session: Session, config: "Config") -> "Run":
        run = Run(config=config.model_dump())

        session.add(run)
        session.flush()

        steps = [
            Step(
                run_id=run.id,
                position=position,
                type=pipeline_step.type,
                method=pipeline_step.method,
                name=pipeline_step.name,
                step_config=pipeline_step.model_dump(),
                status=StepStatus.PENDING,
                run_at=datetime.now(),
            )
            for position, pipeline_step in enumerate(config.pipeline, start=1)
        ]

        session.add_all(steps)
        session.commit()
        session.refresh(run, ["steps"])

        return run

    @staticmethod
    def restart_from_step(session: Session, config: "Config", step: "Step") -> tuple["Run", list[Node], list[Step]]:
        run = session.exec(select(Run).where(Run.id == step.run_id)).first()
        if run.config != config.model_dump():
            raise ValidationError("The actual config is different from the restarted run config")
        run.update(session, RunStatus.RUNNING)

        input_node_ids: list[StepNode] = session.exec(
            select(StepNode.node_id).where(StepNode.step_id==step.id)
        ).fetchall()
        input_nodes: list[Node] = session.exec(select(Node).where(Node.id.in_(input_node_ids))).fetchall()
        return run, input_nodes, run.steps[step.position-1:]

    def restart_run(self, session: Session, last_failed_step: Step) -> tuple[list[Node],list[Step]]:

        return

    def update(self, session: Session, status: RunStatus) -> "Run":
        self.status = status

        session.add(self)
        session.commit()
        session.refresh(self)
        return self

    def get_config(self) -> "Config":
        return Config.model_validate(self.config)
