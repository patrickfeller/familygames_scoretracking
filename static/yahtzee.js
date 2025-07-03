document.addEventListener('DOMContentLoaded', function() {
    const scoreInputs = document.querySelectorAll('.score-input');
    const table = document.querySelector('.table-bordered');

    scoreInputs.forEach(input => {
        input.addEventListener('input', function() {
            const playerId = this.dataset.player;
            calculateTotals(playerId);
        });

        input.addEventListener('focus', function() {
            const row = this.dataset.row;
            const col = this.dataset.col;

            // Highlight row
            if (row !== undefined) {
                const rowElements = table.querySelectorAll(`tr[data-row="${row}"]`);
                rowElements.forEach(el => el.classList.add('highlighted-row'));
            }

            // Highlight column
            if (col !== undefined) {
                const colElements = table.querySelectorAll(`[data-col="${col}"]`);
                colElements.forEach(el => el.classList.add('highlighted-col'));
            }

            // Highlight cell
            this.parentNode.classList.add('highlighted-cell');
        });

        input.addEventListener('blur', function() {
            // Remove all highlighting
            table.querySelectorAll('.highlighted-row').forEach(el => el.classList.remove('highlighted-row'));
            table.querySelectorAll('.highlighted-col').forEach(el => el.classList.remove('highlighted-col'));
            this.parentNode.classList.remove('highlighted-cell');
        });
    });

    function calculateTotals(playerId) {
        let upperScore = 0;
        document.querySelectorAll(`input[data-player='${playerId}'][data-category='upper']`).forEach(input => {
            upperScore += parseInt(input.value) || 0;
        });

        let lowerScore = 0;
        document.querySelectorAll(`input[data-player='${playerId}'][data-category='lower']`).forEach(input => {
            lowerScore += parseInt(input.value) || 0;
        });

        const subtotalCell = document.getElementById(`subtotal-${playerId}`);
        subtotalCell.textContent = upperScore;

        const bonusCell = document.getElementById(`bonus-${playerId}`);
        let bonusValueForDisplay = 0;
        let bonusForTotal = 0;

        if (upperScore >= 63) {
            bonusValueForDisplay = 35;
            bonusForTotal = 35;
            bonusCell.classList.remove('text-red'); // Remove red if bonus is reached
        } else {
            bonusValueForDisplay = 63 - upperScore;
            bonusForTotal = 0;
            bonusCell.classList.add('text-red'); // Add red if bonus is not reached
        }
        bonusCell.textContent = bonusValueForDisplay;

        const totalCell = document.getElementById(`total-${playerId}`);
        totalCell.innerHTML = `<strong>${upperScore + bonusForTotal + lowerScore}</strong>`;
    }
});