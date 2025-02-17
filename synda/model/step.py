from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Column, SQLModel, Field, Relationship, JSON, Session

from synda.model.step_node import StepNode
from synda.model.node import Node

if TYPE_CHECKING:
    from synda.config.step import Step as StepConfig
    from synda.model.run import Run


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERRORED = "errored"


class Step(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    position: int = Field()
    type: str = Field(index=True)
    method: str = Field()
    name: str = Field(index=True)
    step_config: "StepConfig" = Field(default_factory=dict, sa_column=Column(JSON))
    status: StepStatus = Field(default=StepStatus.PENDING)
    run_at: datetime | None = Field()

    run: "Run" = Relationship(back_populates="steps")

    step_node_links: list["StepNode"] = Relationship(
        back_populates="step",
        sa_relationship_kwargs={"overlaps": "input_step,output_step"},
    )

    input_nodes: list[Node] = Relationship(
        back_populates="input_step",
        link_model=StepNode,
        sa_relationship_kwargs={
            "primaryjoin": "and_(Step.id == StepNode.step_id, StepNode.relationship_type == 'input')",
            "secondaryjoin": "Node.id == StepNode.node_id",
            "secondary": "step_node",
            "overlaps": "output_step,step,step_node_links,node",
        },
    )

    output_nodes: list[Node] = Relationship(
        back_populates="output_step",
        link_model=StepNode,
        sa_relationship_kwargs={
            "primaryjoin": "and_(Step.id == StepNode.step_id, StepNode.relationship_type == 'output')",
            "secondaryjoin": "Node.id == StepNode.node_id",
            "secondary": "step_node",
            "overlaps": "input_nodes,input_step,step,step_node_links,node",
        },
    )

    def set_status(self, session: Session, status: str) -> "Step":
        self.status = status
        session.add(self)
        session.commit()
        session.refresh(self)

        return self

    def set_running(self, session: Session, input_nodes: list[Node], restarted: bool=False) -> "Step":
        self.status = StepStatus.RUNNING
        self.run_at = datetime.now()

        for node in input_nodes:
            if node.id is None:
                session.add(node)
        session.flush()

        for node in input_nodes:
            step_node = StepNode(
                step_id=self.id, node_id=node.id, relationship_type="input"
            )
            if restarted:
                continue
            else:
                session.add(step_node)

        session.add(self)
        session.commit()
        session.refresh(self)

        return self

    def set_completed(
        self, session: Session, input_nodes: list[Node], output_nodes: list[Node]
    ) -> "Step":
        self.status = StepStatus.COMPLETED

        self._create_nodes_with_ancestors(session, input_nodes, output_nodes)
        self._map_nodes_to_step(session, output_nodes)

        session.add(self)
        session.commit()
        session.refresh(self)

        return self

    def _create_nodes_with_ancestors(
        self, session: Session, input_nodes: list[Node], output_nodes: list[Node]
    ):
        for node in output_nodes:
            if node.id is None:
                session.add(node)
        session.flush()

        for node in output_nodes:
            parent_id = node.parent_node_id

            if parent_id is None:
                continue

            parent_node = next(node for node in input_nodes if node.id == parent_id)
            node.ancestors = parent_node.ancestors | {self.name: node.id}
            session.add(node)

    def _map_nodes_to_step(self, session: Session, output_nodes: list[Node]):
        for node in output_nodes:
            step_node = StepNode(
                step_id=self.id, node_id=node.id, relationship_type="output"
            )
            session.add(step_node)

    def get_step_config(self) -> "StepConfig":
        match self.type:
            case "split":
                from synda.config.split import split_adapter

                return split_adapter.validate_python(self.step_config)
            case "generation":
                from synda.config.generation import Generation

                return Generation.model_validate(self.step_config)
            case "ablation":
                from synda.config.ablation import Ablation

                return Ablation.model_validate(self.step_config)
            case "clean":
                from synda.config.clean import Deduplicate

                return Deduplicate.model_validate(self.step_config)
            case _:
                raise ValueError(f"Unknown step type: {self.type}")
