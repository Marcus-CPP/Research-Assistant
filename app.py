import streamlit as st
import networkx as nx
import math
import random
from ortools.sat.python import cp_model

# ==========================================
# 1. UI CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Reflexive Edge Labeling", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important; padding-bottom: 0rem !important;
            padding-left: 1rem !important; padding-right: 1rem !important;
            max-width: 100% !important;
        }
        footer { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ALGORITHMS & GENERATORS
# ==========================================
def get_theoretical_res(edges, num_vertices):
    E = len(edges)
    if E == 0: return 0
    S = math.ceil(E / 3)
    if E % 6 in [2, 3]: S += 1

    return S

@st.cache_data(show_spinner=False)
def construct_and_evaluate_labeling(edges_tuple, num_vertices):
    """
    Minimizes res = max(k_E, 2k_V)
    where k_E is max edge label, and 2k_V is max vertex label.
    """
    edges = list(edges_tuple)
    E = len(edges)
    if E == 0: return 0, {}, {}, {}
        
    model = cp_model.CpModel()
    MAX_BOUND = max(num_vertices * 3, 10)
    
    # Base V_half variables
    V_half = [model.NewIntVar(0, MAX_BOUND, f'V_half_{i}') for i in range(num_vertices)]
    
    # Actual Vertex Labels: 2 * V_half
    V_labels = [model.NewIntVar(0, 2 * MAX_BOUND, f'V_{i}') for i in range(num_vertices)]
    for i in range(num_vertices):
        model.Add(V_labels[i] == 2 * V_half[i])
        
    # Edge Labels
    E_labels = [model.NewIntVar(1, 2 * MAX_BOUND, f'E_{i}') for i in range(E)]
    
    # Track the max of edges (k_E) and max of vertices (2k_V)
    k_e = model.NewIntVar(0, 2 * MAX_BOUND, 'k_e')
    k_v_actual = model.NewIntVar(0, 2 * MAX_BOUND, 'k_v_actual')
    
    model.AddMaxEquality(k_e, E_labels)
    model.AddMaxEquality(k_v_actual, V_labels)
    
    # res = max(k_E, 2k_V)
    res_var = model.NewIntVar(0, 2 * MAX_BOUND, 'res_var')
    model.AddMaxEquality(res_var, [k_e, k_v_actual])
    
    # Edge Weights W(e) = L(u) + L(v) + L(e)
    weights = []
    for i, (u, v) in enumerate(edges):
        w = model.NewIntVar(1, 6 * MAX_BOUND, f'W_{i}') 
        model.Add(w == V_labels[u] + V_labels[v] + E_labels[i])
        weights.append(w)
        
    # Constraint: Distinct weights
    model.AddAllDifferent(weights)
    
    # Objective: Minimize our exact definition of res
    model.Minimize(res_var)

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False 
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        vertex_labels = {i: solver.Value(V_labels[i]) for i in range(num_vertices)}
        edge_labels = {}
        edge_weights = {}
        for i in range(E):
            u, v = edges[i]
            val = solver.Value(E_labels[i])
            wt = solver.Value(weights[i])
            edge_labels[(u, v)] = val
            edge_labels[(v, u)] = val
            edge_weights[(u, v)] = wt
        
        evaluated_res = solver.Value(res_var)
        return evaluated_res, vertex_labels, edge_labels, edge_weights

    return -1, {}, {}, {}

def generate_random_tree_string(n):
    if n <= 1: return ""
    edges = []
    for i in range(1, n):
        parent = random.randint(0, i - 1)
        edges.append((parent, i))
        
    labels = list(range(n))
    random.shuffle(labels)
    shuffled_edges = [(labels[u], labels[v]) for u, v in edges]
    
    return "\n".join([f"{u} {v}" for u, v in shuffled_edges])

# ==========================================
# 3. VISUALIZATION HELPERS
# ==========================================
def check_edge_weights_uniqueness(G, vertex_labels, edge_labels):
    seen_weights = {}
    duplicates = []
    for u, v in G.edges():
        lbl_e = edge_labels.get((u, v), edge_labels.get((v, u), 0))
        lbl_u = vertex_labels.get(u, 0)
        lbl_v = vertex_labels.get(v, 0)
        wt = lbl_u + lbl_e + lbl_v
        
        if wt in seen_weights:
            prev_u, prev_v = seen_weights[wt]
            duplicates.append({"weight": wt, "edge1": (prev_u, prev_v), "edge2": (u, v)})
        else:
            seen_weights[wt] = (u, v)

    if duplicates:
        error_msg = "⚠️ **Labeling Error: Duplicate Edge Weights Found!**\n"
        for dup in duplicates:
            error_msg += f"- Found same wt(e) = **{dup['weight']}** at edge {dup['edge1']} and edge {dup['edge2']}\n"
        return False, error_msg 
    return True, ""

@st.cache_data(show_spinner=False)
def compute_dynamic_svg_positions(edges_tuple, num_vertices, r_vertex=18.0):
    G = nx.Graph()
    G.add_nodes_from(range(num_vertices))
    G.add_edges_from(edges_tuple)

    if num_vertices == 0:
        return {}, 0, 0, {}, (0, 0, 1600, 450)
    if num_vertices == 1:
        pad = r_vertex * 4
        return {0: (0.0, 0.0)}, 0.0, 0.0, {0: 'center'}, (-pad, -pad, pad * 2, pad * 2)

    # 1. Compute base topology layout (Kamada-Kawai for small/medium, Spring for large n)
    if num_vertices <= 150:
        raw_pos = nx.kamada_kawai_layout(G)
    else:
        raw_pos = nx.spring_layout(G, k=1.0 / math.sqrt(num_vertices), iterations=100, seed=42)

    nodes = list(raw_pos.keys())
    coords = {u: [float(raw_pos[u][0]), float(raw_pos[u][1])] for u in nodes}

    # 2. Scale world space by nearest-neighbor distance rather than a fixed pixel box
    nn_dists = []
    for i, u in enumerate(nodes):
        ux, uy = coords[u]
        min_d = float('inf')
        for j, v in enumerate(nodes):
            if i == j:
                continue
            d = math.hypot(ux - coords[v][0], uy - coords[v][1])
            if d < min_d:
                min_d = d
        if min_d < float('inf'):
            nn_dists.append(min_d)

    nn_dists.sort()
    ref_dist = nn_dists[max(0, len(nn_dists) // 4)] if nn_dists else 1.0
    target_nn_dist = r_vertex * 3.8  # Comfortable spacing between connected/nearby nodes
    scale = target_nn_dist / max(ref_dist, 1e-5)

    for u in nodes:
        coords[u][0] *= scale
        coords[u][1] *= scale

    # 3. Fast sweep-and-prune collision resolution so no two vertex circles ever overlap
    min_sep = r_vertex * 2.7  # Guarantees clear gap outside circle borders
    for _ in range(60):
        sorted_nodes = sorted(nodes, key=lambda u: coords[u][0])
        moved = False
        for i in range(len(sorted_nodes)):
            u = sorted_nodes[i]
            ux, uy = coords[u]
            for j in range(i + 1, len(sorted_nodes)):
                v = sorted_nodes[j]
                dx = coords[v][0] - ux
                if dx >= min_sep:
                    break  # Remaining nodes are farther away on X-axis
                dy = coords[v][1] - uy
                dist = math.hypot(dx, dy)
                if dist < min_sep:
                    moved = True
                    if dist < 1e-4:
                        angle = (u * 2.39996) % (2 * math.pi)
                        nx_dir, ny_dir = math.cos(angle), math.sin(angle)
                    else:
                        nx_dir, ny_dir = dx / dist, dy / dist
                    push = (min_sep - dist) * 0.5
                    coords[u][0] -= nx_dir * push
                    coords[u][1] -= ny_dir * push
                    coords[v][0] += nx_dir * push
                    coords[v][1] += ny_dir * push
        if not moved:
            break

    scaled_pos = {u: (coords[u][0], coords[u][1]) for u in nodes}
    col_types = {u: 'center' for u in nodes}

    xs = [p[0] for p in scaled_pos.values()]
    ys = [p[1] for p in scaled_pos.values()]
    padding = r_vertex * 3.0

    vb_min_x = min(xs) - padding
    vb_max_x = max(xs) + padding
    vb_min_y = min(ys) - padding
    vb_max_y = max(ys) + padding

    vb_w = vb_max_x - vb_min_x
    vb_h = vb_max_y - vb_min_y
    cx = (vb_min_x + vb_max_x) / 2.0
    cy = (vb_min_y + vb_max_y) / 2.0

    return scaled_pos, cx, cy, col_types, (vb_min_x, vb_min_y, vb_w, vb_h)


def generate_visualgo_svg(G, pos, vertex_labels, edge_labels, res_value, cx, cy, col_types, vb, show_labels=True, show_wt=True, width=1600, height=450):
    r_vertex = 18.0  # Fixed world-space radius for clear outer vertex circles

    # Auto-fit font size to the widest vertex label so digits never cross the circle border
    max_v_val = max(vertex_labels.values()) if vertex_labels else 0
    max_digits = max(1, len(str(max_v_val)))
    inner_chord = r_vertex * 1.72
    font_val = min(14.5, inner_chord / (0.62 * max_digits))

    font_idx = 11.0
    font_edge = 12.5
    font_sum = 9.5
    r_sum = 10.5
    stroke_width = 1.8

    vb_x, vb_y, vb_w, vb_h = vb
    # Estimate initial screen-to-world zoom ratio to hide clutter when zoomed far out on large graphs
    initial_screen_scale = min(width / max(vb_w, 1.0), height / max(vb_h, 1.0))
    hide_text_initially = initial_screen_scale < 0.42
    initial_lod_class = "lod-hidden" if hide_text_initially else ""

    svg = f'<svg id="graph-svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background-color: #ffffff; border-radius: 8px; cursor: grab;">\n'
    svg += '  <defs>\n    <style>\n'
    svg += f'      .v-circle {{ fill: #ffffff; stroke: #222222; stroke-width: 2.2px; }}\n'
    svg += f'      .v-val-text {{ font-family: sans-serif; font-size: {font_val:.2f}px; font-weight: bold; fill: #000000; dominant-baseline: central; text-anchor: middle; pointer-events: none; transition: opacity 0.15s; }}\n'
    svg += f'      .v-idx-text {{ font-family: sans-serif; font-size: {font_idx}px; font-weight: bold; fill: #555555; dominant-baseline: central; pointer-events: none; transition: opacity 0.15s; }}\n'
    svg += f'      .e-line {{ stroke: #000000; stroke-width: {stroke_width}; fill: none; opacity: 0.22; }}\n'
    svg += f'      .e-text {{ font-family: sans-serif; font-size: {font_edge}px; font-weight: bold; fill: #000000; text-anchor: middle; dominant-baseline: central; paint-order: stroke fill; stroke: #ffffff; stroke-width: 3.5px; stroke-linecap: round; stroke-linejoin: round; pointer-events: none; transition: opacity 0.15s; }}\n'
    svg += f'      .e-sum-text {{ font-family: sans-serif; font-size: {font_sum}px; font-weight: bold; fill: #b22222; text-anchor: middle; dominant-baseline: central; pointer-events: none; }}\n'
    svg += f'      .e-sum-circle {{ fill: #ffffff; stroke: #b22222; stroke-width: 1.2px; }}\n'
    svg += f'      .lod-item {{ transition: opacity 0.15s; }}\n'
    svg += f'      .lod-hidden {{ opacity: 0 !important; }}\n'
    svg += '    </style>\n  </defs>\n'
    svg += '  <g id="maingroup">\n    <g id="edges">\n'

    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        lbl_e = edge_labels.get((u, v), edge_labels.get((v, u), 0))
        lbl_u = vertex_labels.get(u, 0)
        lbl_v = vertex_labels.get(v, 0)
        sum_val = lbl_u + lbl_e + lbl_v

        svg += f'      <line class="e-line" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" />\n'

        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        nx_val, ny_val = (-dy / length, dx / length) if length > 0 else (0, -1)

        svg += f'      <text class="e-text lod-item {initial_lod_class}" x="{mx}" y="{my}">{lbl_e}</text>\n'

        if show_wt:
            offset_sum = (font_edge * 0.85) + r_sum
            sx = mx + nx_val * offset_sum
            sy = my + ny_val * offset_sum
            svg += f'      <g class="lod-item {initial_lod_class}">\n'
            svg += f'        <circle class="e-sum-circle" cx="{sx}" cy="{sy}" r="{r_sum}" />\n'
            svg += f'        <text class="e-sum-text" x="{sx}" y="{sy}">{sum_val}</text>\n'
            svg += '      </g>\n'

    svg += '    </g>\n    <g id="vertices">\n'
    for node, (x, y) in pos.items():
        v_val = vertex_labels.get(node, 0)

        svg += f'      <circle class="v-circle" cx="{x}" cy="{y}" r="{r_vertex}" />\n'
        svg += f'      <text class="v-val-text lod-item {initial_lod_class}" x="{x}" y="{y}">{v_val}</text>\n'

        if show_labels:
            offset_idx = r_vertex + (font_idx * 0.95)
            svg += f'      <text class="v-idx-text lod-item {initial_lod_class}" x="{x}" y="{y + offset_idx}" text-anchor="middle">({node})</text>\n'

    svg += '    </g>\n  </g>\n</svg>\n'

    html_with_js = f"""
    {svg}
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const svgElement = d3.select("#graph-svg");
        const gElement = svgElement.select("#maingroup");
        const baseScale = {initial_screen_scale:.6f};

        const zoom = d3.zoom()
            .scaleExtent([0.05, 50])
            .on("zoom", (event) => {{
                gElement.attr("transform", event.transform);
                // Effective pixel size on screen determines whether labels are readable
                const effectiveScale = baseScale * event.transform.k;
                svgElement.selectAll(".lod-item").classed("lod-hidden", effectiveScale < 0.42);
            }});

        svgElement.call(zoom);
        svgElement.on("dblclick.zoom", () => {{
            svgElement.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
        }});
    </script>
    """
    return html_with_js

# ==========================================
# 4. MAIN APP LAYOUT & LOGIC
# ==========================================
canvas_width = 1600
canvas_height = 450

if "edges_input_val" not in st.session_state:
    st.session_state.edges_input_val = "0 1\n0 2\n0 3\n1 4\n1 5"
if "rand_n_box" not in st.session_state:
    st.session_state.rand_n_box = ""  # Keeps the "Random" placeholder on initial load
if "gen_error" not in st.session_state:
    st.session_state.gen_error = ""

def parse_edges(edges_str):
    parsed = []
    max_v = -1
    for line in edges_str.strip().split('\n'):
        if line.strip():
            u, v = map(int, line.split())
            parsed.append((u, v))
            max_v = max(max_v, u, v)
    n = max_v + 1 if max_v >= 0 else 0
    return parsed, n

def on_generate_click():
    raw_val = st.session_state.rand_n_box.strip()
    try:
        n_val = int(raw_val) if raw_val else random.randint(5, 30)
        n_val = max(2, min(n_val, 500))
        st.session_state.edges_input_val = generate_random_tree_string(n_val)
        st.session_state.rand_n_box = str(n_val)
        st.session_state.gen_error = ""
    except ValueError:
        st.session_state.gen_error = "Invalid integer"

def on_edges_change():
    try:
        _, n = parse_edges(st.session_state.edges_input_val)
        st.session_state.rand_n_box = str(n) if n > 0 else ""
    except ValueError:
        pass

with st.sidebar:
    st.header("Graph Parameters")
    
    st.markdown("##### Random Tree Generator")
    rand_col1, rand_col2 = st.columns([1, 1.2])
    
    with rand_col1:
        st.text_input("Vertices (n)", key="rand_n_box", placeholder="Random")
        
    with rand_col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        st.button("Generate", use_container_width=True, on_click=on_generate_click)
        
    if st.session_state.gen_error:
        st.error(st.session_state.gen_error)
                
    st.markdown("---")
    
    edges_input = st.text_area(
        "Edges (u v per line, zero-indexed)",
        key="edges_input_val",
        height=250,
        on_change=on_edges_change
    )
    
    st.components.v1.html("""
        <script>
            const doc = window.parent.document;
            const textareas = doc.querySelectorAll('textarea');
            textareas.forEach(ta => {
                ta.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        ta.blur();
                    }
                });
            });
        </script>
    """, height=0, width=0)

edges = []
num_vertices = 0
try:
    edges, num_vertices = parse_edges(edges_input)
except ValueError:
    st.sidebar.error("Invalid edge format.")

edges_tuple = tuple(edges)

G = nx.Graph()
G.add_nodes_from(range(num_vertices))
G.add_edges_from(edges)

# Calculate standard parameter-based theoretical res
theoretical_res = get_theoretical_res(edges, num_vertices)

with st.spinner("Solver is computing optimal absolute labels..."):
    res_value, vertex_labels, edge_labels, _ = construct_and_evaluate_labeling(edges_tuple, num_vertices)

graph_container = st.container()
controls_container = st.container()

with controls_container:
    st.markdown("---")
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 1.5, 2, 2])

    with ctrl_col1:
        show_labels = st.checkbox("Show Index", value=False)

    with ctrl_col2:
        show_wt = st.checkbox("Show wt($e_i$)", value=False)

    with ctrl_col3:
        st.metric(label="Evaluated res(G) [Absolute Max]", value=res_value if res_value != -1 else "No Solution")

    with ctrl_col4:
        st.metric(label="Theoretical res(G) [k parameter]", value=theoretical_res)

is_valid_labeling, error_msg = check_edge_weights_uniqueness(G, vertex_labels, edge_labels)
pos, cx, cy, col_types, vb = compute_dynamic_svg_positions(edges_tuple, num_vertices)
html_code = generate_visualgo_svg(
    G, pos, vertex_labels, edge_labels, res_value, cx, cy, col_types, vb,
    show_labels=show_labels, show_wt=show_wt, width=canvas_width, height=canvas_height
)

with graph_container:
    if not is_valid_labeling and res_value != -1:
        st.error(error_msg)
    elif res_value == -1:
        st.error("Solver failed to find a valid reflexive labeling for this graph.")
    
    st.components.v1.html(html_code, height=canvas_height, scrolling=False)
