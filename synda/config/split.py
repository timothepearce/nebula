from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from synda.config.step import Step
from synda.model.step import Step as StepModel
from synda.pipeline.executor import Executor


class ChunkParameters(BaseModel):
    size: int = Field(
        default=500, gt=0, lt=10000, description="Size of each chunk in characters"
    )


class ChunkSplit(Step):
    type: Literal["split"]
    method: Literal["chunk"]
    parameters: ChunkParameters

    def get_executor(self, step_model: StepModel) -> Executor:
        from synda.pipeline.split import Chunk
        return Chunk(step_model)


class SeparatorParameters(BaseModel):
    separator: str = Field(
        default=".", description="The separator character(s)"
    )


class SeparatorSplit(Step):
    type: Literal["split"]
    method: Literal["separator"]
    parameters: SeparatorParameters

    def get_executor(self, step_model: StepModel) -> Executor:
        from synda.pipeline.split import Separator
        return Separator(step_model)


Split = Annotated[
    Union[ChunkSplit, SeparatorSplit],
    Field(discriminator='method')
]

split_adapter = TypeAdapter(Split)
