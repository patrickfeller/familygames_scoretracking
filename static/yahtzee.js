function ytzSetTab(playerId) {
  // Deactivate all tabs and hide all panels
  document.querySelectorAll('.ytz-tab').forEach(t => t.classList.remove('ytz-tab--active'));
  document.querySelectorAll('.ytz-panel').forEach(p => p.classList.add('ytz-panel--hidden'));

  // Activate selected
  document.querySelector(`.ytz-tab[data-player-id="${playerId}"]`).classList.add('ytz-tab--active');
  document.getElementById(`panel-${playerId}`).classList.remove('ytz-panel--hidden');
}

function ytzRecalc(playerId) {
  let upper = 0, lower = 0;
  document.querySelectorAll(`.score-input[data-player="${playerId}"][data-section="upper"]`).forEach(inp => {
    upper += parseInt(inp.value) || 0;
  });
  document.querySelectorAll(`.score-input[data-player="${playerId}"][data-section="lower"]`).forEach(inp => {
    lower += parseInt(inp.value) || 0;
  });

  const bonus = upper >= 63 ? 35 : 0;
  document.getElementById(`upper-${playerId}`).textContent = upper;
  document.getElementById(`bonus-${playerId}`).textContent = bonus;
  document.getElementById(`total-${playerId}`).textContent = upper + bonus + lower;
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.score-input').forEach(inp => {
    inp.addEventListener('input', () => ytzRecalc(inp.dataset.player));
  });
});
