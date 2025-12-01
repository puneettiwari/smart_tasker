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
    
    async def generate_annotation_sequence(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate annotation sequence from workflow data"""
        
        workflow_summary = {
            "task": workflow_data.get("task"),
            "task_summary": workflow_data.get("task_summary"),
            "steps": []
        }
        
        for step in workflow_data.get("steps", []):
            workflow_summary["steps"].append({
                "step_number": step["step_number"],
                "description": step["description"],
                "instructions": step["instructions"],
                "search_query": step.get("search_query", "")
            })
        
        prompt = f"""You are creating annotation descriptions for a screen recording of someone completing a Microsoft Office task. 

Task: {workflow_data.get('task')}

Summary: {workflow_data.get('task_summary')}

Steps:

{json.dumps(workflow_summary['steps'], indent=2)}

ANNOTATION STYLE REQUIREMENTS:

1. **For regular actions**: Describe BOTH the physical action AND what it results in on the computer

   Example: "I clicked on the Insert tab in the ribbon, which opened the Insert menu and displayed shape insertion options"

   Example: "I typed '8' into the height field, which updated the star's height dimension to 8 centimeters"

2. **For the LAST annotation**: Write a comprehensive paragraph explaining:

   - How you visually confirmed the task is complete

   - The specific elements you checked

   - What you verified (sizes, positions, colors, text, etc.)

   - A statement confirming completion

   

   Example: "To confirm that I've completed the task, I first verified that the star shape is exactly 8 cm in both height and width by checking the Size fields in the Format pane. I then confirmed the star is filled with standard light blue color and has a light blue outline by visually inspecting the shape. I checked the position by looking at the Position section, ensuring it shows 13 cm horizontally and 1 cm vertically. The star appears in the correct location on the slide, matching the specified coordinates. All formatting requirements have been met, marking this task as complete."

3. **VALID Action Types** (use ONLY these exact strings):

   - "click" - Left mouse clicks

   - "right_click" - Right mouse clicks (opens context menus)

   - "input" - Typing text or numbers

   - "drag" - Dragging objects, resizing, creating shapes

   - "key_press" - Keyboard actions (Enter, Tab, Ctrl+C, Alt+Tab, etc.)

   - "scroll" - Scrolling through content

   - "hover" - Hovering over elements (if relevant)

4. **Be specific about UI elements**: 

   - Not "I clicked a button" but "I clicked the Shapes button in the Insert tab"

   - Not "I changed the color" but "I selected light blue from the Standard Colors palette in the Shape Fill dropdown"

5. **Natural conversational tone**: Use first person ("I clicked", "I typed", "I verified")

Respond ONLY with valid JSON (no markdown, no backticks):

{{
  "task": "{workflow_data.get('task')}",
  "task_summary": "{workflow_data.get('task_summary')}",
  "annotation_sequences": [
    {{
      "step_number": 1,
      "step_description": "Brief title for this step",
      "search_query": "the Google search for this step",
      "expected_actions": [
        {{
          "action_type": "click",
          "description": "I clicked on the Google search bar, which activated the input field and positioned my cursor ready to type",
          "expected_element": "Google search input field",
          "expected_input": null,
          "notes": null
        }},
        {{
          "action_type": "input",
          "description": "I typed 'powerpoint insert star shape' into the search bar, which displayed the query text as I typed each character",
          "expected_element": "Google search input",
          "expected_input": "powerpoint insert star shape",
          "notes": null
        }},
        {{
          "action_type": "key_press",
          "description": "I pressed Enter, which submitted the search and loaded the results page showing tutorials about inserting star shapes in PowerPoint",
          "expected_element": "keyboard",
          "expected_input": "Enter",
          "notes": null
        }}
      ],
      "estimated_duration_seconds": 45
    }}
  ],
  "total_steps": 3,
  "total_estimated_actions": 20,
  "annotation_guidelines": "When annotating this recording, focus on capturing the complete flow from searching for information to implementing the changes in PowerPoint. Pay special attention to the Format Shape pane interactions and precise value entries. The final verification should confirm all dimensional, color, and positioning requirements."
}}

CRITICAL: 

- Use ONLY the exact action_type strings listed above: "click", "right_click", "input", "drag", "key_press", "scroll", "hover"

- Last action must be a verification paragraph

- Include both action AND result in every description

- Use first person ("I clicked", "I typed", "I verified")

- Be specific about measurements, colors, positions, and UI elements"""

        response_text = None
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response_text = message.content[0].text.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            annotation_data = json.loads(response_text)
            return annotation_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse annotation sequence: {e}\nResponse: {response_text}")
        except Exception as e:
            raise Exception(f"Error generating annotation sequence: {e}")
    
    async def generate_workflow_with_annotations(self, task: str) -> Dict[str, Any]:
        """Generate workflow AND annotations in a single API call"""
        
        prompt = f"""You are a task breakdown expert creating both a workflow and annotation sequences for a Microsoft Office task.

Task: {task}

Generate BOTH:
1. A focused workflow (3-8 substantial steps, skip basic navigation)
2. Detailed annotation sequences for screen recording

CRITICAL RULES:
- DO NOT include steps for opening files or launching applications
- EVERY step MUST start with Google search actions (search, view results, switch back to app)
- Focus only on the technical implementation steps
- Assume the file is already open and the user starts by searching Google

Respond ONLY with valid JSON (no markdown, no backticks):

{{
  "task": "{task}",
  "task_summary": "brief technical description",
  "simple_explanation": "2-4 sentences explaining what user will accomplish",
  "steps": [
    {{
      "step_number": 1,
      "description": "concise action-focused description",
      "search_query": "specific Google search",
      "expected_results": "what type of results",
      "key_phrases": ["term1", "term2"],
      "alternative_searches": ["backup1", "backup2"],
      "instructions": "detailed technical instructions"
    }}
  ],
  "estimated_time": "10-15 minutes",
  "difficulty": "easy/medium/hard",
  "annotation_sequences": [
    {{
      "step_number": 1,
      "step_description": "Same as step description above",
      "search_query": "Same as step search_query above",
      "expected_actions": [
        {{
          "action_type": "click",
          "description": "I clicked on the Google search bar, which activated the input field and displayed the cursor"
        }},
        {{
          "action_type": "input",
          "description": "I typed 'excel chart rounded bars semicircle' into the search box, which displayed each character as I typed"
        }},
        {{
          "action_type": "key_press",
          "description": "I pressed Enter, which submitted the search and loaded the results page showing Excel chart formatting tutorials"
        }},
        {{
          "action_type": "click",
          "description": "I clicked on the top Microsoft Support result, which opened the tutorial page with instructions on formatting chart bars"
        }},
        {{
          "action_type": "key_press",
          "description": "I pressed Alt+Tab, which switched from the browser back to the Excel window with the chart visible"
        }},
        {{
          "action_type": "click",
          "description": "I clicked on the blue bar in the chart, which selected the entire blue data series and displayed selection handles"
        }},
        {{
          "action_type": "right_click",
          "description": "I right-clicked on the selected blue bar, which opened a context menu with formatting options"
        }},
        {{
          "action_type": "click",
          "description": "I clicked on Format Data Series in the context menu, which opened the Format Data Series pane on the right side"
        }}
      ],
      "estimated_duration_seconds": 45
    }}
  ],
  "total_steps": 3,
  "total_estimated_actions": 20,
  "annotation_guidelines": "Specific guidelines for annotating this task"
}}

ANNOTATION REQUIREMENTS:

1. **Structure for EACH step**:
   - Start with Google search actions (4-5 actions: click search, type query, press Enter, click result, switch back)
   - Then include the actual implementation actions in the application
   - Each action must describe: physical action + what happened on screen

2. **Action types** (use ONLY these exact strings):
   - "click" - Left mouse clicks
   - "right_click" - Right mouse clicks
   - "input" - Typing text/numbers  
   - "drag" - Dragging/resizing objects
   - "key_press" - Keyboard actions (Enter, Tab, Alt+Tab, etc.)
   - "scroll" - Scrolling content
   - "hover" - Hovering over elements

3. **Description format**: 
   "I [action], which [result on screen]"
   Example: "I clicked the Shapes button, which opened a dropdown gallery showing available shape options"

4. **LAST action in ENTIRE workflow**: Must be a comprehensive verification paragraph
   Example: "To confirm the task is complete, I first verified the blue bars have semicircular left edges and red bars have semicircular right edges by visually inspecting the chart. I checked the data labels show both names and percentages in white text, size 10, centered on each bar. I confirmed the VS WordArt is positioned above the bar intersection with gradient fill transitioning from blue at 20% to red at 80%. All requirements have been met, marking this task as complete."

5. **NO fields for**: notes, expected_input, expected_element
   Only include: action_type and description

WORKFLOW GUIDELINES:
- 3-8 substantial steps only
- Skip opening files, launching apps, basic navigation
- Each step is a technical implementation task"""

        response_text = None
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=12000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            combined_data = json.loads(response_text)
            return combined_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response: {e}\nResponse: {response_text}")
        except Exception as e:
            raise Exception(f"Error generating workflow with annotations: {e}")

