from flask import Flask, render_template, request, jsonify
import json
import os
import re

app = Flask(__name__, 
            static_folder='app/static',
            template_folder='app/templates')

# Sample parsing tables for examples
SAMPLE_TABLES = {
    "example1": {
        "grammar": ["E → E+T", "E → T", "T → T*F", "T → F", "F → (E)", "F → id"],
        "terminals": ["id", "+", "*", "(", ")", "$"],
        "non_terminals": ["E", "T", "F"],
        "start_symbol": "E",
        "action_table": {
            "0": {"id": "s5", "(": "s4"},
            "1": {"+": "s6", "$": "acc"},
            "2": {"+": "r2", "*": "s7", ")": "r2", "$": "r2"},
            "3": {"+": "r4", "*": "r4", ")": "r4", "$": "r4"},
            "4": {"id": "s5", "(": "s4"},
            "5": {"+": "r6", "*": "r6", ")": "r6", "$": "r6"},
            "6": {"id": "s5", "(": "s4"},
            "7": {"id": "s5", "(": "s4"},
            "8": {"+": "s6", ")": "s11"},
            "9": {"+": "r1", "*": "s7", ")": "r1", "$": "r1"},
            "10": {"+": "r3", "*": "r3", ")": "r3", "$": "r3"},
            "11": {"+": "r5", "*": "r5", ")": "r5", "$": "r5"}
        },
        "goto_table": {
            "0": {"E": "1", "T": "2", "F": "3"},
            "4": {"E": "8", "T": "2", "F": "3"},
            "6": {"T": "9", "F": "3"},
            "7": {"F": "10"}
        },
        "rules": [
            {"lhs": "E", "rhs": "E+T", "length": 3},
            {"lhs": "E", "rhs": "T", "length": 1},
            {"lhs": "T", "rhs": "T*F", "length": 3},
            {"lhs": "T", "rhs": "F", "length": 1},
            {"lhs": "F", "rhs": "(E)", "length": 3},
            {"lhs": "F", "rhs": "id", "length": 1}
        ]
    },
    "example2": {
        "grammar": ["S → S+S", "S → S*S", "S → (S)", "S → a"],
        "terminals": ["a", "+", "*", "(", ")", "$"],
        "non_terminals": ["S"],
        "start_symbol": "S",
        "action_table": {
            "0": {"a": "s3", "(": "s2"},
            "1": {"+": "s4", "*": "s5", "$": "acc"},
            "2": {"a": "s3", "(": "s2"},
            "3": {"+": "r4", "*": "r4", ")": "r4", "$": "r4"},
            "4": {"a": "s3", "(": "s2"},
            "5": {"a": "s3", "(": "s2"},
            "6": {"+": "s4", "*": "s5", ")": "s9"},
            "7": {"+": "r1", "*": "s5", ")": "r1", "$": "r1"},
            "8": {"+": "r2", "*": "r2", ")": "r2", "$": "r2"},
            "9": {"+": "r3", "*": "r3", ")": "r3", "$": "r3"}
        },
        "goto_table": {
            "0": {"S": "1"},
            "2": {"S": "6"},
            "4": {"S": "7"},
            "5": {"S": "8"}
        },
        "rules": [
            {"lhs": "S", "rhs": "S+S", "length": 3},
            {"lhs": "S", "rhs": "S*S", "length": 3},
            {"lhs": "S", "rhs": "(S)", "length": 3},
            {"lhs": "S", "rhs": "a", "length": 1}
        ]
    }
}

def parse_grammar_rules(grammar):
    """Parse grammar rules from strings to dictionaries"""
    rules = []
    for rule in grammar:
        parts = rule.split('→')
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        
        # Count the number of symbols in RHS
        # We need to identify special tokens like 'id' and treat them as a single symbol
        symbols = []
        # Look for special tokens (id) or standard symbols (+, *, (, ), a)
        i = 0
        while i < len(rhs):
            if i < len(rhs) - 1 and rhs[i:i+2] == 'id':
                symbols.append('id')
                i += 2
            elif rhs[i] in ['+', '*', '(', ')', 'a']:
                symbols.append(rhs[i])
                i += 1
            elif not rhs[i].isspace():
                # This is a non-terminal or another symbol
                if i < len(rhs) - 1 and rhs[i+1].isalpha():
                    # Multi-character non-terminal
                    j = i + 1
                    while j < len(rhs) and rhs[j].isalnum():
                        j += 1
                    symbols.append(rhs[i:j])
                    i = j
                else:
                    symbols.append(rhs[i])
                    i += 1
            else:
                # Skip spaces
                i += 1
        
        length = len(symbols)
        rules.append({"lhs": lhs, "rhs": rhs, "length": length})
    return rules

def tokenize_input(input_string):
    """Tokenize input string to handle multi-character tokens like 'id'"""
    tokens = []
    i = 0
    while i < len(input_string):
        if i < len(input_string) - 1 and input_string[i:i+2] == 'id':
            tokens.append('id')
            i += 2
        else:
            tokens.append(input_string[i])
            i += 1
    return tokens

def slr_parse(input_string, action_table, goto_table, rules):
    """
    Implements the SLR parsing algorithm
    
    Args:
        input_string: The input string to parse
        action_table: The action table for the SLR parser
        goto_table: The goto table for the SLR parser
        rules: The grammar rules
        
    Returns:
        A dictionary containing parsing results and steps
    """
    # Tokenize the input string
    tokens = tokenize_input(input_string)
    
    # Add $ to the end of the tokens if not already present
    if tokens[-1] != '$':
        tokens.append('$')
    
    # Initialize the stack with state 0
    stack = ['0']
    input_buffer = tokens
    steps = []
    
    while True:
        current_state = stack[-1]
        current_symbol = input_buffer[0] if input_buffer else '$'
        
        # Get the action for the current state and symbol
        action = action_table.get(current_state, {}).get(current_symbol, "")
        
        # Record this step
        steps.append({
            'stack': stack.copy(),
            'input': ' '.join(input_buffer),  # Display tokens with spaces for clarity
            'action': action
        })
        
        # If no action is found, there's an error
        if not action:
            return {
                'success': False,
                'steps': steps,
                'error': f"No action found for state {current_state} and symbol {current_symbol}"
            }
        
        # Check the action type (shift, reduce, accept, or error)
        if action.startswith('s'):  # Shift
            shift_state = action[1:]
            stack.append(current_symbol)
            stack.append(shift_state)
            input_buffer.pop(0)
        
        elif action.startswith('r'):  # Reduce
            # Get the rule to reduce by
            production_idx = int(action[1:]) - 1  # Adjust for 0-indexing
            if production_idx < 0 or production_idx >= len(rules):
                return {
                    'success': False,
                    'steps': steps,
                    'error': f"Invalid production index: {production_idx + 1}"
                }
            
            rule = rules[production_idx]
            lhs = rule['lhs']
            rhs = rule['rhs']
            length = rule['length']
            
            steps[-1]['reduce'] = f"Reducing by rule {production_idx + 1}: {lhs} → {rhs}"
            
            # Pop 2*length items from the stack (symbol and state for each symbol in RHS)
            for _ in range(2 * length):
                stack.pop()
            
            # Get the current state after popping
            current_state = stack[-1]
            
            # Get the goto state for the current state and LHS non-terminal
            goto_state = goto_table.get(current_state, {}).get(lhs, "")
            if not goto_state:
                return {
                    'success': False,
                    'steps': steps,
                    'error': f"No goto found for state {current_state} and non-terminal {lhs}"
                }
            
            # Push the LHS non-terminal and new state onto the stack
            stack.append(lhs)
            stack.append(goto_state)
        
        elif action == 'acc':  # Accept
            return {
                'success': True,
                'steps': steps,
                'message': "Input accepted"
            }
        
        else:  # Error
            return {
                'success': False,
                'steps': steps,
                'error': f"Invalid action: {action}"
            }

@app.route('/')
def index():
    return render_template('index.html', examples=list(SAMPLE_TABLES.keys()))

@app.route('/parse', methods=['POST'])
def parse():
    data = request.json
    
    if data.get('example'):
        # Use a predefined example
        table_data = SAMPLE_TABLES.get(data['example'])
        if not table_data:
            return jsonify({'error': 'Example not found'})
        
        action_table = table_data['action_table']
        goto_table = table_data['goto_table']
        rules = table_data.get('rules')
        
        # If rules aren't pre-parsed, parse them from the grammar
        if not rules:
            rules = parse_grammar_rules(table_data['grammar'])
    else:
        # Use custom table data
        try:
            action_table = json.loads(data.get('action_table', '{}'))
            goto_table = json.loads(data.get('goto_table', '{}'))
            grammar = json.loads(data.get('grammar', '[]'))
            rules = parse_grammar_rules(grammar)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format'})
    
    input_string = data.get('input', '')
    if not input_string:
        return jsonify({'error': 'Input string cannot be empty'})
    
    result = slr_parse(input_string, action_table, goto_table, rules)
    return jsonify(result)

@app.route('/get_example/<example_id>')
def get_example(example_id):
    if example_id in SAMPLE_TABLES:
        return jsonify(SAMPLE_TABLES[example_id])
    return jsonify({'error': 'Example not found'})

if __name__ == '__main__':
    app.run(debug=True) 