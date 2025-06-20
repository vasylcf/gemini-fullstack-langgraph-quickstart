# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response, Body
from fastapi.staticfiles import StaticFiles
import networkx as nx
import json

from src.agent.components.gexf_to_cytoscape import networkx_to_cytoscape_json

# Define the FastAPI app
app = FastAPI()


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)


@app.post("/graph_vis")
def graph_vis(query: str = Body(..., embed=True)):
    """
    POST endpoint to visualize a GEXF graph as Cytoscape.js JSON elements.
    Args:
        query: Path to the GEXF file (str)
    Returns:
        JSON string of Cytoscape elements

    Example:
        curl -X POST http://127.0.0.1:2024/graph_vis \
            -H "Content-Type: application/json" \
            -d '{"query": "/absolute/path/to/your/file.gexf"}'
    """
    # You may want to validate or sanitize the input in production
    # Print the query for debugging
    print(f"Received query: {query}")
    gexf_file = "/home/vash/apps/gemini-fullstack-langgraph-quickstart/backend/src/assets/sub_graph_20250611_104001.gexf"
    path_gexf_file = pathlib.Path(gexf_file)
    display_label_attribute = 'name'  # or set as needed
    G = nx.read_gexf(path_gexf_file)
    cytoscape_elements = networkx_to_cytoscape_json(G, display_label_attribute)
    elements_json_string = json.dumps(cytoscape_elements, indent=2)
    return Response(content=elements_json_string, media_type="application/json")
