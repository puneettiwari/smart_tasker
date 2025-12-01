from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from pathlib import Path
from .models import TaskRequest, WorkflowResponse, Step, SearchValidation, SearchResult, WorkflowAnnotationSequence, StepAnnotationSequence, AnnotationAction
from .services.claude_service import ClaudeService
from .services.search_service import SearchService

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Task Workflow Generator",
    description="Generate step-by-step workflows with validated Google searches using Claude AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Initialize services
claude_service = ClaudeService()
search_service = SearchService()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend"""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    return HTMLResponse(content="<h1>Task Workflow Generator API</h1><p>Visit /docs for API documentation</p>")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "search_configured": bool(os.getenv("GOOGLE_API_KEY"))
    }

@app.post("/api/generate-workflow", response_model=WorkflowResponse)
async def generate_workflow(request: TaskRequest):
    """
    Generate a step-by-step workflow for the given task.
    Optionally validates Google searches if validate_searches=true.
    """
    try:
        # Step 1: Generate workflow from Claude
        workflow_data = await claude_service.generate_workflow(request.task)
        
        # Step 2: Optionally validate searches
        validated_steps = []
        
        for step_data in workflow_data["steps"]:
            step_dict = {
                "step_number": step_data["step_number"],
                "description": step_data["description"],
                "search_query": step_data["search_query"],
                "expected_results": step_data["expected_results"],
                "key_phrases": step_data["key_phrases"],
                "alternative_searches": step_data["alternative_searches"],
                "instructions": step_data["instructions"],
                "validation": None
            }
            
            if request.validate_searches:
                # Perform actual Google search
                search_results = await search_service.search(step_data["search_query"])
                
                # Ask Claude to verify if results are helpful
                if search_results["has_relevant_results"]:
                    verification = await claude_service.verify_search_quality(
                        step_data["search_query"],
                        search_results["results"][:3],
                        step_data["description"]
                    )
                    
                    # Use better query if suggested
                    if not verification["is_helpful"] and verification["better_query"]:
                        step_dict["search_query"] = verification["better_query"]
                        # Re-search with better query
                        search_results = await search_service.search(verification["better_query"])
                    
                    step_dict["validation"] = {
                        "is_verified": verification["is_helpful"],
                        "search_results": [
                            SearchResult(**result) for result in search_results["results"][:3]
                        ],
                        "recommended_result": verification.get("recommended_result", 1)
                    }
            
            validated_steps.append(Step(**step_dict))
        
        # Step 3: Return complete workflow
        response = WorkflowResponse(
            task=request.task,
            task_summary=workflow_data["task_summary"],
            simple_explanation=workflow_data.get("simple_explanation", "Complete the task by following the steps below."),
            steps=validated_steps,
            total_steps=len(validated_steps),
            estimated_time=workflow_data["estimated_time"],
            difficulty=workflow_data["difficulty"]
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/quick-workflow")
async def quick_workflow(request: TaskRequest):
    """
    Quick workflow generation without validation (faster response).
    Returns raw JSON without Pydantic validation.
    """
    try:
        workflow_data = await claude_service.generate_workflow(request.task)
        return {
            "task": request.task,
            **workflow_data,
            "total_steps": len(workflow_data["steps"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-annotations", response_model=WorkflowAnnotationSequence)
async def generate_annotations(request: TaskRequest):
    """
    Generate annotation sequence for the given task.
    Returns predicted user actions for each step.
    """
    try:
        # First generate the workflow
        workflow_data = await claude_service.generate_workflow(request.task)
        
        # Then generate annotation sequences
        annotation_data = await claude_service.generate_annotation_sequence(workflow_data)
        
        # Convert to response model
        annotation_sequences = []
        for seq in annotation_data["annotation_sequences"]:
            actions = [
                AnnotationAction(**action) 
                for action in seq["expected_actions"]
            ]
            annotation_sequences.append(
                StepAnnotationSequence(
                    step_number=seq["step_number"],
                    step_description=seq["step_description"],
                    search_query=seq["search_query"],
                    expected_actions=actions,
                    estimated_duration_seconds=seq["estimated_duration_seconds"]
                )
            )
        
        response = WorkflowAnnotationSequence(
            task=annotation_data["task"],
            task_summary=annotation_data["task_summary"],
            total_steps=annotation_data["total_steps"],
            annotation_sequences=annotation_sequences,
            total_estimated_actions=annotation_data["total_estimated_actions"],
            annotation_guidelines=annotation_data["annotation_guidelines"]
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating annotations: {str(e)}")

@app.post("/api/quick-annotations")
async def quick_annotations(request: TaskRequest):
    """
    Quick annotation generation without validation.
    Returns raw JSON without Pydantic validation for faster response.
    """
    try:
        workflow_data = await claude_service.generate_workflow(request.task)
        annotation_data = await claude_service.generate_annotation_sequence(workflow_data)
        return annotation_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

