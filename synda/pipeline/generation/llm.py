from sqlmodel import Session

from synda.model.provider import Provider
from synda.model.run import Run
from synda.model.step import Step
from synda.pipeline.executor import Executor
from synda.model.node import Node
from synda.utils.llm_provider import LLMProvider
from synda.utils.prompt_builder import PromptBuilder
from synda.progress_manager import ProgressManager


class LLM(Executor):
    def __init__(self, session: Session, run: Run, step_model: Step):
        super().__init__(session, run, step_model)
        self.progress = ProgressManager("GENERATION")
        self.provider = Provider.get(self.config.parameters.provider)
        self.model = self.config.parameters.model

    def execute(self, input_data: list[Node]):
        template = self.config.parameters.template
        prompts = PromptBuilder.build(self.session, template, input_data)
        result = []
        with self.progress.task("Generating...", len(input_data)) as advance:
            for node, prompt in zip(input_data, prompts):
                llm_answer = LLMProvider.call(
                    self.provider.name,
                    self.model,
                    self.provider.api_key,
                    prompt,
                    url=self.provider.api_url,
                )
                result.append(Node(parent_node_id=node.id, value=llm_answer))
                advance()

        return result
