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
def compute_dynamic_svg_positions(edges_tuple, num_vertices, width=1600, height=450):
    
    G = nx.Graph()
    G.add_nodes_from(range(num_vertices))
    G.add_edges_from(edges_tuple)
    
    # 1. Pure geometric layout (no physics simulation that alters topology)
    n = max(len(G.nodes), 1)
    if n <= 30:
        edge_length_factor=1.2
    elif n <= 50:
        edge_length_factor = 1.5
    elif n <= 70:
        edge_length_factor = 1.9
    else:
        edge_length_factor = 2.2

    pos = nx.kamada_kawai_layout(G)
    
    padding_x = 80
    padding_y = 60
    cx, cy = width / 2, height / 2
    
    if len(pos) == 0: return {}, cx, cy, {}, (0, 0, width, height)

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    range_x = max(1e-5, max_x - min_x)
    range_y = max(1e-5, max_y - min_y)
    
    # Aspect-ratio preserving base scale
    avail_w = width - 2 * padding_x
    avail_h = height - 2 * padding_y
    scale = min(avail_w / range_x, avail_h / range_y)
    
    center_x = min_x + range_x / 2
    center_y = min_y + range_y / 2
    
    scaled_pos = {}
    col_types = {}
    for node, (x, y) in pos.items():
        # Pure geometric scalar multiplication preserves exact graph pattern
        sx = cx + (x - center_x) * scale * edge_length_factor
        sy = cy + (y - center_y) * scale * edge_length_factor
        scaled_pos[node] = (sx, sy)
        col_types[node] = 'center'
            
    # Compute new viewBox to ensure everything is visible and centered
    final_xs = [p[0] for p in scaled_pos.values()]
    final_ys = [p[1] for p in scaled_pos.values()]
    
    vb_min_x = min(final_xs) - padding_x
    vb_max_x = max(final_xs) + padding_x
    vb_min_y = min(final_ys) - padding_y
    vb_max_y = max(final_ys) + padding_y
    
    vb_w = vb_max_x - vb_min_x
    vb_h = vb_max_y - vb_min_y
    

    return scaled_pos, cx, cy, col_types, (vb_min_x, vb_min_y, vb_w, vb_h)

def generate_visualgo_svg(G, pos, vertex_labels, edge_labels, res_value, cx, cy, col_types, vb, show_labels=True, show_wt=True, width=1600, height=450):
    n = max(len(G.nodes), 1)
    
    # Tiered shrink rate (m) based on graph size
    if n <= 30:
        m = 0.85
    elif n <= 50:
        m = 0.7
    elif n <= 80:
        m = 0.68
    elif n <= 100:
        m = 0.6
    elif n <= 350:
        m = 0.3
    else:
        m = 0.15
    V = m * 22.0

    font_val = max(6.0, 0.75 * V)
    font_idx = max(5.0, 0.65 * V)
    font_edge = max(6.0, 0.75 * V)
    font_sum = max(3.0, 0.50 * V)
    r_sum = max(4.0, font_sum * 1.15)
    stroke_width = max(1.2, 2.0 * m)
    
    # Revert r_dot back to a small dot
    r_dot = max(2.5, 4.0 * m)  # Small dot size

    vb_x, vb_y, vb_w, vb_h = vb
    svg = f'<svg id="graph-svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background-color: #ffffff; border-radius: 8px; cursor: grab;">\n'
    svg += '  <defs>\n    <style>\n'
    
    # CSS Updates for Inverse Colors
    svg += f'      .v-point {{ stroke: #ffffff; stroke-width: 1px; }}\n'
    # Use stroke to create white halo around vertex labels
    svg += f'      .v-val-text {{ font-family: sans-serif; font-size: {font_val}px; font-weight: bold; fill: #ffffff; dominant-baseline: central; text-anchor: middle; pointer-events: none; paint-order: stroke fill; stroke-width: {max(2.0, font_val * 0.2)}px; stroke-linecap: round; stroke-linejoin: round; }}\n'
    svg += f'      .v-idx-text {{ font-family: sans-serif; font-size: {font_idx}px; font-weight: bold; fill: #555555; dominant-baseline: central; }}\n'
    svg += f'      .e-line {{ stroke: #000000; stroke-width: {stroke_width}; fill: none; opacity: 0.15}}\n'
    
    # Edge text uses SVG "paint-order" to draw a thick white halo around the letters, rendering it perfectly over lines
    svg += f'      .e-text {{ font-family: sans-serif; font-size: {font_edge}px; font-weight: bold; text-anchor: middle; dominant-baseline: central; paint-order: stroke fill; stroke: #ffffff; stroke-width: {max(2.5, font_edge * 0.25)}px; stroke-linecap: round; stroke-linejoin: round; }}\n'
    svg += f'      .e-sum-text {{ font-family: sans-serif; font-size: {font_sum}px; font-weight: bold; fill: #b22222; text-anchor: middle; dominant-baseline: central; }}\n'
    svg += f'      .e-sum-circle {{ fill: #ffffff; stroke: #b22222; stroke-width: {max(0.8, 1.2 * m)}; }}\n'
    svg += '    </style>\n  </defs>\n'
    svg += '  <g id="maingroup">\n    <g id="edges">\n'
        
    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        lbl_e = edge_labels.get((u, v), edge_labels.get((v, u), 0))
        lbl_u = vertex_labels.get(u, 0)
        lbl_v = vertex_labels.get(v, 0)
        sum_val = lbl_u + lbl_e + lbl_v
        
        edge_color = "#d9513c" if lbl_e == res_value and res_value > 0 else "#0011FF"
        svg += f'      <line class="e-line" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" />\n'
        
        # Calculate EXACT midpoint of the edge
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        nx_val, ny_val = (-dy / length, dx / length) if length > 0 else (0, -1)
        
        # Place Edge Label at midpoint
        svg += f'      <text class="e-text" x="{mx}" y="{my}" fill="{edge_color}">{lbl_e}</text>\n'
        
        if show_wt:
            # Offset the edge weight perpendicularly from the midpoint
            offset_sum = (font_edge * 0.8) + r_sum
            sx = mx + nx_val * offset_sum
            sy = my + ny_val * offset_sum
            svg += f'      <circle class="e-sum-circle" cx="{sx}" cy="{sy}" r="{r_sum}" />\n'
            svg += f'      <text class="e-sum-text" x="{sx}" y="{sy}">{sum_val}</text>\n'
            
    svg += '    </g>\n    <g id="vertices">\n'
    for node, (x, y) in pos.items():
        v_val = vertex_labels.get(node, 0)
        
        # Vertex highlights red if it equals the maximum absolute res_value
        vertex_color = "#d9513c" if v_val == res_value and res_value > 0 else "#222222"
        
        # Small dot serving as the background
        svg += f'      <circle class="v-point" cx="{x}" cy="{y}" r="{r_dot}" fill="{vertex_color}" />\n'
        
        # Place vertex label EXACTLY on the dot. 
        # The text is white, with a stroke matching the dot color in case it overflows the dot slightly.
        svg += f'      <text class="v-val-text" x="{x}" y="{y}" stroke="{vertex_color}">{v_val}</text>\n'
        
        if show_labels:
            # Tuck the node index beneath the dot
            offset_idx = r_dot + (font_idx * 1.1)
            svg += f'      <text class="v-idx-text" x="{x}" y="{y + offset_idx}" text-anchor="middle">({node})</text>\n'
                
    svg += '    </g>\n  </g>\n</svg>\n'
    
    html_with_js = f"""
    {svg}
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const svgElement = d3.select("#graph-svg");
        const gElement = svgElement.select("#maingroup");
        const zoom = d3.zoom()
            .scaleExtent([0.02, 100])
            .on("zoom", (event) => {{ gElement.attr("transform", event.transform); }});
        svgElement.call(zoom);
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

with st.sidebar:
    st.header("Graph Parameters")
    
    st.markdown("##### Random Tree Generator")
    rand_col1, rand_col2 = st.columns([1, 1.2])
    
    with rand_col1:
        rand_n_input = st.text_input("Vertices (n)", placeholder="Random")
        
    with rand_col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Generate", use_container_width=True):
            try:
                n_val = int(rand_n_input.strip()) if rand_n_input.strip() else random.randint(5, 30)
                n_val = max(2, min(n_val, 500))
                st.session_state.edges_input_val = generate_random_tree_string(n_val)
            except ValueError:
                st.error("Invalid integer")
                
    st.markdown("---")
    
    edges_input = st.text_area("Edges (u v per line, zero-indexed)", key="edges_input_val", height=250)
    
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
max_vertex_index = -1
try:
    for line in edges_input.strip().split('\n'):
        if line.strip():
            u, v = map(int, line.split())
            edges.append((u, v))
            max_vertex_index = max(max_vertex_index, u, v)
except ValueError:
    st.sidebar.error("Invalid edge format.")

edges_tuple = tuple(edges)
num_vertices = max_vertex_index + 1 if max_vertex_index >= 0 else 0
st.sidebar.markdown(f"**Detected Vertices (n):** `{num_vertices}`")

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
pos, cx, cy, col_types, vb = compute_dynamic_svg_positions(edges_tuple, num_vertices, width=canvas_width, height=canvas_height)

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