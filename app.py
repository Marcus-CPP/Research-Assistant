import streamlit as st
import networkx as nx
import math

# Use full wide layout
st.set_page_config(page_title="Graph Analysis Tool", layout="wide")

# CSS: Remove header (Deploy button), page margins, and footers
st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        .block-container {
            padding-top: 0rem !important; padding-bottom: 0rem !important;
            padding-left: 0.5rem !important; padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        footer { display: none !important; }
    </style>
""", unsafe_allow_html=True)

def check_edge_weights_uniqueness(G, vertex_labels, edge_labels):
    """
    Checks if all edge weights wt(e) = phi(u) + phi(e) + phi(v) in graph G are distinct.
    Reports Streamlit error/warning if duplicate weights are detected.
    """
    seen_weights = {}  # Maps sum_val -> (u, v)
    duplicates = []    # Stores duplicate error details

    for u, v in G.edges():
        lbl_e = edge_labels.get((u, v), edge_labels.get((v, u), 0))
        lbl_u = vertex_labels.get(u, 0)
        lbl_v = vertex_labels.get(v, 0)
        
        wt = lbl_u + lbl_e + lbl_v
        
        if wt in seen_weights:
            prev_u, prev_v = seen_weights[wt]
            duplicates.append({
                "weight": wt,
                "edge1": (prev_u, prev_v),
                "edge2": (u, v)
            })
        else:
            seen_weights[wt] = (u, v)

    # Report errors in Streamlit if duplicates exist
    if duplicates:
        error_msg = "⚠️ **Labeling Error: Duplicate Edge Weights Found!**\n"
        for dup in duplicates:
            error_msg += f"- Found same wt(e) = **{dup['weight']}** at edge {dup['edge1']} and edge {dup['edge2']}\n"
        return False, error_msg # Return the string instead of calling st.error()
    
    return True, ""
# ==========================================
# 1. FORMULA & RES CALCULATION
# ==========================================
def calculate_edge_irregular_reflexive(G):
    vertex_labels = {}
    edge_labels = {}
    theoretical_res = 0

    if graph_type == "Path":
    
        # Base manual overrides for n <= 6
        base_v = {1: 0, 2: 0, 3: 0, 4: 2, 5: 0, 6: 2}
        base_e = {(1, 2): 1, (2, 3): 2, (3, 4): 1, (4, 5): 2, (5, 6): 3}

        # 1. Compute Vertex Labels \phi(v_i)
        for i in G.nodes():
            if i in base_v:
                vertex_labels[i] = base_v[i]
            else:
                mod = i % 6
                term = (i + 3) // 3
                if mod in (0, 1, 2):
                    vertex_labels[i] = term - 1
                else:
                    vertex_labels[i] = term
                
        # 2. Compute Edge Labels \phi(e_i)
        for u, v in G.edges():
            i = min(u, v)
            if (1, 2) <= (u, v) <= (5, 6) or (1, 2) <= (v, u) <= (5, 6):
                val = base_e.get((u, v), base_e.get((v, u), 0))
            else:
                mod = i % 6
                term = (i + 3) // 3
                if mod == 0:
                    val = term - 1
                elif mod == 1:
                    val = term
                elif mod == 2:
                    val = term - 1
                elif mod == 3:
                    val = term - 3
                elif mod == 4:
                    val = term - 2
                elif mod == 5:
                    val = term - 1
                val = max(0, val)
                
            edge_labels[(u, v)] = val
            edge_labels[(v, u)] = val

        if n % 6 == 2:
            theoretical_res = (n + 1) // 3
        else:
            theoretical_res = 2 * ((n + 3) // 6)

    elif graph_type == "Star":
    
        # Base manual overrides
        vertex_labels[0] = 0
        base_v = {1: 0, 2: 0}
        base_e = {(0, 1): 1, (0, 2): 2} # Changed to valid star graph edges

        for i in G.nodes():
            if i == 0: 
                continue
            if i in base_v:
                vertex_labels[i] = base_v[i]
            else:
                mod = i % 4
                term = i / 2
                if mod == 0:
                    vertex_labels[i] = int(term)
                elif mod == 1:
                    vertex_labels[i] = math.floor(term)
                elif mod == 2:
                    vertex_labels[i] = int(term) - 1
                else:
                    vertex_labels[i] = math.ceil(term)
                
        # 2. Compute Edge Labels \phi(e_i)
        for u, v in G.edges():
            i = max(u, v) # Changed to max() to get the leaf node index (1 to n)
            
            # Check if this edge is in our base overrides
            if (0, i) in base_e or (i, 0) in base_e:
                val = base_e.get((0, i), base_e.get((i, 0), 0))
            else:
                mod = i % 4
                term = i / 2
                if mod == 0:
                    val = int(term)
                elif mod == 1:
                    val = math.ceil(term)
                elif mod == 2:
                    val = int(term) + 1
                else:
                    val = math.floor(term)
                
            edge_labels[(u, v)] = val
            edge_labels[(v, u)] = val
        
        if n % 4 == 2:
            theoretical_res = math.ceil(n/2) + 1
        else:
            theoretical_res = math.ceil(n/2)

    elif graph_type == "Cycle":

        for i in G.nodes():
            if i <= (n+3)/2:
                vertex_labels[i] = 2*(math.ceil((i+1)/3) - 1)
            else:
                vertex_labels[i] = 2*math.ceil((n - i)/3)

        # 2. Compute Edge Labels \phi(e_i)
        for u, v in G.edges():
            i = min(u, v)
            if (u == 1 and v == n) or (u == n and v == 1):
                val = 2
            elif n % 6 == 3 and ((u == (n+3)/2 and v == (n+5)/2) or (v == (n+3)/2 and u == (n+5)/2)):
                val = 2 * (n // 6)
            elif i <= (n+1)/2:
                val = 2 * math.ceil(i / 3) - 1
            else:
                i = n - i
                val = 2 * math.ceil((i + 1) / 3)
            edge_labels[(u, v)] = val
            edge_labels[(v, u)] = val
        if n % 6 == 2 or n % 6 == 3:
            theoretical_res = math.ceil(n/3) + 1
        else:
            theoretical_res = math.ceil(n/3)

    # Other types of graph

    # Calculate res(G) strictly over active vertices and edges in G
    active_v_vals = [vertex_labels[v] for v in G.nodes() if v in vertex_labels]
    active_e_vals = [edge_labels[(u, v)] for u, v in G.edges() if (u, v) in edge_labels]
    
    max_v = max(active_v_vals) if active_v_vals else 0
    max_e = max(active_e_vals) if active_e_vals else 0
    res_value = max(max_v, max_e)
    
    
    return vertex_labels, edge_labels, res_value, theoretical_res


# ==========================================
# 2. POSITION CALCULATOR
# ==========================================
def compute_svg_positions(G, graph_type, n, width=1600, height=580):
    pos = {}
    col_types = {}
    padding_x = 120
    padding_y = 90
    cx, cy = width / 2, height / 2
    
    if graph_type == "Path" or (graph_type == "Cycle" and n > 30):
        # Grid/Snake Layout for Path, and Cycle when n > 30
        canvas_ratio = (width - 2 * padding_x) / (height - 2 * padding_y)
        cols = math.ceil(math.sqrt(n * canvas_ratio))
        cols = max(1, min(n, cols)) 
        rows = math.ceil(n / cols)
        cols = math.ceil(n / rows)

        step_x = (width - 2 * padding_x) / max(1, cols - 1) if cols > 1 else 0
        step_y = (height - 2 * padding_y) / max(1, rows - 1) if rows > 1 else 0
        
        for i in range(1, n + 1):
            idx = i - 1
            row = idx // cols
            col = idx % cols
            
            # Snake Pattern: physical column on canvas
            physical_col = (cols - 1) - col if row % 2 == 1 else col
                
            x = padding_x + physical_col * step_x
            y = padding_y + row * step_y
            pos[i] = (x, y)
            
            if cols > 1:
                if physical_col == 0:
                    col_types[i] = 'left'
                elif physical_col == cols - 1:
                    col_types[i] = 'right'
                else:
                    col_types[i] = 'center'
            else:
                col_types[i] = 'left'
                
    elif graph_type == "Cycle" and n <= 30:
        # Pure Radial Layout for Cycle when n <= 30
        radius = min(width - 2 * padding_x, height - 2 * padding_y) / 2
        for i in range(1, n + 1):
            angle = 2 * math.pi * (i - 1) / n - math.pi / 2
            pos[i] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            col_types[i] = 'radial'
            
    elif graph_type == "Star":
        pos[0] = (cx, cy)
        col_types[0] = 'center'
        
        if n <= 30:
            r = min(width - 2 * padding_x, height - 2 * padding_y) / 2
            for i in range(1, n + 1):
                angle = 2 * math.pi * (i - 1) / n - math.pi / 2
                pos[i] = (cx + r * math.cos(angle), cy + r * math.sin(angle))
                col_types[i] = 'radial'
        else:
            canvas_w = width - 2 * padding_x
            canvas_h = height - 2 * padding_y
            canvas_ratio = canvas_w / max(1, canvas_h)
            
            cols = math.ceil(math.sqrt((n + 1) * canvas_ratio))
            rows = math.ceil((n + 1) / cols)
            
            if (rows * cols) - 1 < n:
                rows += 1
                
            step_x = canvas_w / max(1, cols - 1)
            step_y = canvas_h / max(1, rows - 1)
            
            center_row, center_col = rows // 2, cols // 2
            leaf_idx = 1
            
            for row in range(rows):
                for col in range(cols):
                    if row == center_row and col == center_col:
                        continue
                    if leaf_idx > n:
                        break
                        
                    x = padding_x + col * step_x
                    y = padding_y + row * step_y
                    pos[leaf_idx] = (x, y)
                    col_types[leaf_idx] = 'radial'
                    leaf_idx += 1
            
    return pos, cx, cy, col_types


# ==========================================
# 3. BALANCED SVG GENERATOR
# ==========================================
def generate_visualgo_svg(G, pos, vertex_labels, edge_labels, res_value, cx, cy, col_types, graph_type, show_labels=True, show_wt=True, width=1600, height=580, n=7):
    k1 = 4.5
    m = max(0.35, min(1.8, k1 / (max(1, n) ** 0.35)))
    V = m * 22.0

    font_val = max(6.0, 0.75 * V)
    font_idx = max(5.0, 0.65 * V)
    font_edge = max(6.0, 0.75 * V)
    
    font_sum = max(3.0, 0.50 * V)
    r_sum = max(4.0, font_sum * 1.15)
    
    r_dot = max(2.5, 4.0 * m)
    stroke_width = max(1.2, 2.0 * m)

    svg = f'<svg id="graph-svg" viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background-color: #ffffff; border-radius: 8px; cursor: grab;">\n'
    
    svg += '  <defs>\n'
    svg += '    <style>\n'
    svg += f'      .v-point {{ fill: #000000; }}\n'
    svg += f'      .v-val-text {{ font-family: sans-serif; font-size: {font_val}px; font-weight: bold; dominant-baseline: central; }}\n'
    svg += f'      .v-idx-text {{ font-family: sans-serif; font-size: {font_idx}px; font-weight: bold; fill: #555555; dominant-baseline: central; }}\n'
    svg += f'      .e-line {{ stroke: #000000; stroke-width: {stroke_width}; fill: none; opacity: 0.1}}\n'
    svg += f'      .e-text {{ font-family: sans-serif; font-size: {font_edge}px; font-weight: bold; text-anchor: middle; dominant-baseline: central; }}\n'
    svg += f'      .e-sum-text {{ font-family: sans-serif; font-size: {font_sum}px; font-weight: bold; fill: #b22222; text-anchor: middle; dominant-baseline: central; }}\n'
    svg += f'      .e-sum-circle {{ fill: #ffffff; stroke: #b22222; stroke-width: {max(0.8, 1.2 * m)}; }}\n'
    svg += '    </style>\n'
    svg += '  </defs>\n'

    svg += '  <g id="maingroup">\n'

    svg += '    <g id="edges">\n'
    
    # Precalculate grid boundaries for wrap-around routing
    if pos:
        min_x = min(p[0] for p in pos.values())
        max_x = max(p[0] for p in pos.values())
    else:
        min_x, max_x = cx, cx
        
    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        
        lbl_e = edge_labels.get((u, v), edge_labels.get((v, u), 0))
        lbl_u = vertex_labels.get(u, 0)
        lbl_v = vertex_labels.get(v, 0)
        sum_val = lbl_u + lbl_e + lbl_v
        
        edge_color = "#d9513c" if lbl_e == res_value and res_value > 0 else "#0011FF"
        
        # Identify the wrap-around cycle edge for large n
        is_wrap_around = (graph_type == "Cycle" and n > 30 and min(u, v) == 1 and max(u, v) == n)
        
        if is_wrap_around:
            px1, py1 = pos[1]
            pxn, pyn = pos[n]
            px_prev, py_prev = pos[n-1]
            
            # Determine if the last row is moving left or right
            is_going_left = pxn <= px_prev
            
            offset_x = 80
            offset_y = 60
            
            if is_going_left:
                # Routes entirely outside the left boundary of the grid
                path_d = f"M {pxn},{pyn} L {min_x - offset_x},{pyn} L {min_x - offset_x},{py1} L {px1},{py1}"
                # Place label on the long vertical segment on the far left
                mx, my = min_x - offset_x, (pyn + py1) / 2.0
                nx_val, ny_val = 1, 0  # Push label rightward slightly from the vertical line
            else:
                # Routes entirely outside the right boundary, over the top, and connects left
                path_d = f"M {pxn},{pyn} L {max_x + offset_x},{pyn} L {max_x + offset_x},{py1 - offset_y} L {min_x - offset_x},{py1 - offset_y} L {min_x - offset_x},{py1} L {px1},{py1}"
                # Place label on the long top horizontal segment above the grid
                mx, my = (max_x + min_x) / 2.0, py1 - offset_y
                nx_val, ny_val = 0, 1  # Push label downward slightly from the horizontal line
                
            svg += f'      <path class="e-line" d="{path_d}" />\n'
            
            offset_edge = font_edge * 1.1
            offset_sum = font_edge * 0.8 + r_sum
            
            lx = mx + nx_val * offset_edge
            ly = my + ny_val * offset_edge
            sx = mx - nx_val * offset_sum
            sy = my - ny_val * offset_sum
            
        else:
            svg += f'      <line class="e-line" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" />\n'
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            
            if graph_type == "Star":
                leaf_idx = max(u, v)
                px, py = pos[leaf_idx]
                dx, dy = px - cx, py - cy
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist > 0:
                    dir_x, dir_y = dx / dist, dy / dist
                    inward_offset_edge = font_val * 2.2
                    lx = px - dir_x * inward_offset_edge
                    ly = py - dir_y * inward_offset_edge
                    
                    inward_offset_sum = inward_offset_edge + (r_sum * 2.2)
                    sx = px - dir_x * inward_offset_sum
                    sy = py - dir_y * inward_offset_sum
                else:
                    lx, ly, sx, sy = px, py, px, py

            elif graph_type in ["Path", "Cycle"] and abs(x2 - x1) < abs(y2 - y1):
                is_left_side = mx < cx
                offset_label = font_edge * 1.1
                gap_sum = font_edge * 0.8 + (2.2 * r_sum)
                
                if is_left_side:
                    lx, ly = mx - offset_label, my
                    sx, sy = mx - offset_label - gap_sum, my
                else:
                    lx, ly = mx + offset_label, my
                    sx, sy = mx + offset_label + gap_sum, my
            else:
                dx, dy = x2 - x1, y2 - y1
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    nx_val, ny_val = -dy / length, dx / length
                else:
                    nx_val, ny_val = 0, -1
                    
                offset_edge = font_edge * 1.1
                offset_sum = font_edge * 0.8 + r_sum
                
                lx = mx + nx_val * offset_edge
                ly = my + ny_val * offset_edge
                sx = mx - nx_val * offset_sum
                sy = my - ny_val * offset_sum
        
        svg += f'      <text class="e-text" x="{lx}" y="{ly}" fill="{edge_color}">{lbl_e}</text>\n'
        
        if show_wt:
            svg += f'      <circle class="e-sum-circle" cx="{sx}" cy="{sy}" r="{r_sum}" />\n'
            svg += f'      <text class="e-sum-text" x="{sx}" y="{sy}">{sum_val}</text>\n'
            
    svg += '    </g>\n'

    svg += '    <g id="vertices">\n'
    for node, (x, y) in pos.items():
        v_val = vertex_labels.get(node, 0)
        vertex_color = "#d9513c" if v_val == res_value and res_value > 0 else "#000000"
        
        c_type = col_types.get(node, 'center')
        svg += f'      <circle class="v-point" cx="{x}" cy="{y}" r="{r_dot}" />\n'
        
        if c_type == 'left':
            val_x = x - (font_val * 0.8)
            svg += f'      <text class="v-val-text" x="{val_x}" y="{y}" text-anchor="end" fill="{vertex_color}">{v_val}</text>\n'
            if show_labels:
                gap = font_val * (0.55 * len(str(v_val)) + 0.7)
                svg += f'      <text class="v-idx-text" x="{val_x - gap}" y="{y}" text-anchor="end">({node})</text>\n'

        elif c_type == 'right':
            val_x = x + (font_val * 0.8)
            svg += f'      <text class="v-val-text" x="{val_x}" y="{y}" text-anchor="start" fill="{vertex_color}">{v_val}</text>\n'
            if show_labels:
                gap = font_val * (0.55 * len(str(v_val)) + 0.7)
                svg += f'      <text class="v-idx-text" x="{val_x + gap}" y="{y}" text-anchor="start">({node})</text>\n'

        elif c_type == 'radial':
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                off_v = font_val * 1.1
                vx = x + (dx / dist) * off_v
                vy = y + (dy / dist) * off_v
                svg += f'      <text class="v-val-text" x="{vx}" y="{vy}" text-anchor="middle" fill="{vertex_color}">{v_val}</text>\n'
                
                if show_labels:
                    off_idx = off_v + (font_idx * 1.3)
                    ix = x + (dx / dist) * off_idx
                    iy = y + (dy / dist) * off_idx
                    svg += f'      <text class="v-idx-text" x="{ix}" y="{iy}" text-anchor="middle">({node})</text>\n'
        else:
            v_offset_above = font_val * 1.1
            svg += f'      <text class="v-val-text" x="{x}" y="{y - v_offset_above}" text-anchor="middle" fill="{vertex_color}">{v_val}</text>\n'
            
            if show_labels:
                offset_idx = font_idx * 1.5
                svg += f'      <text class="v-idx-text" x="{x}" y="{y + offset_idx}" text-anchor="middle">({node})</text>\n'
                
    svg += '    </g>\n'
    svg += '  </g>\n'
    svg += '</svg>\n'
    
    html_with_js = f"""
    {svg}
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const svgElement = d3.select("#graph-svg");
        const gElement = svgElement.select("#maingroup");
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {{
                gElement.attr("transform", event.transform);
            }});
        svgElement.call(zoom);
    </script>
    """
    return html_with_js

# ==========================================
# 4. MAIN APP LAYOUT
# ==========================================

canvas_width = 1600
canvas_height = 580

# Reserve top area for canvas ONLY
canvas_container = st.container()

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# Bottom Compact Control Bar
ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5, ctrl_col6, ctrl_col7 = st.columns([1.5, 0.8, 2.8, 1, 1, 1, 1])

with ctrl_col1:
    selected_function = st.selectbox("Function:", ["Edge Irregular Reflexive"], label_visibility="collapsed")

with ctrl_col2:
    graph_type = st.selectbox("Graph Type:", ["Path", "Cycle", "Star"], label_visibility="collapsed")

with ctrl_col3:
    n = st.slider("Vertices (n):", min_value=3, max_value=500, value=7)

with ctrl_col4:
    show_labels = st.checkbox("Show Index", value=False)

with ctrl_col5:
    show_wt = st.checkbox("Show wt($e_i$)", value=False)

# Build Graph with 1-based indexing [1, 2, ..., n]
node_range = range(1, n + 1)

if graph_type == "Path":
    G = nx.path_graph(node_range)
elif graph_type == "Cycle":
    G = nx.cycle_graph(node_range)
elif graph_type == "Star":
    G = nx.star_graph(n)

pos, cx, cy, col_types = compute_svg_positions(G, graph_type, n, width=canvas_width, height=canvas_height)
vertex_labels, edge_labels, res_value, theoretical_res = calculate_edge_irregular_reflexive(G)
is_valid_labeling, error_msg = check_edge_weights_uniqueness(G, vertex_labels, edge_labels)

with ctrl_col6:
    st.metric(label="res(G)", value=res_value)

with ctrl_col7:
    st.metric(label="Theoretical res(G)", value=theoretical_res)

# Render SVG
html_code = generate_visualgo_svg(
    G, pos, vertex_labels, edge_labels, res_value, cx, cy, col_types, graph_type,
    show_labels=show_labels, show_wt=show_wt, width=canvas_width, height=canvas_height, n=n
)

with canvas_container:
    if not is_valid_labeling:
        st.error(error_msg) # Now renders prominently at the top
    st.components.v1.html(html_code, height=canvas_height + 5, scrolling=False)
