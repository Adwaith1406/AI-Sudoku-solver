import copy
from collections import deque
import random
import time
import tkinter as tk
from tkinter import messagebox, ttk

# =====================================================================
# 1. AI ENGINE: CONSTRAINT SATISFACTION PROBLEM (CSP)
# =====================================================================


class SudokuCSP:
    """Represents the Sudoku board as a formal Constraint Satisfaction Problem.

    - Variables: 81 cells (row, col)
    - Domains: {1..9} or {pre-filled digit}
    - Constraints: AllDiff across rows, columns, and 3x3 subgrids
    """

    def __init__(self, board):
        self.variables = [(r, c) for r in range(9) for c in range(9)]
        self.neighbors = {v: set() for v in self.variables}
        self._build_constraints()

        # Initial Domains
        self.domains = {}
        for r in range(9):
            for c in range(9):
                val = board[r][c]
                self.domains[(r, c)] = {val} if val != 0 else set(range(1, 10))

        # Metrics for project viva & reporting
        self.backtracks = 0
        self.pruned_count = 0

    def _build_constraints(self):
        for r, c in self.variables:
            # Row and Column peers
            for i in range(9):
                if i != c:
                    self.neighbors[(r, c)].add((r, i))
                if i != r:
                    self.neighbors[(r, c)].add((i, c))

            # 3x3 Box peers
            br, bc = 3 * (r // 3), 3 * (c // 3)
            for box_r in range(br, br + 3):
                for box_c in range(bc, bc + 3):
                    if (box_r, box_c) != (r, c):
                        self.neighbors[(r, c)].add((box_r, box_c))


def revise(csp, xi, xj):
    """Enforces Arc Consistency on the directed arc (xi, xj)."""
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
    """AC-3 (Arc Consistency 3) Algorithm."""
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
    """MRV (Minimum Remaining Values) with Degree Heuristic tie-breaker."""
    unassigned = [v for v in csp.variables if v not in assignment]

    def mrv_degree_key(v):
        domain_size = len(csp.domains[v])
        degree = sum(
            1 for neighbor in csp.neighbors[v] if neighbor not in assignment
        )
        return (domain_size, -degree)

    return min(unassigned, key=mrv_degree_key)


def order_domain_values(csp, var):
    """LCV (Least Constraining Value) Heuristic."""
    if len(csp.domains[var]) == 1:
        return list(csp.domains[var])

    def count_conflicts(val):
        return sum(1 for n in csp.neighbors[var] if val in csp.domains[n])

    return sorted(list(csp.domains[var]), key=count_conflicts)


def backtrack(csp, assignment):
    """Recursive CSP Backtracking search with Forward Checking / AC-3 Inference."""
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
# 2. RANDOM PUZZLE GENERATOR
# =====================================================================


def is_valid_placement(board, row, col, num):
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False
    start_r, start_c = 3 * (row // 3), 3 * (col // 3)
    for r in range(start_r, start_r + 3):
        for c in range(start_c, start_c + 3):
            if board[r][c] == num:
                return False
    return True


def fill_board_randomly(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                nums = list(range(1, 10))
                random.shuffle(nums)
                for num in nums:
                    if is_valid_placement(board, r, c, num):
                        board[r][c] = num
                        if fill_board_randomly(board):
                            return True
                        board[r][c] = 0
                return False
    return True


def generate_sudoku(clues=32):
    board = [[0] * 9 for _ in range(9)]
    fill_board_randomly(board)

    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    removals = 81 - clues
    for i in range(removals):
        r, c = cells[i]
        board[r][c] = 0

    return board


# =====================================================================
# 3. INTERACTIVE LIGHT-THEMED GUI
# =====================================================================


class SudokuGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("AI Microproject: CSP Sudoku Solver")
        self.root.geometry("540x690")
        self.root.resizable(False, False)

        # Light Color Palette
        self.BG_APP = "#f8fafc"  # Soft slate off-white
        self.BG_GRID_BORDER = "#64748b"  # Outer & 3x3 block borders
        self.BG_CELL = "#ffffff"  # Cell background
        self.TEXT_GIVEN = "#0f172a"  # Deep slate for user/preset numbers
        self.TEXT_SOLVED = "#2563eb"  # Vibrant blue for AI-solved numbers
        self.ACCENT_PRIMARY = "#10b981"  # Emerald green for Solve
        self.ACCENT_SECONDARY = "#0284c7"  # Sky blue for Generate
        self.BTN_TEXT = "#ffffff"
        self.SUBTEXT = "#64748b"

        self.root.configure(bg=self.BG_APP)

        self.cells = {}
        self.original_entries = set()

        self._build_header()
        self._build_grid()
        self._build_controls()
        self._build_metrics_bar()

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg=self.BG_APP)
        header_frame.pack(pady=(16, 8))

        title = tk.Label(
            header_frame,
            text="AI Sudoku Solver & Generator",
            font=("Segoe UI", 16, "bold"),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
        )
        title.pack()

        subtitle = tk.Label(
            header_frame,
            text="Constraint Satisfaction Problem • AC-3 • MRV • LCV",
            font=("Segoe UI", 9),
            bg=self.BG_APP,
            fg=self.SUBTEXT,
        )
        subtitle.pack(pady=(2, 0))

    def _build_grid(self):
        # Outer container with border color
        board_container = tk.Frame(
            self.root, bg=self.BG_GRID_BORDER, bd=2, relief="solid"
        )
        board_container.pack(pady=4)

        vcmd = (self.root.register(self._validate_input), "%P")

        for r in range(9):
            for c in range(9):
                # 3x3 block visual separation
                top_pad = 2 if r % 3 == 0 and r != 0 else 1
                left_pad = 2 if c % 3 == 0 and c != 0 else 1

                cell_frame = tk.Frame(board_container, bg=self.BG_CELL)
                cell_frame.grid(
                    row=r,
                    column=c,
                    padx=(left_pad, 1),
                    pady=(top_pad, 1),
                    sticky="nsew",
                )

                entry = tk.Entry(
                    cell_frame,
                    width=2,
                    font=("Segoe UI", 17, "bold"),
                    justify="center",
                    bd=0,
                    bg=self.BG_CELL,
                    fg=self.TEXT_GIVEN,
                    insertbackground=self.TEXT_GIVEN,
                    highlightthickness=0,
                    validate="key",
                    validatecommand=vcmd,
                )
                entry.pack(ipadx=4, ipady=4)
                self.cells[(r, c)] = entry

    def _validate_input(self, text):
        return text == "" or (len(text) == 1 and text in "123456789")

    def _build_controls(self):
        ctrl_frame = tk.Frame(self.root, bg=self.BG_APP)
        ctrl_frame.pack(fill="x", padx=36, pady=12)

        # Style Combobox for light theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "TCombobox",
            fieldbackground="#ffffff",
            background="#e2e8f0",
            foreground=self.TEXT_GIVEN,
        )

        # Row 1: Generation Controls
        gen_label = tk.Label(
            ctrl_frame,
            text="Difficulty:",
            font=("Segoe UI", 9, "bold"),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
        )
        gen_label.grid(row=0, column=0, padx=(0, 4), pady=4, sticky="w")

        self.diff_var = tk.StringVar(value="Medium")
        diff_menu = ttk.Combobox(
            ctrl_frame,
            textvariable=self.diff_var,
            values=["Easy", "Medium", "Hard"],
            state="readonly",
            width=9,
        )
        diff_menu.grid(row=0, column=1, padx=4, pady=4)

        gen_btn = tk.Button(
            ctrl_frame,
            text="🎲 Generate",
            bg=self.ACCENT_SECONDARY,
            fg=self.BTN_TEXT,
            activebackground="#0369a1",
            activeforeground=self.BTN_TEXT,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.generate_new_board,
        )
        gen_btn.grid(row=0, column=2, padx=6, pady=4)

        clear_btn = tk.Button(
            ctrl_frame,
            text="Clear",
            bg="#e2e8f0",
            fg=self.TEXT_GIVEN,
            activebackground="#cbd5e1",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.clear_grid,
        )
        clear_btn.grid(row=0, column=3, padx=4, pady=4)

        # Row 2: Big Solve Button
        solve_btn = tk.Button(
            ctrl_frame,
            text="⚡ Solve Puzzle with CSP",
            bg=self.ACCENT_PRIMARY,
            fg=self.BTN_TEXT,
            activebackground="#059669",
            activeforeground=self.BTN_TEXT,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            pady=5,
            cursor="hand2",
            command=self.solve,
        )
        solve_btn.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 2))

    def _build_metrics_bar(self):
        metrics_frame = tk.LabelFrame(
            self.root,
            text=" Live AI Search Metrics ",
            font=("Segoe UI", 9, "bold"),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
            padx=12,
            pady=8,
            bd=1,
            relief="solid",
        )
        metrics_frame.pack(fill="x", padx=36, pady=4)

        self.time_label = tk.Label(
            metrics_frame,
            text="Solve Time: --",
            font=("Segoe UI", 9),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
        )
        self.time_label.grid(row=0, column=0, sticky="w", padx=(0, 16))

        self.backtrack_label = tk.Label(
            metrics_frame,
            text="Backtracks: --",
            font=("Segoe UI", 9),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
        )
        self.backtrack_label.grid(row=0, column=1, sticky="w", padx=16)

        self.prune_label = tk.Label(
            metrics_frame,
            text="Values Pruned: --",
            font=("Segoe UI", 9),
            bg=self.BG_APP,
            fg=self.TEXT_GIVEN,
        )
        self.prune_label.grid(row=0, column=2, sticky="w", padx=16)

    def clear_grid(self):
        for r in range(9):
            for c in range(9):
                self.cells[(r, c)].delete(0, tk.END)
                self.cells[(r, c)].config(fg=self.TEXT_GIVEN)
        self.original_entries.clear()
        self.time_label.config(text="Solve Time: --", fg=self.TEXT_GIVEN)
        self.backtrack_label.config(text="Backtracks: --", fg=self.TEXT_GIVEN)
        self.prune_label.config(text="Values Pruned: --", fg=self.TEXT_GIVEN)

    def generate_new_board(self):
        self.clear_grid()
        clue_counts = {"Easy": 38, "Medium": 30, "Hard": 24}
        clues = clue_counts.get(self.diff_var.get(), 30)

        new_puzzle = generate_sudoku(clues=clues)
        for r in range(9):
            for c in range(9):
                val = new_puzzle[r][c]
                if val != 0:
                    self.cells[(r, c)].insert(0, str(val))
                    self.cells[(r, c)].config(fg=self.TEXT_GIVEN)
                    self.original_entries.add((r, c))

    def solve(self):
        board = [[0] * 9 for _ in range(9)]
        self.original_entries.clear()

        # Read board input
        for r in range(9):
            for c in range(9):
                val = self.cells[(r, c)].get().strip()
                if val.isdigit() and 1 <= int(val) <= 9:
                    board[r][c] = int(val)
                    self.original_entries.add((r, c))
                    self.cells[(r, c)].config(fg=self.TEXT_GIVEN)

        csp = SudokuCSP(board)
        t_start = time.perf_counter()

        # Arc Consistency check
        if not ac3(csp):
            messagebox.showerror(
                "Rule Violation",
                "Puzzle violates basic Sudoku rules! Check for duplicates in a row, column, or 3x3 block.",
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
            # AI filled digits highlighted in vibrant blue
            for (r, c), val in solution.items():
                if (r, c) not in self.original_entries:
                    self.cells[(r, c)].delete(0, tk.END)
                    self.cells[(r, c)].insert(0, str(val))
                    self.cells[(r, c)].config(fg=self.TEXT_SOLVED)

            # Update Metrics Panel
            self.time_label.config(
                text=f"Solve Time: {t_elapsed:.2f} ms", fg="#0284c7"
            )
            self.backtrack_label.config(
                text=f"Backtracks: {csp.backtracks}", fg="#dc2626"
            )
            self.prune_label.config(
                text=f"Values Pruned: {csp.pruned_count}", fg="#059669"
            )
        else:
            messagebox.showinfo("Unsolvable", "No valid solution exists.")


# =====================================================================
# 4. ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()