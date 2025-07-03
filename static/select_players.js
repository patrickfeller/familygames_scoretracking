const availablePlayersList = document.getElementById('availablePlayers');
const selectedPlayersList = document.getElementById('selectedPlayers');
const selectedPlayerIdsInput = document.getElementById('selectedPlayerIdsInput');

function updateSelectedPlayerIds() {
    const selectedIds = Array.from(selectedPlayersList.children).map(li => li.dataset.playerId);
    selectedPlayerIdsInput.value = selectedIds.join(',');
    console.log("Updated selectedPlayerIdsInput:", selectedPlayerIdsInput.value);
}

// Initial update in case there are pre-selected players (though not in this template yet)
updateSelectedPlayerIds();

// Drag and Drop functionality
[availablePlayersList, selectedPlayersList].forEach(list => {
    list.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', e.target.dataset.playerId); // Set the player ID as data
        e.target.classList.add('dragging');
        console.log('Drag started for player ID:', e.target.dataset.playerId);
    });

    list.addEventListener('dragend', (e) => {
        e.target.classList.remove('dragging');
        updateSelectedPlayerIds(); // Update IDs after drag ends
        console.log('Drag ended.');
    });

    list.addEventListener('dragover', (e) => {
        e.preventDefault(); // Allow drop
        e.dataTransfer.dropEffect = 'move'; // Visual feedback for move operation
        list.classList.add('over'); // Add visual feedback for dragover
        console.log('Drag over:', list.id);
    });

    list.addEventListener('dragleave', () => {
        list.classList.remove('over');
        // console.log('Drag left.');
    });

    list.addEventListener('drop', (e) => {
        e.preventDefault(); // Crucial for allowing the drop
        list.classList.remove('over');
        console.log('Drop event fired on:', list.id);

        const playerId = e.dataTransfer.getData('text/plain'); // Get the player ID
        const droppedElement = document.querySelector(`[data-player-id="${playerId}"]`); // Find the actual element

        if (droppedElement) {
            console.log('Dropped element found:', droppedElement.textContent);
            // Remove from the original list if it's being moved to a different list
            if (droppedElement.parentNode && droppedElement.parentNode !== list) {
                droppedElement.parentNode.removeChild(droppedElement);
                console.log('Removed from original parent.');
            }

            // Determine where to insert the dropped item in the current list
            const afterElement = getDragAfterElement(list, e.clientY);
            if (afterElement == null) {
                list.appendChild(droppedElement);
                console.log('Appended to list.');
            } else {
                list.insertBefore(droppedElement, afterElement);
                console.log('Inserted before:', afterElement.textContent);
            }

            droppedElement.classList.remove('dragging'); // Clean up dragging class
            updateSelectedPlayerIds(); // Update IDs after successful drop
        } else {
            console.log('Dropped element not found for player ID:', playerId);
        }
    });
});

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('li:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: -Infinity }).element;
}

// Handle form submission for player selection
document.getElementById('selectPlayersForm').addEventListener('submit', function(e) {
    updateSelectedPlayerIds(); // Ensure the hidden input is up-to-date
    const selectedIds = selectedPlayerIdsInput.value;
    if (!selectedIds) {
        e.preventDefault();
        alert('Please select at least one player.');
    }
});

// Handle form submission for adding new player (already handled by Flask)