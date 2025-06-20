import React, { useEffect, useRef, useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";

interface GraphViewProps {
  elements: any[];
  style?: React.CSSProperties;
}

// Helper to compute min/max pagerank for scaling node size
function getPagerankRange(elements: any[]) {
  const prValues = elements
    .filter((el) => el.group === "nodes" && typeof el.data.pagerank_for_size === "number")
    .map((el) => el.data.pagerank_for_size);
  if (prValues.length === 0) return { min: 0, max: 1 };
  const min = Math.min(...prValues);
  const max = Math.max(...prValues);
  return min === max ? { min: 0, max: 1 } : { min, max };
}

const minNodeSize = 15;
const maxNodeSize = 70;

// Color palette for node groups
const colorPalette = [
  '#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999',
  '#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#b3b3b3', '#b15928', '#1b9e77', '#d95f02', '#7570b3'
];

function getLabelToColorMap(elements: any[]) {
  const uniqueLabels = Array.from(new Set(
    elements.filter(el => el.group === 'nodes').map(el => el.data.node_group_for_color || 'Unknown')
  ));
  const map: Record<string, string> = {};
  uniqueLabels.forEach((label, idx) => {
    map[label] = colorPalette[idx % colorPalette.length];
  });
  return map;
}

const GraphView: React.FC<GraphViewProps> = ({ elements, style }) => {
  const cyRef = useRef<any>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const { min, max } = getPagerankRange(elements);
  const labelToColorMap = useMemo(() => getLabelToColorMap(elements), [elements]);

  // Dynamic stylesheet with correct min/max for pagerank scaling and color mapping
  const stylesheet = useMemo(() => [
    {
      selector: "node",
      style: {
        "background-color": (ele: any) => labelToColorMap[ele.data('node_group_for_color')] || '#808080',
        "label": "data(label_for_display)",
        "width": `mapData(pagerank_for_size, ${min}, ${max}, ${minNodeSize}, ${maxNodeSize})`,
        "height": `mapData(pagerank_for_size, ${min}, ${max}, ${minNodeSize}, ${maxNodeSize})`,
        "font-size": "10px",
        "color": "#000",
        "text-valign": "center",
        "text-halign": "center",
        "text-outline-width": 1,
        "text-outline-color": "#fff",
        "border-width": 1,
        "border-color": "#555",
      },
    },
    {
      selector: "edge",
      style: {
        "width": 1.5,
        "line-color": "#ccc",
        "target-arrow-shape": "none",
        "curve-style": "bezier",
        "opacity": 0.7,
      },
    },
    {
      selector: "edge[edge_color = 'blue']",
      style: {
        "line-color": "#0066FF",
        "width": 3,
        "target-arrow-color": "#0066FF",
        "opacity": 0.95,
      },
    },
  ], [min, max, labelToColorMap]);

  const layout = {
    name: "cose",
    idealEdgeLength: 100,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: 400000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  };

  const tooltipStyle: React.CSSProperties = {
    position: "fixed",
    pointerEvents: "none",
    background: "#fffbe9",
    border: "1px solid #aaa",
    padding: "8px 12px",
    borderRadius: 8,
    fontSize: 13,
    color: "#222",
    boxShadow: "2px 2px 8px #bbb",
    zIndex: 2000,
    maxWidth: 340,
    display: "none",
  };

  function buildTooltipContent(nodeData: any) {
    return (
      `<table>` +
      `<tr><td><b>Name</b></td><td>${nodeData.name || nodeData.label_for_display || ""}</td></tr>` +
      `<tr><td><b>Description</b></td><td>${nodeData.description_for_hover || nodeData.description || ""}</td></tr>` +
      `<tr><td><b>Labels</b></td><td>${nodeData.labels || nodeData.node_group_for_color || ""}</td></tr>` +
      `</table>`
    );
  }

  useEffect(() => {
    const cy = cyRef.current && cyRef.current._cy;
    const tooltip = tooltipRef.current;
    if (!cy || !tooltip) return;

    function showTooltip(evt: any) {
      if (!tooltip) return;
      const node = evt.target;
      tooltip.innerHTML = buildTooltipContent(node.data());
      tooltip.style.display = "block";
      tooltip.style.left = evt.originalEvent.clientX + 16 + "px";
      tooltip.style.top = evt.originalEvent.clientY + 16 + "px";
    }
    function moveTooltip(evt: any) {
      if (!tooltip) return;
      tooltip.style.left = evt.originalEvent.clientX + 16 + "px";
      tooltip.style.top = evt.originalEvent.clientY + 16 + "px";
    }
    function hideTooltip() {
      if (!tooltip) return;
      tooltip.style.display = "none";
    }
    cy.on("mouseover", "node", showTooltip);
    cy.on("mousemove", "node", moveTooltip);
    cy.on("mouseout", "node", hideTooltip);
    return () => {
      cy.removeListener("mouseover", "node", showTooltip);
      cy.removeListener("mousemove", "node", moveTooltip);
      cy.removeListener("mouseout", "node", hideTooltip);
    };
  }, [elements]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <CytoscapeComponent
        cy={(cy: any) => (cyRef.current = { _cy: cy })}
        elements={elements}
        style={style || { width: "100%", height: "100vh" }}
        layout={layout}
        stylesheet={stylesheet}
      />
      <div ref={tooltipRef} style={tooltipStyle} />
    </div>
  );
};

export default GraphView;