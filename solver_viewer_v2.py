import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re
import pysolver_v4

class PokerSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Solver")
        self.json_data = None
        
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
            'All-In Threshold:', 'Max Iterations:', 'Target Exploitability:'
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
            pysolver_v4.main(input_file, output_file)
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
                self.file_label.config(text=os.path.basename(filename))
                self.setup_solution_display()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
    
    def load_json_from_path(self, filename):
        try:
            with open(filename, 'r') as file:
                self.json_data = json.load(file)
            self.file_label.config(text=os.path.basename(filename))
            self.setup_solution_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
    
    def setup_solution_display(self):
        # Clear previous display
        for widget in self.display_frame.winfo_children():
            widget.destroy()
            
        if not self.json_data:
            return
            
        self.current_node = 0
        self.node_history = [0]
        
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
        
        # Range display frame
        self.range_frame = ttk.LabelFrame(self.display_frame, text="Range Strategy & EVs")
        self.range_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.update_solution_display()
    
    def update_solution_display(self):
        if not self.json_data:
            return
            
        # Clear previous widgets
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        for widget in self.range_frame.winfo_children():
            widget.destroy()
            
        current_node_data = self.json_data[self.current_node]
        
        # Update action sequence
        action_seq = " > ".join(current_node_data["atn-sq"])
        self.action_label.config(text=f"Action Sequence: {action_seq}")
        
        # Show/hide back button
        if self.current_node == 0:
            self.back_button.grid_remove()
        else:
            self.back_button.grid()
            
        # Create action buttons if available actions exist
        if current_node_data["avl-acs"] is not None:
            for i, action in enumerate(current_node_data["avl-acs"]):
                btn = ttk.Button(self.actions_frame, text=action,
                               command=lambda a=action: self.navigate(a))
                btn.grid(row=0, column=i, padx=5)
        
        # Display range grid
        hands = current_node_data["rg-strat"].keys()
        if hands:
            # Headers
            ttk.Label(self.range_frame, text="Hand").grid(row=0, column=0, padx=5, pady=2)
            ttk.Label(self.range_frame, text="EV").grid(row=0, column=1, padx=5, pady=2)
            
            if current_node_data["avl-acs"]:
                for i, action in enumerate(current_node_data["avl-acs"]):
                    ttk.Label(self.range_frame, text=action).grid(row=0, column=i+2, padx=5, pady=2)
            
            for i, hand in enumerate(hands, 1):
                ttk.Label(self.range_frame, text=hand).grid(row=i, column=0, padx=5, pady=2)
                ev = current_node_data["rg-EVs"][hand]
                ttk.Label(self.range_frame, text=f"{ev:.2f}").grid(row=i, column=1, padx=5, pady=2)
                
                strat = current_node_data["rg-strat"][hand]
                for j, freq in enumerate(strat):
                    if freq > 0:
                        ttk.Label(self.range_frame, text=f"{freq:.2f}").grid(row=i, column=j+2, padx=5, pady=2)
    
    def navigate(self, action):
        current_node_data = self.json_data[self.current_node]
        next_seq = current_node_data["atn-sq"] + [action]
        
        for node in self.json_data:
            if node["atn-sq"] == next_seq:
                self.current_node = node["id"]
                self.node_history.append(self.current_node)
                self.update_solution_display()
                break
    
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
