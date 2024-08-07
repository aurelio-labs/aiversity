import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import colorsys

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def generate_color_palette(n):
    HSV_tuples = [(x * 1.0 / n, 0.5, 0.9) for x in range(n)]
    rgb_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))
    return [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in rgb_tuples]

def create_dissertation_quality_layout(plan):
    levels = sorted(plan['levels'], key=lambda x: x['order'], reverse=True)
    max_tasks = max(len(level['tasks']) for level in levels)
    
    # Generate a color palette for tasks
    task_colors = generate_color_palette(max_tasks)
    status_colors = {
        'Completed': 'rgb(102, 187, 106)',
        'In Progress': 'rgb(255, 167, 38)',
        'Not Started': 'rgb(189, 189, 189)'
    }

    # Create subplot figure with 2 rows: 1 for title, 1 for the main chart
    fig = make_subplots(rows=2, cols=1, row_heights=[0.1, 0.9], vertical_spacing=0.03)

    # Add title to the first row
    fig.add_annotation(
        text=f"Plan Structure Visualization:<br>{plan['name']}",
        xref="paper", yref="paper",
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=24, color="#333333"),
        align="center",
    )

    for i, level in enumerate(levels):
        level_name = f"Level {level['order']}"
        
        # Add cover-all box for the level
        fig.add_shape(
            type="rect",
            x0=0.02, y0=i-0.45, x1=0.98, y1=i+0.45,
            line=dict(color="rgba(50, 171, 96, 0.7)", width=2),
            fillcolor="rgba(50, 171, 96, 0.1)",
            layer='below',
            row=2, col=1
        )
        
        # Add level label
        fig.add_annotation(
            x=-0.01, y=i,
            text=level_name,
            showarrow=False,
            xanchor="right",
            font=dict(size=16, color="#444444", family="Arial"),
            row=2, col=1
        )

        # Calculate task widths based on text length
        task_widths = [len(task['name']) for task in level['tasks']]
        total_width = sum(task_widths)
        task_positions = []
        current_pos = 0.05  # Start from 5% of the width

        for width in task_widths:
            task_width = (width / total_width) * 0.9  # Use 90% of the total width
            task_positions.append((current_pos, current_pos + task_width))
            current_pos += task_width + 0.02  # Add a small gap between tasks

        # Add tasks
        for j, (task, (x0, x1)) in enumerate(zip(level['tasks'], task_positions)):
            x = (x0 + x1) / 2
            y = i

            # Add task box
            fig.add_shape(
                type="rect",
                x0=x0, y0=y-0.3, x1=x1, y1=y+0.3,
                line=dict(color=task_colors[j], width=2),
                fillcolor=f"rgba{task_colors[j][3:-1]}, 0.3)",
                layer='below',
                row=2, col=1
            )

            # Add task label
            fig.add_annotation(
                x=x, y=y,
                text=task['name'],
                showarrow=False,
                font=dict(size=12, color="#333333", family="Arial"),
                align="center",
                row=2, col=1
            )

            # Add status indicator
            fig.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=x1-0.02, y0=y+0.2, x1=x1, y1=y+0.3,
                fillcolor=status_colors.get(task['status'], 'rgb(189, 189, 189)'),
                line_color=status_colors.get(task['status'], 'rgb(189, 189, 189)'),
                row=2, col=1
            )

            # Add arrow to next level's cover-all box
            if i < len(levels) - 1:
                fig.add_annotation(
                    x=x, y=y+0.3,
                    ax=0.5, ay=i+1-0.45,
                    xref="x", yref="y", axref="x", ayref="y",
                    text="",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1,
                    arrowcolor="rgba(100,100,100,0.5)",
                    row=2, col=1
                )

        # Add main arrow to next level if not the last level
        if i < len(levels) - 1:
            fig.add_annotation(
                x=0.5, y=i+0.5,
                ax=0.5, ay=i+1-0.5,
                xref="x", yref="y", axref="x", ayref="y",
                text="", showarrow=True,
                arrowhead=2, arrowsize=1.5, arrowwidth=2,
                arrowcolor="rgb(50, 50, 50)",
                row=2, col=1
            )

    # Update layout
    fig.update_layout(
        showlegend=False,
        height=250 * len(levels) + 100,
        width=1200,
        plot_bgcolor='rgba(240,240,240,0.8)',
        paper_bgcolor='rgb(250,250,250)',
        margin=dict(l=50, r=50, t=100, b=50)
    )

    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.1], row=2, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, len(levels)-0.5], row=2, col=1)

    # Add legend for task status
    legend_y = -0.05 / len(levels)  # Position legend below the chart
    for status, color in status_colors.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=color),
            name=status,
            legendgroup="status",
            showlegend=True
        ), row=2, col=1)
    
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=legend_y,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        )
    )

    return fig

def main():
    file_path = 'f1f1b256-1c4e-44fc-bf78-d08cce9c5930.json'
    plan_data = read_json_file(file_path)
    fig = create_dissertation_quality_layout(plan_data)
    fig.write_html("dissertation_quality_plan_visualization.html", auto_open=True)

if __name__ == "__main__":
    main()