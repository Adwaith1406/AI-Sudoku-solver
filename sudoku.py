import copy
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

# =====================================================================
# 1. CORE CSP AI ENGINE
# =====================================================================

class SudokuCSP:

    def __init__(self, board):
        self.variables = [(r, c) for r in range(9) for c in range(9)]
        self.neighbors = {v: set() for v in self.variables}
        self._build_constraints()

        self.domains = {}
        for r in range(9):
            for c in range(9):
                val = board[r][c]
                self.domains[(r, c)] = {val} if val != 0 else set(range(1, 10))

        self.backtracks = 0
        self.pruned_count = 0

    def _build_constraints(self):
        for r, c in self.variables:
            for i in range(9):
                if i != c:
                    self.neighbors[(r, c)].add((r, i))
                if i != r:
                    self.neighbors[(r, c)].add((i, c))
            br, bc = 3 * (r // 3), 3 * (c // 3)
            for box_r in range(br, br + 3):
                for box_c in range(bc, bc + 3):
                    if (box_r, box_c) != (r, c):
                        self.neighbors[(r, c)].add((box_r, box_c))


def revise(csp, xi, xj):
    revised = False
    to_remove = set()
    for x in csp.domains[xi]:
        if csp.domains[xj] == {x}:
            to_remove.add(x)
            revised = True
    if revised:
        csp.domains[xi] -= to_remove
        csp.pruned_count += len(to_remove)
    return revised


def ac3(csp, queue=None):
    if queue is None:
        queue = deque(
            (xi, xj) for xi in csp.variables for xj in csp.neighbors[xi]
        )
    while queue:
        xi, xj = queue.popleft()
        if revise(csp, xi, xj):
            if len(csp.domains[xi]) == 0:
                return False
            for xk in csp.neighbors[xi]:
                if xk != xj:
                    queue.append((xk, xi))
    return True


def select_unassigned_variable(csp, assignment):
    unassigned = [v for v in csp.variables if v not in assignment]

    def mrv_degree_key(v):
        domain_size = len(csp.domains[v])
        degree = sum(
            1 for neighbor in csp.neighbors[v] if neighbor not in assignment
        )
        return (domain_size, -degree)

    return min(unassigned, key=mrv_degree_key)


def order_domain_values(csp, var):
    if len(csp.domains[var]) == 1:
        return list(csp.domains[var])
    return sorted(
        list(csp.domains[var]),
        key=lambda val: sum(
            1 for n in csp.neighbors[var] if val in csp.domains[n]
        ),
    )


def backtrack(csp, assignment):
    if len(assignment) == len(csp.variables):
        return assignment
    var = select_unassigned_variable(csp, assignment)

    for val in order_domain_values(csp, var):
        saved_domains = {v: set(csp.domains[v]) for v in csp.variables}
        assignment[var] = val
        csp.domains[var] = {val}

        inferences_queue = deque((n, var) for n in csp.neighbors[var])
        if ac3(csp, inferences_queue):
            result = backtrack(csp, assignment)
            if result is not None:
                return result

        csp.backtracks += 1
        del assignment[var]
        csp.domains = saved_domains
    return None


# =====================================================================
# 2. TKINTER INTERACTIVE DEMO GUI
# =====================================================================

PRESETS = {
    "Select Preset...": [[0] * 9 for _ in range(9)],
    "Easy (Few Constraints)": [
        [0, 0, 0, 2, 6, 0, 7, 0, 1],
        [6, 8, 0, 0, 7, 0, 0, 9, 0],
        [1, 9, 0, 0, 0, 4, 5, 0, 0],
        [8, 2, 0, 1, 0, 0, 0, 4, 0],
        [0, 0, 4, 6, 0, 2, 9, 0, 0],
        [0, 5, 0, 0, 0, 3, 0, 2, 8],
        [0, 0, 9, 3, 0, 0, 0, 7, 4],
        [0, 4, 0, 0, 5, 0, 0, 3, 6],
        [7, 0, 3, 0, 1, 8, 0, 0, 0],
    ],
    "Medium (Requires Search)": [
        [0, 2, 0, 6, 0, 8, 0, 0, 0],
        [5, 8, 0, 0, 0, 9, 7, 0, 0],
        [0, 0, 0, 0, 4, 0, 0, 0, 0],
        [3, 7, 0, 0, 0, 0, 5, 0, 0],
        [6, 0, 0, 0, 0, 0, 0, 0, 4],
        [0, 0, 8, 0, 0, 0, 0, 1, 3],
        [0, 0, 0, 0, 2, 0, 0, 0, 0],
        [0, 0, 9, 8, 0, 0, 0, 3, 6],
        [0, 0, 0, 3, 0, 6, 0, 9, 0],
    ],
    "Hard (Escargot / AI Challenge)": [
        [1, 0, 0, 0, 0, 7, 0, 9, 0],
        [0, 3, 0, 0, 2, 0, 0, 0, 8],
        [0, 0, 9, 6, 0, 0, 5, 0, 0],
        [0, 0, 5, 3, 0, 0, 9, 0, 0],
        [0, 1, 0, 0, 8, 0, 0, 0, 2],
        [6, 0, 0, 0, 0, 4, 0, 0, 0],
        [3, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 4, 0, 0, 0, 0, 0, 0, 7],
        [0, 0, 7, 0, 0, 0, 3, 0, 0],
    ],
}


class SudokuGUI:

    COLORS = {
        "background": "#f3f6fc",
        "panel": "#e5eaf5",
        "board": "#6475c7",
        "cell": "#ffffff",
        "cell_alt": "#eef1ff",
        "given": "#dce8ff",
        "given_text": "#23458a",
        "solved": "#dcfce7",
        "solved_text": "#166534",
        "accent": "#4f46a5",
        "text": "#24304a",
        "muted": "#5c6680",
        "green": "#16834a",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("AI Microproject: CSP Sudoku Solver")
        self.root.geometry("540x660")
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLORS["background"])

        self.cells = {}
        self.original_entries = set()

        self._create_header()
        self._create_grid()
        self._create_controls()
        self._create_metrics_bar()

    def _create_header(self):
        title = tk.Label(
            self.root,
            text="AI Sudoku Solver (CSP Engine)",
            font=("Arial", 16, "bold"),
            bg=self.COLORS["background"],
            fg=self.COLORS["accent"],
        )
        title.pack(pady=(12, 2))
        subtitle = tk.Label(
            self.root,
            text="AC-3 Arc Consistency • MRV • Degree • LCV",
            font=("Arial", 9),
            bg=self.COLORS["background"],
            fg=self.COLORS["muted"],
        )
        subtitle.pack(pady=(0, 10))

    def _create_grid(self):
        board_frame = tk.Frame(self.root, bg=self.COLORS["board"], bd=3)
        board_frame.pack()

        vcmd = (self.root.register(self._validate_input), "%P")

        for r in range(9):
            for c in range(9):
                # Calculate margins to visually separate 3x3 boxes
                top = 2 if r % 3 == 0 and r != 0 else 1
                left = 2 if c % 3 == 0 and c != 0 else 1

                cell_color = (
                    self.COLORS["cell_alt"]
                    if (r // 3 + c // 3) % 2
                    else self.COLORS["cell"]
                )
                cell_frame = tk.Frame(board_frame, bg=cell_color)
                cell_frame.grid(
                    row=r,
                    column=c,
                    padx=(left, 1),
                    pady=(top, 1),
                    sticky="nsew",
                )

                entry = tk.Entry(
                    cell_frame,
                    width=2,
                    font=("Helvetica", 18, "bold"),
                    justify="center",
                    bd=0,
                    bg=cell_color,
                    fg="#312e81",
                    insertbackground="#7c3aed",
                    highlightthickness=1,
                    highlightbackground=cell_color,
                    highlightcolor=self.COLORS["accent"],
                    validate="key",
                    validatecommand=vcmd,
                )
                entry.pack(ipadx=4, ipady=4)
                self.cells[(r, c)] = entry

    def _validate_input(self, text):
        return text == "" or (len(text) == 1 and text in "123456789")

    def _create_controls(self):
        ctrl_frame = tk.Frame(self.root, bg=self.COLORS["background"])
        ctrl_frame.pack(fill="x", padx=35, pady=12)

        # Preset selector
        self.preset_var = tk.StringVar(value="Select Preset...")
        preset_dropdown = ttk.Combobox(
            ctrl_frame,
            textvariable=self.preset_var,
            values=list(PRESETS.keys()),
            state="readonly",
            width=20,
            font=("Arial", 10),
        )
        preset_dropdown.bind("<<ComboboxSelected>>", self._load_preset)
        preset_dropdown.grid(row=0, column=0, padx=4, pady=4)

        # Buttons
        solve_btn = tk.Button(
            ctrl_frame,
            text="Solve with CSP",
            bg=self.COLORS["green"],
            fg="black",
            font=("Arial", 10, "bold"),
            padx=10,
            activebackground="#116b3c",
            activeforeground="white",
            relief="flat",
            command=self.solve,
        )
        solve_btn.grid(row=0, column=1, padx=4, pady=4)

        clear_btn = tk.Button(
            ctrl_frame,
            text="Clear",
            font=("Arial", 10),
            padx=8,
            bg="#52627d",
            fg="black",
            activebackground="#3f4d66",
            activeforeground="white",
            relief="flat",
            command=self.clear_grid,
        )
        clear_btn.grid(row=0, column=2, padx=4, pady=4)

    def _create_metrics_bar(self):
        metrics_frame = tk.LabelFrame(
            self.root,
            text=" AI Search Metrics  ",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=6,
            bg=self.COLORS["panel"],
            fg=self.COLORS["accent"],
            bd=0,
        )
        metrics_frame.pack(fill="x", padx=35, pady=4)

        self.time_label = tk.Label(
            metrics_frame,
            text="Time: --",
            font=("Arial", 9, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        )
        self.time_label.grid(row=0, column=0, sticky="w", padx=10)

        self.backtrack_label = tk.Label(
            metrics_frame,
            text="Backtracks: --",
            font=("Arial", 9, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        )
        self.backtrack_label.grid(row=0, column=1, sticky="w", padx=10)

        self.prune_label = tk.Label(
            metrics_frame,
            text="Values Pruned: --",
            font=("Arial", 9, "bold"),
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
        )
        self.prune_label.grid(row=0, column=2, sticky="w", padx=10)

    def _load_preset(self, event=None):
        name = self.preset_var.get()
        if name not in PRESETS or name == "Select Preset...":
            return
        grid = PRESETS[name]
        self.clear_grid()
        for r in range(9):
            for c in range(9):
                val = grid[r][c]
                if val != 0:
                    self.cells[(r, c)].insert(0, str(val))
                    self.cells[(r, c)].config(
                        fg=self.COLORS["given_text"],
                        bg=self.COLORS["given"],
                        highlightbackground=self.COLORS["given"],
                    )
                    self.original_entries.add((r, c))

    def clear_grid(self):
        for r in range(9):
            for c in range(9):
                self.cells[(r, c)].delete(0, tk.END)
                cell_color = (
                    self.COLORS["cell_alt"]
                    if (r // 3 + c // 3) % 2
                    else self.COLORS["cell"]
                )
                self.cells[(r, c)].config(
                    fg="#312e81",
                    bg=cell_color,
                    highlightbackground=cell_color,
                )
        self.original_entries.clear()
        self.time_label.config(text="Time: --")
        self.backtrack_label.config(text="Backtracks: --")
        self.prune_label.config(text="Values Pruned: --")

    def solve(self):
        # Read current grid state
        board = [[0] * 9 for _ in range(9)]
        self.original_entries.clear()

        for r in range(9):
            for c in range(9):
                val = self.cells[(r, c)].get().strip()
                if val.isdigit() and 1 <= int(val) <= 9:
                    board[r][c] = int(val)
                    self.original_entries.add((r, c))
                    self.cells[(r, c)].config(
                        fg=self.COLORS["given_text"],
                        bg=self.COLORS["given"],
                        highlightbackground=self.COLORS["given"],
                    )

        # Solve
        csp = SudokuCSP(board)
        t_start = time.perf_counter()

        if not ac3(csp):
            messagebox.showerror(
                "Inconsistent State",
                "Puzzle violates basic Sudoku rules! Check for duplicates.",
            )
            return

        assignment = {
            v: next(iter(csp.domains[v]))
            for v in csp.variables
            if len(csp.domains[v]) == 1
        }
        solution = backtrack(csp, assignment)
        t_elapsed = (time.perf_counter() - t_start) * 1000

        if solution:
            # Update GUI with solution values (colored blue for filled values)
            for (r, c), val in solution.items():
                if (r, c) not in self.original_entries:
                    self.cells[(r, c)].delete(0, tk.END)
                    self.cells[(r, c)].insert(0, str(val))
                    self.cells[(r, c)].config(
                        fg=self.COLORS["solved_text"],
                        bg=self.COLORS["solved"],
                        highlightbackground=self.COLORS["solved"],
                    )

            # Update Metrics Panel
            self.time_label.config(text=f"Time: {t_elapsed:.2f} ms")
            self.backtrack_label.config(
                text=f"Backtracks: {csp.backtracks}", fg="#a32645"
            )
            self.prune_label.config(
                text=f"Values Pruned: {csp.pruned_count}", fg="#18723d"
            )
        else:
            messagebox.showinfo("Unsolvable", "No valid solution exists.")


if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()
