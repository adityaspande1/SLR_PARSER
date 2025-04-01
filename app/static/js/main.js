$(document).ready(function() {
    // Load example from dropdown
    $('#exampleSelect').change(function() {
        const selectedExample = $(this).val();
        
        if (selectedExample) {
            // Show loading state
            $('#customInputs').addClass('opacity-50');
            
            // Fetch example data
            $.getJSON(`/get_example/${selectedExample}`, function(data) {
                // Fill the form with example data
                $('#grammar').val(JSON.stringify(data.grammar, null, 2));
                $('#actionTable').val(JSON.stringify(data.action_table, null, 2));
                $('#gotoTable').val(JSON.stringify(data.goto_table, null, 2));
                
                // Provide a default input string example based on the grammar
                if (data.grammar.some(rule => rule.includes("id"))) {
                    $('#inputString').val("id+id*id");
                } else if (data.grammar.some(rule => rule.includes("a"))) {
                    $('#inputString').val("a+a*a");
                }
                
                // Remove loading state
                $('#customInputs').removeClass('opacity-50');
            }).fail(function() {
                showError("Failed to load example");
                $('#customInputs').removeClass('opacity-50');
            });
        } else {
            // Clear the form for custom input
            $('#grammar').val('');
            $('#actionTable').val('');
            $('#gotoTable').val('');
            $('#inputString').val('');
        }
    });
    
    // Parse button click handler
    $('#parseBtn').click(function() {
        // Hide previous results
        hideMessages();
        
        // Show loading state
        $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Parsing...');
        
        // Prepare the data
        const selectedExample = $('#exampleSelect').val();
        const inputString = $('#inputString').val();
        
        let requestData = {
            input: inputString
        };
        
        if (selectedExample) {
            requestData.example = selectedExample;
        } else {
            try {
                // Parse custom input
                requestData.grammar = JSON.parse($('#grammar').val() || '[]');
                requestData.action_table = JSON.parse($('#actionTable').val() || '{}');
                requestData.goto_table = JSON.parse($('#gotoTable').val() || '{}');
            } catch (e) {
                showError("Invalid JSON format in one of the inputs");
                resetParseButton();
                return;
            }
        }
        
        // Send the request
        $.ajax({
            url: '/parse',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(requestData),
            success: function(response) {
                resetParseButton();
                
                if (response.error) {
                    showError(response.error);
                    return;
                }
                
                if (response.success) {
                    showSuccess(response.message || "Input string accepted");
                    displayParsingSteps(response.steps);
                } else {
                    showError(response.error || "Parsing failed");
                    displayParsingSteps(response.steps);
                }
            },
            error: function() {
                resetParseButton();
                showError("Server error. Please try again.");
            }
        });
    });
    
    // Helper functions
    function resetParseButton() {
        $('#parseBtn').prop('disabled', false).text('Parse');
    }
    
    function hideMessages() {
        $('#errorMessage, #successMessage').addClass('d-none').text('');
        $('#resultSection').addClass('d-none');
        $('#resultTable').empty();
    }
    
    function showError(message) {
        $('#errorMessage').removeClass('d-none').text(message);
    }
    
    function showSuccess(message) {
        $('#successMessage').removeClass('d-none').text(message);
    }
    
    function displayParsingSteps(steps) {
        if (!steps || steps.length === 0) {
            return;
        }
        
        $('#resultSection').removeClass('d-none');
        const resultTable = $('#resultTable');
        resultTable.empty();
        
        steps.forEach(function(step, index) {
            const row = $('<tr>');
            
            // Step number
            row.append($('<td>').text(index + 1));
            
            // Stack
            const stackCell = $('<td>');
            const stackText = step.stack.join(' ');
            stackCell.text(stackText);
            row.append(stackCell);
            
            // Input buffer
            row.append($('<td>').text(step.input));
            
            // Action
            const actionCell = $('<td>');
            let actionText = step.action;
            
            if (step.reduce) {
                actionText += " - " + step.reduce;
            }
            
            actionCell.text(actionText);
            row.append(actionCell);
            
            resultTable.append(row);
        });
        
        // Highlight the last row if there was an error
        if (!$('#errorMessage').hasClass('d-none')) {
            resultTable.find('tr:last').addClass('highlight');
        }
    }
}); 