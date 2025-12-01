import os
import json
from anthropic import Anthropic
from typing import Dict, Any, List

class ClaudeService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    async def generate_workflow(self, task: str) -> Dict[str, Any]:
        """Generate workflow steps for a given task"""
        prompt = f"""You are a task breakdown expert. Given a task, provide a focused, efficient workflow.

Task: {task}

IMPORTANT GUIDELINES:

- Skip obvious/basic steps like "Open the file" or "Launch the application"

- Focus ONLY on the specific technical steps needed to complete the task

- Combine simple related actions into single steps

- Each step should require a Google search or specific technical knowledge

- Target 3-8 steps maximum (not 15+ steps)

- Steps should be substantial, not trivial

EXAMPLE OF GOOD WORKFLOW:

Task: "Add rounded bars and gradient text to Excel chart"

✅ GOOD (4 steps):

  1. Modify chart bar shapes to rounded rectangles

  2. Add custom data labels with formatting

  3. Insert and style WordArt gradient text

  4. Apply theme colors

❌ BAD (too many trivial steps):

  1. Open Excel

  2. Click on file

  3. Select the chart

  4. Right-click

  5. Find format option

  ...etc

Respond ONLY with a valid JSON object (no markdown, no backticks):

{{

  "task_summary": "brief description focusing on the technical challenge",

  "simple_explanation": "A clear, simple explanation of what the user will accomplish and why each part matters. Write in friendly, actionable language. Example: 'You'll be modifying an Excel chart to make it more visually appealing. First, you'll round the bar edges to give them a modern look. Then you'll add labels so viewers can see the exact values. Finally, you'll add a VS text with a gradient to create a professional comparison visual.'",

  "steps": [

    {{

      "step_number": 1,

      "description": "concise action-focused description",

      "search_query": "specific technical Google search",

      "expected_results": "what type of results should appear",

      "key_phrases": ["technical term 1", "technical term 2"],

      "alternative_searches": ["backup search 1", "backup search 2"],

      "instructions": "detailed technical instructions with menu paths and settings"

    }}

  ],

  "estimated_time": "realistic time estimate",

  "difficulty": "easy/medium/hard"

}}

CRITICAL: 

- Each step must be technically substantial

- Skip navigation/opening files unless it's a complex or unusual file type

- Focus on the "how to do X" not "how to get to X"

- Provide searches that return technical tutorials, not basic navigation

- Keep total steps between 3-8 for most tasks

- The simple_explanation should be 2-4 sentences that help the user understand the big picture"""

        response_text = None
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = message.content[0].text.strip()
            
            # Clean up response (remove markdown if present)
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            workflow_data = json.loads(response_text)
            
            # Add the original task to the response
            workflow_data["task"] = task
            
            return workflow_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Claude response as JSON: {e}\nResponse: {response_text}")
        except Exception as e:
            raise Exception(f"Error calling Claude API: {e}")
    
    async def verify_search_quality(self, search_query: str, search_results: List[Dict[str, str]], step_description: str) -> Dict[str, Any]:
        """Verify if search results are helpful for the given step"""
        results_text = "\n".join([
            f"{i+1}. {result.get('title', '')}\n   {result.get('snippet', '')}\n   {result.get('link', '')}"
            for i, result in enumerate(search_results)
        ])
        
        prompt = f"""You are evaluating Google search results for a workflow step.

Step Description: {step_description}
Search Query: {search_query}

Search Results:
{results_text}

Respond ONLY with a valid JSON object in this exact format (no markdown, no backticks):
{{
  "is_helpful": true or false,
  "better_query": "improved search query if needed, or null",
  "recommended_result": 1 (index of best result, 1-based)
}}

Evaluate if these results are helpful for completing the step. If not helpful, suggest a better query."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = message.content[0].text.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            verification = json.loads(content)
            return verification
            
        except json.JSONDecodeError as e:
            # Default to helpful if parsing fails
            return {
                "is_helpful": True,
                "better_query": None,
                "recommended_result": 1
            }
        except Exception as e:
            raise RuntimeError(f"Error verifying search quality: {e}")

