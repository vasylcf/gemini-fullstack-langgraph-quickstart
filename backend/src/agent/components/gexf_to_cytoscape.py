import networkx as nx
import json
import argparse
import os


def networkx_to_cytoscape_json(nx_graph, display_label_attribute='id'):
    """
    Converts a NetworkX graph to a list of elements in Cytoscape.js JSON format.
    """
    elements = []

    # Add nodes
    for i, (node_id_nx, data) in enumerate(nx_graph.nodes(data=True)):
        node_id_str = str(node_id_nx)
        cy_node_data = {'id': node_id_str}
        display_label_content = data.get(display_label_attribute, data.get('label', node_id_str))
        cy_node_data['label_for_display'] = str(display_label_content)
        node_group_label = data.get('labels', 'Unknown')
        cy_node_data['node_group_for_color'] = str(node_group_label)
        raw_pagerank = data.get('pagerank')
        pagerank_value = 0.0001
        if raw_pagerank is not None:
            try:
                pagerank_value = float(raw_pagerank)
            except (ValueError, TypeError):
                print(f"Warning: Could not convert pagerank for node {node_id_str}. Using default.")
        cy_node_data['pagerank_for_size'] = max(pagerank_value, 0.00001)
        # We are removing hover info for now, but will still pass the data
        description_content = data.get('description', 'No description available.')
        cy_node_data['description_for_hover'] = str(description_content)
        for key, value in data.items():
            if key not in cy_node_data:
                cy_node_data[key] = value
        elements.append({'data': cy_node_data, 'group': 'nodes'})

    # Add edges
    if nx_graph.is_multigraph():
        edge_iterator = nx_graph.edges(data=True, keys=True)
        for i, (source, target, key, data) in enumerate(edge_iterator):
            source_id = str(source)
            target_id = str(target)
            edge_id = data.get('id', f"e_{source_id}_{target_id}_{i}")
            cy_edge_data = {'id': edge_id, 'source': source_id, 'target': target_id}
            for k, v in data.items():
                if k not in cy_edge_data:
                    cy_edge_data[k] = v
            elements.append({'data': cy_edge_data, 'group': 'edges'})
    else:
        edge_iterator = nx_graph.edges(data=True)
        for i, (source, target, data) in enumerate(edge_iterator):
            source_id = str(source)
            target_id = str(target)
            edge_id = data.get('id', f"e_{source_id}_{target_id}_{i}")
            cy_edge_data = {'id': edge_id, 'source': source_id, 'target': target_id}
            for k, v in data.items():
                if k not in cy_edge_data:
                    cy_edge_data[k] = v
            elements.append({'data': cy_edge_data, 'group': 'edges'})

    return elements

def create_html_visualization(elements_json_str, output_html_path="output_visualization.html"):
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Cytoscape.js Enhanced COSE Layout</title>
<script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
<style>
    body {{ font-family: helvetica, arial, sans-serif; font-size: 14px; margin: 0; padding: 0; }}
    #cy {{
        width: 100%;
        height: 100vh;
        display: block;
        position: absolute;
        top: 0; left: 0; z-index: 999;
    }}
    h1 {{
        font-size: 1.5em; font-weight: normal; opacity: 0.8;
        position: absolute; left: 10px; top: 10px; z-index: 1000;
    }}
    #cy-tooltip td {{ vertical-align: top; padding-right: 10px; }}
</style>
</head>
<body>
    <h1>Cytoscape.js Graph (COSE Layout - Enhanced)</h1>
    <div id="cy-tooltip" style="
        display: none;
        position: absolute;
        pointer-events: none;
        background: #fffbe9;
        border: 1px solid #aaa;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 13px;
        color: #222;
        box-shadow: 2px 2px 8px #bbb;
        z-index: 2000;
        max-width: 340px;
    "></div>
    <div id="cy"></div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{

            // <<<-- Customizable properties for tooltip -->>>
            const NODE_TOOLTIP_PROPERTIES = ["name","description", "labels"];
            const NODE_TOOLTIP_TITLES = {{
                "name": "Name",
                "labels": "Labels",
                "description": "Description",
            }};
            // <<<-- End customizable section -->>>

            // Helper to build tooltip HTML table
            function buildTooltipContent(nodeData) {{
                let html = "<table>";
                NODE_TOOLTIP_PROPERTIES.forEach(prop => {{
                    if (nodeData[prop] !== undefined) {{
                        html += `<tr><td><b>${{NODE_TOOLTIP_TITLES[prop] || prop}}</b></td><td>${{nodeData[prop]}}</td></tr>`;
                    }}
                }});
                html += "</table>";
                return html;
            }}

            var graphElements = {elements_json_str};

            var uniqueLabels = new Set();
            graphElements.filter(el => el.group === 'nodes').forEach(el => uniqueLabels.add(el.data.node_group_for_color));

            var colorPalette = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f'];
            var labelToColorMap = {{}};
            var labelIndex = 0;
            uniqueLabels.forEach(label => {{
                labelToColorMap[label] = colorPalette[labelIndex % colorPalette.length];
                labelIndex++;
            }});

            var pagerankValues = graphElements.filter(el => el.group === 'nodes' && typeof el.data.pagerank_for_size === 'number')
                                            .map(el => el.data.pagerank_for_size);
            var minPr = Math.min(...pagerankValues);
            var maxPr = Math.max(...pagerankValues);
            var minNodeSize = 15;
            var maxNodeSize = 70;

            if (pagerankValues.length === 0 || minPr === maxPr) {{
                minPr = 0; maxPr = 1;
            }}

            var cy = cytoscape({{
                container: document.getElementById('cy'),
                elements: graphElements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'background-color': function(ele) {{
                                return labelToColorMap[ele.data('node_group_for_color')] || '#808080';
                            }},
                            'label': 'data(label_for_display)',
                            'width': 'mapData(pagerank_for_size, ' + minPr + ', ' + maxPr + ', ' + minNodeSize + ', ' + maxNodeSize + ')',
                            'height': 'mapData(pagerank_for_size, ' + minPr + ', ' + maxPr + ', ' + minNodeSize + ', ' + maxNodeSize + ')',
                            'font-size': '10px',
                            'color': '#000',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'text-outline-width': 1,
                            'text-outline-color': '#fff',
                            'border-width': 1,
                            'border-color': '#555'
                        }}
                    }},
                    {{
                        selector: 'edge',
                        style: {{
                            'width': 1.5,
                            'line-color': '#ccc',
                            'target-arrow-shape': 'none',
                            'curve-style': 'bezier',
                            'opacity': 0.7
                        }}
                    }},
                    {{
                        selector: 'edge[edge_color = "blue"]',
                        style: {{
                            'line-color': '#0066FF',
                            'width': 3,
                            'target-arrow-color': '#0066FF',
                            'opacity': 0.95
                        }}
                    }}
                ],
                layout: {{
                    name: 'cose',
                    idealEdgeLength: 100, nodeOverlap: 20, refresh: 20, fit: true, padding: 30,
                    randomize: false, componentSpacing: 100,
                    nodeRepulsion: function(node){{ return 400000; }},
                    edgeElasticity: function(edge){{ return 100; }},
                    nestingFactor: 5, gravity: 80, numIter: 1000, initialTemp: 200,
                    coolingFactor: 0.95, minTemp: 1.0
                }}
            }});

            // Tooltip logic
            const tooltip = document.getElementById('cy-tooltip');
            let fixedTooltip = false;

            function moveTooltip(e) {{
                if (!fixedTooltip) {{
                    tooltip.style.left = (e.clientX + 16) + 'px';
                    tooltip.style.top = (e.clientY + 16) + 'px';
                }}
            }}

            function showTooltipNearNode(node) {{
                const pos = node.renderedPosition();
                const containerRect = cy.container().getBoundingClientRect();
                let left = containerRect.left + pos.x + 24;
                let top = containerRect.top + pos.y - 16;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
                tooltip.style.display = 'block';
            }}

            cy.on('mouseover', 'node', function(evt) {{
                if (!fixedTooltip) {{
                    evt.target.style('border-color', 'black');
                    evt.target.style('border-width', 3);
                    tooltip.innerHTML = buildTooltipContent(evt.target.data());
                    tooltip.style.display = 'block';
                    cy.container().addEventListener('mousemove', moveTooltip);
                }}
            }});

            cy.on('mouseout', 'node', function(evt) {{
                if (!fixedTooltip) {{
                    evt.target.style('border-color', '#555');
                    evt.target.style('border-width', 1);
                    tooltip.style.display = 'none';
                    cy.container().removeEventListener('mousemove', moveTooltip);
                }}
            }});

            cy.on('tap', 'node', function(evt) {{
                evt.target.select();
                fixedTooltip = true;
                tooltip.innerHTML = buildTooltipContent(evt.target.data());
                showTooltipNearNode(evt.target);
            }});

            cy.on('tap', function(evt) {{
                if (evt.target === cy) {{
                    cy.nodes().unselect();
                    fixedTooltip = false;
                    tooltip.style.display = 'none';
                }}
            }});

            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    cy.nodes().unselect();
                    fixedTooltip = false;
                    tooltip.style.display = 'none';
                }}
            }});
        }});
    </script>
</body>
</html>
"""
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"HTML visualization saved to: {os.path.abspath(output_html_path)}")


def main():
    parser = argparse.ArgumentParser(description="Generate Cytoscape.js HTML visualization from a GEXF file.")
    parser.add_argument("gexf_file", help="Path to the input GEXF file.")
    parser.add_argument("-o", "--output", default="output_visualization.html", help="Path for the output HTML file.")
    parser.add_argument("--label_attr", default="name", help="GEXF node attribute to use for node display labels. Defaults to 'name'.")
    args = parser.parse_args()

    if not os.path.exists(args.gexf_file):
        print(f"Error: GEXF file not found at {args.gexf_file}")
        return

    try:
        G = nx.read_gexf(args.gexf_file)
    except Exception as e:
        print(f"Error reading GEXF file: {e}")
        return

    cytoscape_elements = networkx_to_cytoscape_json(G, display_label_attribute=args.label_attr)
    elements_json_string = json.dumps(cytoscape_elements, indent=2)
    create_html_visualization(elements_json_string, args.output)


if __name__ == "__main__":
    main()


# MATCH (a:Article)
# WHERE a.name IS NULL AND a.title IS NOT NULL
# SET a.name = a.title
# RETURN count(a) AS updated_nodes_count
