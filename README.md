# Nebula

A simple synthetic data generator pipeline.

## Pipeline file

```yaml
source:
  type: csv
  properties:
    path: tests/stubs/simple_pipeline/source.csv
    target_column: content
    separator: "\t"

pipeline:
  - type: split
    method: chunk
    parameters:
      size: 500

  - type: generation
    method: llm
    parameters:
      provider: openai
      model: gpt-4o-mini
      template: |
        Ask a question regarding the content.
        content: {chunk}

        Instructions :
        1. Use english only
        2. Keep it short
        
        question: 

  - type: ablation
    method: llm
    parameters:
      provider: openai
      model: gpt-4o-mini
      consensus: all # any, majority
      criteria:
        - Is the text consistent?
        - Is the text only in english?
```
