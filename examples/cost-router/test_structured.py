#!/usr/bin/env python3
"""Test ChatLiteLLM structured output capability."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM
from pydantic import BaseModel, Field


class Classification(BaseModel):
    complexity: str = Field(description="simple, medium, or complex")
    reasoning: str = Field(description="Brief explanation")


llm = ChatLiteLLM(
    model="replicate/ibm-granite/granite-4.0-h-small",
    temperature=0.3,
)

# Check if with_structured_output works
try:
    structured_llm = llm.with_structured_output(Classification)
    result = structured_llm.invoke(
        [
            SystemMessage(
                content="Classify query complexity as simple, medium, or complex."
            ),
            HumanMessage(content="Classify: What is the capital of France?"),
        ]
    )
    print(f"Structured output: {result}")
except Exception as e:
    print(f"Error with structured output: {e}")

    # Fall back to raw completion
    result = llm.invoke(
        [
            SystemMessage(
                content='Classify query complexity. Respond with JSON: {"complexity": "simple|medium|complex", "reasoning": "..."}'
            ),
            HumanMessage(content="Classify: What is the capital of France?"),
        ]
    )
    print(f"Raw output: {result.content}")
