import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re
import pysolver_v10

class PokerSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Solver")
        self.json_data = None
        self.node_id_to_index = {}  # Mapping from node "id" to list index
        self.ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create frames for tabs
        self.run_frame = ttk.Frame(self.notebook)
        self.view_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.run_frame, text="Run Solver")
        self.notebook.add(self.view_frame, text="View Solution")
        
        self.setup_run_tab()
        self.setup_view_tab()
        
    def setup_run_tab(self):
        # Main frame for inputs
        input_frame = ttk.LabelFrame(self.run_frame, text="Solver Parameters", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Default values from solver_inputs.txt
        defaults = {
            'pot_size': '10',
            'stack_size': '50',
            'oop_range': 'AsAc:0.5, QsQc',
            'ip_range': 'KsKc',
            'board': '2c2h2s2d3h',
            'oop_bet_sizes': '100',
            'ip_bet_sizes': '100',
            'oop_raise_sizes': '50',
            'ip_raise_sizes': '50',
            'ai_threshold': '70',
            'max_iterations': '90',
            'target_exploitability': '0.7'
        }
        
        self.entries = {}
        labels = [
            'Pot Size:', 'Stack Size:', 'OOP Range:', 'IP Range:', 'Board:',
            'OOP Bet Sizes:', 'IP Bet Sizes:', 'OOP Raise Sizes:', 'IP Raise Sizes:',
            'All-In Threshold:', 'Max Iterations:', 'Target exploitability:'
        ]
        
        for i, label in enumerate(labels):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            entry = ttk.Entry(input_frame)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))
            entry.insert(0, defaults[list(defaults.keys())[i]])
            self.entries[list(defaults.keys())[i]] = entry
        
        # Input file selection
        file_frame = ttk.Frame(input_frame)
        file_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        
        self.file_path = tk.StringVar(value='solver_inputs.txt')
        ttk.Label(file_frame, text="Parameters File:").grid(row=0, column=0, padx=5)
        ttk.Entry(file_frame, textvariable=self.file_path, width=30).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5)
        
        # Solver output file selection
        output_file_frame = ttk.Frame(input_frame)
        output_file_frame.grid(row=len(labels)+1, column=0, columnspan=2, pady=10)
        
        self.output_file_path = tk.StringVar(value='solver_output.json')
        ttk.Label(output_file_frame, text="Solver Output File:").grid(row=0, column=0, padx=5)
        ttk.Entry(output_file_frame, textvariable=self.output_file_path, width=30).grid(row=0, column=1, padx=5)
        ttk.Button(output_file_frame, text="Browse", command=self.browse_output_file).grid(row=0, column=2, padx=5)
        
        # Save button
        ttk.Button(input_frame, text="Save Parameters", command=self.save_parameters).grid(
            row=len(labels)+2, column=0, columnspan=2, pady=10)
        
        # Run Solver button
        ttk.Button(input_frame, text="Run Solver", command=self.run_solver).grid(
            row=len(labels)+3, column=0, columnspan=2, pady=10)
        
        # Configure column weights
        input_frame.columnconfigure(1, weight=1)
        
    def browse_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
    
    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.output_file_path.set(filename)
    
    def validate_inputs(self):
        try:
            # Validate numeric inputs
            pot_size = float(self.entries['pot_size'].get())
            stack_size = float(self.entries['stack_size'].get())
            ai_threshold = float(self.entries['ai_threshold'].get())
            max_iterations = int(self.entries['max_iterations'].get())
            target_exploitability = float(self.entries['target_exploitability'].get())
            
            # Validate board (10 characters)
            board = self.entries['board'].get()
            if len(board) != 10:
                raise ValueError("Board must be exactly 10 characters")
            
            # Validate range strings
            oop_range = self.entries['oop_range'].get()
            ip_range = self.entries['ip_range'].get()
            if not oop_range or not ip_range:
                raise ValueError("Ranges cannot be empty")
            
            # Validate bet/raise sizes
            for key in ['oop_bet_sizes', 'ip_bet_sizes', 'oop_raise_sizes', 'ip_raise_sizes']:
                value = self.entries[key].get()
                if value:
                    items = [item.strip() for item in value.split(',')]
                    for item in items:
                        if item.lower() not in ['a', ''] and not item.replace('.', '').isdigit():
                            raise ValueError(f"Invalid {key}: must be 'a' or numbers separated by commas")
            
            return True
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return False
    
    def save_parameters(self):
        if not self.validate_inputs():
            return
            
        inputs = [
            self.entries['pot_size'].get(),
            self.entries['stack_size'].get(),
            self.entries['oop_range'].get(),
            self.entries['ip_range'].get(),
            self.entries['board'].get(),
            self.entries['oop_bet_sizes'].get(),
            self.entries['ip_bet_sizes'].get(),
            self.entries['oop_raise_sizes'].get(),
            self.entries['ip_raise_sizes'].get(),
            self.entries['ai_threshold'].get(),
            self.entries['max_iterations'].get(),
            self.entries['target_exploitability'].get()
        ]
        
        try:
            with open(self.file_path.get(), 'w') as f:
                f.write('\n'.join(inputs))
            messagebox.showinfo("Success", "Parameters saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save parameters: {str(e)}")
    
    def run_solver(self):
        # Save parameters first
        self.save_parameters()
        
        # Get input and output files
        input_file = self.file_path.get()
        output_file = self.output_file_path.get()
        
        # Run the solver
        try:
            pysolver_v10.main(input_file, output_file)
            messagebox.showinfo("Success", "Solver Finished")
            
            # Load the output file
            self.load_json_from_path(output_file)
            
            # Switch to View Solution tab
            self.notebook.select(self.view_frame)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run solver: {str(e)}")
    
    def setup_view_tab(self):
        # File selection frame
        file_frame = ttk.Frame(self.view_frame)
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(file_frame, text="Load JSON File", command=self.load_json).grid(
            row=0, column=0, padx=5, pady=5)
        
        self.file_label = ttk.Label(file_frame, text="No file loaded")
        self.file_label.grid(row=0, column=1, padx=5, pady=5)
        
        # Main display frame (will be populated after loading)
        self.display_frame = ttk.Frame(self.view_frame)
        self.display_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.view_frame.columnconfigure(0, weight=1)
        self.view_frame.rowconfigure(1, weight=1)
    
    def load_json(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as file:
                    self.json_data = json.load(file)
                # Build the node ID to index mapping
                self.node_id_to_index = {node["id"]: idx for idx, node in enumerate(self.json_data)}
                self.file_label.config(text=os.path.basename(filename))
                self.setup_solution_display()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
    
    def load_json_from_path(self, filename):
        try:
            with open(filename, 'r') as file:
                self.json_data = json.load(file)
            # Build the node ID to index mapping
            self.node_id_to_index = {node["id"]: idx for idx, node in enumerate(self.json_data)}
            self.file_label.config(text=os.path.basename(filename))
            self.setup_solution_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
    
    def find_root_node_id(self):
        """Find the node with an empty action sequence as the root node."""
        for node in self.json_data:
            if node["atn-sq"] == []:
                return node["id"]
        raise ValueError("No root node (empty action sequence) found in JSON data.")
    
    def setup_solution_display(self):
        # Clear previous display
        for widget in self.display_frame.winfo_children():
            widget.destroy()
            
        if not self.json_data:
            return
            
        # Find the root node dynamically
        try:
            root_node_id = self.find_root_node_id()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
            
        self.current_node = root_node_id  # Set to the root node's ID
        self.node_history = [self.current_node]  # Store node IDs
        
        # Navigation frame
        nav_frame = ttk.Frame(self.display_frame)
        nav_frame.grid(row=0, column=0, columnspan=2, pady=5)
        
        self.back_button = ttk.Button(nav_frame, text="Back", command=self.go_back)
        self.back_button.grid(row=0, column=0, padx=5)
        
        self.action_label = ttk.Label(nav_frame, text="")
        self.action_label.grid(row=0, column=1, padx=5)
        
        # Action buttons frame
        self.actions_frame = ttk.Frame(self.display_frame)
        self.actions_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Grids frame for hand display
        self.grids_frame = ttk.Frame(self.display_frame)
        self.grids_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.update_solution_display()
    
    def update_solution_display(self):
        if not self.json_data:
            return
            
        # Map the current node ID to its index in self.json_data
        if self.current_node not in self.node_id_to_index:
            messagebox.showerror("Error", f"Invalid node ID: {self.current_node}. Unable to display node.")
            return
            
        current_idx = self.node_id_to_index[self.current_node]
        current_node_data = self.json_data[current_idx]
        print(f"Displaying node {self.current_node} (index {current_idx}) with sequence: {current_node_data['atn-sq']}")
        
        # Update action sequence
        action_seq = " > ".join(current_node_data["atn-sq"])
        self.action_label.config(text=f"Action Sequence: {action_seq}")
        
        # Show/hide back button
        if len(self.node_history) <= 1:  # Root node if history has only one entry
            self.back_button.grid_remove()
        else:
            self.back_button.grid()
            
        # Clear previous widgets
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        for widget in self.grids_frame.winfo_children():
            widget.destroy()
            
        # Create action buttons if available actions exist
        if current_node_data["avl-acs"] is not None:
            for i, action in enumerate(current_node_data["avl-acs"]):
                btn = ttk.Button(self.actions_frame, text=action,
                               command=lambda a=action: self.navigate(a))
                btn.grid(row=0, column=i, padx=5)
        
        # Create left grid canvas
        self.left_grid_canvas = tk.Canvas(self.grids_frame, width=400, height=400)
        self.left_grid_canvas.grid(row=0, column=0)
        
        # Compute min and max EV for color scaling
        all_evs = []
        for hand in current_node_data.get("rg-EVs", {}):
            try:
                ev = current_node_data["rg-EVs"][hand]
                all_evs.append(float(ev))
            except (ValueError, TypeError, KeyError):
                continue
        min_ev = min(all_evs) if all_evs else 0
        max_ev = max(all_evs) if all_evs else 0
        
        # Create 13x13 grid for hand types
        cell_size = 30
        for i in range(13):
            for j in range(13):
                x1 = j * cell_size
                y1 = i * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                
                # Determine hand type
                if i == j:
                    hand_type = self.ranks[i] + self.ranks[j]  # e.g., "AA"
                elif i < j:
                    hand_type = self.ranks[i] + self.ranks[j] + 's'  # e.g., "AKs"
                else:
                    hand_type = self.ranks[j] + self.ranks[i] + 'o'  # e.g., "AKo"
                
                # Find specific hands in this category
                specific_hands = [
                    hand for hand in current_node_data.get("rg-strat", {}).keys()
                    if self.get_hand_type(hand) == hand_type
                ]
                if specific_hands:
                    evs = []
                    for hand in specific_hands:
                        try:
                            ev = current_node_data["rg-EVs"][hand]
                            evs.append(float(ev))
                        except (KeyError, ValueError, TypeError):
                            continue
                    avg_ev = sum(evs) / len(evs) if evs else None
                    color = self.get_color(avg_ev, min_ev, max_ev)
                else:
                    avg_ev = None
                    color = 'white'
                
                # Draw rectangle and text
                rect_id = self.left_grid_canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags=hand_type)
                text_id = self.left_grid_canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=hand_type, tags=hand_type)
                
                # Bind hover events
                self.left_grid_canvas.tag_bind(hand_type, '<Enter>', lambda event, ht=hand_type: self.show_detailed_grid(ht))
                self.left_grid_canvas.tag_bind(hand_type, '<Leave>', lambda event: self.hide_detailed_grid())
    
    def get_hand_type(self, hand):
        """Map a specific hand to its hand type category."""
        rank1, suit1, rank2, suit2 = hand[0], hand[1], hand[2], hand[3]
        if rank1 == rank2:
            return rank1 + rank2  # Pair, e.g., "KK"
        elif suit1 == suit2:
            return rank1 + rank2 + 's'  # Suited, e.g., "KQs"
        else:
            return rank1 + rank2 + 'o'  # Offsuit, e.g., "AKo"
    
    def get_color(self, ev, min_ev, max_ev):
        """Return a color based on EV value using a red-to-green gradient."""
        if ev is None:
            return 'white'
        norm = (ev - min_ev) / (max_ev - min_ev) if max_ev > min_ev else 0.5
        r = int(255 * (1 - norm))
        g = int(255 * norm)
        b = 0
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def show_detailed_grid(self, hand_type):
        """Display a detailed grid for specific hands when hovering over a hand type."""
        current_idx = self.node_id_to_index[self.current_node]
        current_node_data = self.json_data[current_idx]
        specific_hands = [
            hand for hand in current_node_data.get("rg-strat", {}).keys()
            if self.get_hand_type(hand) == hand_type
        ]
        if not specific_hands:
            return
        
        # Create detailed frame
        self.detailed_frame = ttk.Frame(self.grids_frame)
        self.detailed_frame.grid(row=0, column=1, padx=10)
        
        # Headers
        ttk.Label(self.detailed_frame, text="Hand").grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(self.detailed_frame, text="EV").grid(row=0, column=1, padx=5, pady=2)
        
        if current_node_data.get("avl-acs") is not None:
            actions = current_node_data["avl-acs"]
            for i, action in enumerate(actions):
                ttk.Label(self.detailed_frame, text=action).grid(row=0, column=i+2, padx=5, pady=2)
        
        # Populate data
        for i, hand in enumerate(specific_hands, 1):
            ttk.Label(self.detailed_frame, text=hand).grid(row=i, column=0, padx=5, pady=2)
            
            # Safely get EV
            ev = current_node_data.get("rg-EVs", {}).get(hand, "N/A")
            try:
                ev = float(ev)
                ev_text = f"{ev:.2f}"
            except (ValueError, TypeError):
                ev_text = "N/A"
            ttk.Label(self.detailed_frame, text=ev_text).grid(row=i, column=1, padx=5, pady=2)
            
            # Safely get strategy frequencies
            if current_node_data.get("avl-acs") is not None:
                strat = current_node_data.get("rg-strat", {}).get(hand, [])
                if strat and len(strat) == len(current_node_data["avl-acs"]):
                    for j, freq in enumerate(strat):
                        try:
                            freq = float(freq)
                            if freq > 0:
                                ttk.Label(self.detailed_frame, text=f"{freq:.2f}").grid(row=i, column=j+2, padx=5, pady=2)
                        except (ValueError, TypeError):
                            ttk.Label(self.detailed_frame, text="N/A").grid(row=i, column=j+2, padx=5, pady=2)
    
    def hide_detailed_grid(self):
        """Hide the detailed grid when the mouse leaves the cell."""
        if hasattr(self, 'detailed_frame'):
            self.detailed_frame.destroy()
    
    def navigate(self, action):
        current_idx = self.node_id_to_index[self.current_node]
        current_node_data = self.json_data[current_idx]
        current_seq = current_node_data["atn-sq"]
        print(f"Current sequence: {current_seq}, Selected action: {action}")
        
        # Search for the node that extends the current sequence with the selected action
        next_node_id = None
        for node in self.json_data:
            node_seq = node["atn-sq"]
            # Check if this node's sequence extends the current sequence by one action
            if (len(node_seq) == len(current_seq) + 1 and
                node_seq[:-1] == current_seq and
                node_seq[-1] == action):  # Exact match for the last action
                next_node_id = node["id"]
                print(f"Found matching node {next_node_id} with sequence {node_seq}")
                break
        
        if next_node_id is not None:
            self.current_node = next_node_id
            self.node_history.append(self.current_node)
            self.update_solution_display()
        else:
            # If no matching node is found, show an error and don't navigate
            expected_seq = current_seq + [action]
            messagebox.showerror("Error", f"No node found for action sequence: {expected_seq}")
    
    def go_back(self):
        if len(self.node_history) > 1:
            self.node_history.pop()
            self.current_node = self.node_history[-1]
            self.update_solution_display()

def main():
    root = tk.Tk()
    app = PokerSolverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
