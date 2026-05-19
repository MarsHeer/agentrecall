"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  listAgents,
  getGraphStats,
  getGraphEntities,
  getGraphRelationships,
  type Agent,
  type GraphEntity,
  type GraphRelationship,
  type GraphStats,
} from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────

interface GraphNode {
  id: string;
  name: string;
  type: string;
  memoryCount: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  connectionCount: number;
  color: string;
  radius: number;
  pinned: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  relationType: string;
  strength: number;
}

// ─── Color palette ───────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  person: "#60a5fa",
  organization: "#a78bfa",
  location: "#34d399",
  event: "#fbbf24",
  concept: "#f472b6",
  skill: "#2dd4bf",
  technology: "#818cf8",
  project: "#fb923c",
  topic: "#c084fc",
  tool: "#f87171",
};

const FALLBACK_COLORS = [
  "#60a5fa", "#a78bfa", "#34d399", "#fbbf24", "#f472b6",
  "#2dd4bf", "#818cf8", "#fb923c", "#c084fc", "#f87171",
  "#e879f9", "#38bdf8", "#4ade80", "#facc15",
];

function getColorForType(type: string): string {
  if (TYPE_COLORS[type.toLowerCase()]) return TYPE_COLORS[type.toLowerCase()];
  let hash = 0;
  for (let i = 0; i < type.length; i++) {
    hash = type.charCodeAt(i) + ((hash << 5) - hash);
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

// ─── Main Component ──────────────────────────────────────────────

export default function GraphPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [entities, setEntities] = useState<GraphEntity[]>([]);
  const [relationships, setRelationships] = useState<GraphRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Graph state
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  // SVG interaction
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    nodeId: string | null;
    offsetX: number;
    offsetY: number;
  }>({ nodeId: null, offsetX: 0, offsetY: 0 });
  const animFrameRef = useRef<number>(0);
  const nodesRef = useRef<GraphNode[]>([]);

  // Keep nodesRef in sync
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  // Load agents
  useEffect(() => {
    listAgents().then((a) => {
      setAgents(a);
      if (a.length > 0) setSelectedAgent(a[0].id);
    }).catch(() => {});
  }, []);

  // Load graph data when agent selected
  useEffect(() => {
    if (!selectedAgent) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [s, e, r] = await Promise.all([
          getGraphStats(selectedAgent),
          getGraphEntities(selectedAgent, undefined, 100),
          getGraphRelationships(selectedAgent, undefined, undefined, 200),
        ]);
        if (cancelled) return;
        setStats(s);
        setEntities(e);
        setRelationships(r);

        // Build graph nodes
        const connectionMap: Record<string, number> = {};
        r.forEach((rel) => {
          connectionMap[rel.source] = (connectionMap[rel.source] || 0) + 1;
          connectionMap[rel.target] = (connectionMap[rel.target] || 0) + 1;
        });

        const width = svgRef.current?.clientWidth || 800;
        const height = svgRef.current?.clientHeight || 500;

        const graphNodes: GraphNode[] = e.map((ent, i) => {
          const conns = connectionMap[ent.name] || 0;
          const angle = (2 * Math.PI * i) / Math.max(e.length, 1);
          const spread = Math.min(width, height) * 0.35;
          return {
            id: ent.name,
            name: ent.name,
            type: ent.type,
            memoryCount: ent.memory_count,
            x: width / 2 + Math.cos(angle) * spread * (0.5 + Math.random() * 0.5),
            y: height / 2 + Math.sin(angle) * spread * (0.5 + Math.random() * 0.5),
            vx: 0,
            vy: 0,
            connectionCount: conns,
            color: getColorForType(ent.type),
            radius: Math.max(6, Math.min(20, 6 + conns * 2)),
            pinned: false,
          };
        });

        const graphEdges: GraphEdge[] = r.map((rel) => ({
          source: rel.source,
          target: rel.target,
          relationType: rel.relation_type,
          strength: rel.strength,
        }));

        setNodes(graphNodes);
        setEdges(graphEdges);
        setSelectedNode(null);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load graph");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [selectedAgent]);

  // ─── Force simulation ──────────────────────────────────────────

  const simulate = useCallback(() => {
    setNodes((prev) => {
      if (prev.length === 0) return prev;
      const next = prev.map((n) => ({ ...n }));
      const nodeMap: Record<string, GraphNode> = {};
      next.forEach((n) => { nodeMap[n.id] = n; });

      const width = svgRef.current?.clientWidth || 800;
      const height = svgRef.current?.clientHeight || 500;
      const centerX = width / 2;
      const centerY = height / 2;

      // Repulsion between all node pairs
      for (let i = 0; i < next.length; i++) {
        for (let j = i + 1; j < next.length; j++) {
          const a = next[i];
          const b = next[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 1) dist = 1;
          const force = 3000 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
          if (!b.pinned) { b.vx += fx; b.vy += fy; }
        }
      }

      // Attraction along edges
      edges.forEach((edge) => {
        const a = nodeMap[edge.source];
        const b = nodeMap[edge.target];
        if (!a || !b) return;
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) dist = 1;
        const idealDist = 120;
        const force = (dist - idealDist) * 0.005;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (!a.pinned) { a.vx += fx; a.vy += fy; }
        if (!b.pinned) { b.vx -= fx; b.vy -= fy; }
      });

      // Center gravity
      next.forEach((n) => {
        if (n.pinned) return;
        n.vx += (centerX - n.x) * 0.001;
        n.vy += (centerY - n.y) * 0.001;
      });

      // Apply velocities with damping
      let moving = false;
      next.forEach((n) => {
        if (n.pinned) {
          n.vx = 0;
          n.vy = 0;
          return;
        }
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
        // Bounds
        n.x = Math.max(n.radius, Math.min(width - n.radius, n.x));
        n.y = Math.max(n.radius, Math.min(height - n.radius, n.y));
        if (Math.abs(n.vx) > 0.1 || Math.abs(n.vy) > 0.1) moving = true;
      });

      return next;
    });
    animFrameRef.current = requestAnimationFrame(simulate);
  }, [edges]);

  useEffect(() => {
    if (nodes.length > 0) {
      animFrameRef.current = requestAnimationFrame(simulate);
    }
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [nodes.length > 0, simulate]);

  // ─── Drag handlers ─────────────────────────────────────────────

  function getSvgCoords(e: React.MouseEvent): { x: number; y: number } {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  function handleMouseDown(nodeId: string, e: React.MouseEvent) {
    e.stopPropagation();
    const pos = getSvgCoords(e);
    const node = nodesRef.current.find((n) => n.id === nodeId);
    if (!node) return;
    dragRef.current = {
      nodeId,
      offsetX: pos.x - node.x,
      offsetY: pos.y - node.y,
    };
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId ? { ...n, pinned: true, vx: 0, vy: 0 } : n
      )
    );
    setSelectedNode(node);
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!dragRef.current.nodeId) return;
    const pos = getSvgCoords(e);
    setNodes((prev) =>
      prev.map((n) =>
        n.id === dragRef.current.nodeId
          ? { ...n, x: pos.x - dragRef.current.offsetX, y: pos.y - dragRef.current.offsetY }
          : n
      )
    );
  }

  function handleMouseUp() {
    if (dragRef.current.nodeId) {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragRef.current.nodeId ? { ...n, pinned: false } : n
        )
      );
    }
    dragRef.current = { nodeId: null, offsetX: 0, offsetY: 0 };
  }

  function handleSvgClick() {
    setSelectedNode(null);
  }

  // ─── Filtered data ─────────────────────────────────────────────

  const filteredNodes = nodes.filter((n) => {
    const matchesSearch = !searchFilter ||
      n.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      n.type.toLowerCase().includes(searchFilter.toLowerCase());
    const matchesType = !typeFilter || n.type === typeFilter;
    return matchesSearch && matchesType;
  });

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));

  const filteredEdges = edges.filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  const allTypes = [...new Set(entities.map((e) => e.type))].sort();

  // Connected entities for selected node
  const connectedEntities = selectedNode
    ? edges
        .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
        .map((e) => ({
          name: e.source === selectedNode.id ? e.target : e.source,
          relation: e.relationType,
          strength: e.strength,
          direction: e.source === selectedNode.id ? "→" : "←",
        }))
    : [];

  // ─── Node lookup map for edges ─────────────────────────────────

  const nodeMap: Record<string, GraphNode> = {};
  nodes.forEach((n) => { nodeMap[n.id] = n; });

  // ─── Render ────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">Graph Explorer</h1>
        <p className="text-[var(--color-text-muted)] text-sm mt-1">
          Visualize entity relationships in your knowledge graph
        </p>
      </div>

      {/* Agent selector */}
      <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-[var(--color-text-muted)]">Agent:</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
          >
            <option value="">Select agent</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          {loading && (
            <div className="w-4 h-4 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
          )}
        </div>
      </div>

      {error && <p className="text-[var(--color-danger)] text-sm">{error}</p>}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
            <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
              Total Entities
            </span>
            <p className="text-2xl font-bold mt-1">{stats.total_entities}</p>
          </div>
          <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
            <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
              Relationships
            </span>
            <p className="text-2xl font-bold mt-1">{stats.total_relationships}</p>
          </div>
          <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
            <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
              Memories in Graph
            </span>
            <p className="text-2xl font-bold mt-1">{stats.total_memories_in_graph}</p>
          </div>
          <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
            <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
              Entity Types
            </span>
            <p className="text-2xl font-bold mt-1">{Object.keys(stats.entity_types).length}</p>
            <div className="flex flex-wrap gap-1 mt-2">
              {Object.entries(stats.entity_types).map(([type, count]) => (
                <span
                  key={type}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                >
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Search / filter bar */}
      <div className="border border-[var(--color-border)] rounded-xl p-4 bg-[var(--color-bg-card)]">
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Search entities..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">All types</option>
            {allTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          {(searchFilter || typeFilter) && (
            <button
              onClick={() => { setSearchFilter(""); setTypeFilter(""); }}
              className="px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] text-xs hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Graph + side panel */}
      <div className="flex gap-4 flex-col lg:flex-row">
        {/* SVG Graph */}
        <div className="flex-1 border border-[var(--color-border)] rounded-xl bg-[var(--color-bg-card)] overflow-hidden min-h-[500px] relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-bg-card)]/80 z-10">
              <div className="w-5 h-5 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          {!loading && nodes.length === 0 && selectedAgent && (
            <div className="absolute inset-0 flex items-center justify-center text-[var(--color-text-muted)] text-sm">
              No entities found for this agent
            </div>
          )}
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox="0 0 800 500"
            className="cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={handleSvgClick}
          >
            {/* Edges */}
            {filteredEdges.map((edge, i) => {
              const src = nodeMap[edge.source];
              const tgt = nodeMap[edge.target];
              if (!src || !tgt) return null;
              const isHighlighted =
                selectedNode &&
                (edge.source === selectedNode.id || edge.target === selectedNode.id);
              return (
                <line
                  key={`${edge.source}-${edge.target}-${i}`}
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={isHighlighted ? "var(--color-accent)" : "var(--color-border)"}
                  strokeWidth={isHighlighted ? 2 : 1}
                  strokeOpacity={isHighlighted ? 0.8 : 0.4}
                />
              );
            })}

            {/* Nodes */}
            {filteredNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              const isConnected =
                selectedNode &&
                edges.some(
                  (e) =>
                    (e.source === selectedNode.id && e.target === node.id) ||
                    (e.target === selectedNode.id && e.source === node.id)
                );
              const dimmed = selectedNode && !isSelected && !isConnected;

              return (
                <g
                  key={node.id}
                  onMouseDown={(e) => handleMouseDown(node.id, e)}
                  style={{ cursor: "grab" }}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.radius}
                    fill={node.color}
                    fillOpacity={dimmed ? 0.2 : isSelected ? 1 : 0.8}
                    stroke={isSelected ? "#fff" : "transparent"}
                    strokeWidth={isSelected ? 2 : 0}
                  />
                  {(isSelected || node.connectionCount > 2 || filteredNodes.length <= 20) && (
                    <text
                      x={node.x}
                      y={node.y + node.radius + 12}
                      textAnchor="middle"
                      fill="var(--color-text)"
                      fontSize="10"
                      opacity={dimmed ? 0.3 : 0.9}
                      style={{ pointerEvents: "none", userSelect: "none" }}
                    >
                      {node.name.length > 16 ? node.name.slice(0, 14) + "…" : node.name}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Side panel */}
        {selectedNode && (
          <div className="w-full lg:w-72 border border-[var(--color-border)] rounded-xl bg-[var(--color-bg-card)] p-4 space-y-4 shrink-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">Entity Details</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] text-lg leading-none"
              >
                ×
              </button>
            </div>

            <div className="space-y-2">
              <div>
                <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  Name
                </span>
                <p className="text-sm font-medium mt-0.5">{selectedNode.name}</p>
              </div>
              <div>
                <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  Type
                </span>
                <p className="mt-0.5">
                  <span
                    className="text-xs px-2 py-0.5 rounded"
                    style={{ backgroundColor: selectedNode.color + "20", color: selectedNode.color }}
                  >
                    {selectedNode.type}
                  </span>
                </p>
              </div>
              <div>
                <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  Memories
                </span>
                <p className="text-sm mt-0.5">{selectedNode.memoryCount}</p>
              </div>
              <div>
                <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  Connections
                </span>
                <p className="text-sm mt-0.5">{connectedEntities.length}</p>
              </div>
            </div>

            {connectedEntities.length > 0 && (
              <div>
                <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  Connected Entities
                </span>
                <div className="mt-1 space-y-1 max-h-48 overflow-y-auto">
                  {connectedEntities.map((ce) => (
                    <div
                      key={ce.name}
                      className="text-xs p-2 rounded bg-[var(--color-bg)] border border-[var(--color-border)]"
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-[var(--color-text-muted)]">{ce.direction}</span>
                        <span className="font-medium truncate">{ce.name}</span>
                      </div>
                      <div className="text-[var(--color-text-muted)] mt-0.5">
                        {ce.relation} · {(ce.strength * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Relationships table */}
      {relationships.length > 0 && (
        <div className="border border-[var(--color-border)] rounded-xl bg-[var(--color-bg-card)]">
          <div className="px-4 py-3 border-b border-[var(--color-border)]">
            <h2 className="text-sm font-semibold">Relationships ({relationships.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide border-b border-[var(--color-border)]">
                  <th className="text-left px-4 py-2">Source</th>
                  <th className="text-left px-4 py-2">Target</th>
                  <th className="text-left px-4 py-2">Type</th>
                  <th className="text-left px-4 py-2">Strength</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {relationships.map((rel, i) => (
                  <tr key={i} className="hover:bg-[var(--color-bg-hover)] transition-colors">
                    <td className="px-4 py-2 font-mono text-xs truncate max-w-[200px]">
                      {rel.source}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs truncate max-w-[200px]">
                      {rel.target}
                    </td>
                    <td className="px-4 py-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
                        {rel.relation_type}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[var(--color-accent)] rounded-full"
                            style={{ width: `${rel.strength * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-[var(--color-text-muted)]">
                          {(rel.strength * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
