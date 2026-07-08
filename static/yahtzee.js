const seq = (a, b) => Array.from({length: b - a + 1}, (_, i) => a + i);

const VALID_VALUES = {
  ones:              [0, 1, 2, 3, 4, 5],
  twos:              [0, 2, 4, 6, 8, 10],
  threes:            [0, 3, 6, 9, 12, 15],
  fours:             [0, 4, 8, 12, 16, 20],
  fives:             [0, 5, 10, 15, 20, 25],
  sixes:             [0, 6, 12, 18, 24, 30],
  one_pair:          [0, 2, 4, 6, 8, 10, 12],
  two_pair:          [0, ...seq(6, 22)],
  three_of_a_kind:   [0, 3, 6, 9, 12, 15, 18],
  four_of_a_kind:    [0, 4, 8, 12, 16, 20, 24],
  full_house:        [0, 25, 30],
  small_straight:    [0, 30, 35],
  large_straight:    [0, 40, 45],
  chance:            [0, ...seq(5, 30)],
  yahtzee:           [0, 50, 55],
};

function snapToValid(category, value) {
  const values = VALID_VALUES[category];
  if (!values) return value;
  if (values.includes(value)) return value;
  return values.reduce((best, v) => {
    const d1 = Math.abs(best - value), d2 = Math.abs(v - value);
    return d2 < d1 || (d2 === d1 && v > best) ? v : best;
  }, values[0]);
}

function ytzStep(playerId, category, direction) {
  const input = document.getElementById(`${playerId}_${category}`);
  if (!input) return;
  if (input.closest('.ytz-row--skipped')) return;
  const values = VALID_VALUES[category];
  if (!values) return;

  const current = parseInt(input.value) || 0;
  let idx = values.indexOf(current);
  if (idx === -1) {
    idx = values.reduce((best, v, i) =>
      Math.abs(v - current) < Math.abs(values[best] - current) ? i : best, 0);
  }
  const newIdx = Math.max(0, Math.min(idx + direction, values.length - 1));
  input.value = values[newIdx];
  ytzRecalc(playerId);
}

function ytzToggleSkip(playerId, category) {
  const input = document.getElementById(`${playerId}_${category}`);
  if (!input) return;
  const row = input.closest('.ytz-row');
  if (!row) return;

  const skipped = row.classList.toggle('ytz-row--skipped');
  if (skipped) {
    input.dataset.prevValue = input.value;
    input.value = 0;
  } else {
    input.value = input.dataset.prevValue || '';
    delete input.dataset.prevValue;
  }
  ytzRecalc(playerId);
}

function ytzSetTab(playerId) {
  document.querySelectorAll('.ytz-tab').forEach(t => t.classList.remove('ytz-tab--active'));
  document.querySelectorAll('.ytz-panel').forEach(p => p.classList.add('ytz-panel--hidden'));

  document.querySelector(`.ytz-tab[data-player-id="${playerId}"]`).classList.add('ytz-tab--active');
  document.getElementById(`panel-${playerId}`).classList.remove('ytz-panel--hidden');
}

function ytzRecalc(playerId) {
  let upper = 0, lower = 0;
  document.querySelectorAll(`.score-input[data-player="${playerId}"]`).forEach(inp => {
    const row = inp.closest('.ytz-row');
    if (row) row.classList.toggle('ytz-row--filled', inp.value !== '');
  });
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

  // Stepper buttons
  document.querySelectorAll('.ytz-btn-dec, .ytz-btn-inc').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.classList.contains('ytz-btn-inc') ? 1 : -1;
      ytzStep(btn.dataset.player, btn.dataset.category, dir);
    });
  });

  // Skip buttons
  document.querySelectorAll('.ytz-btn-skip').forEach(btn => {
    btn.addEventListener('click', () => {
      ytzToggleSkip(btn.dataset.player, btn.dataset.category);
    });
  });

  // Snap manual input to nearest valid value on blur
  document.querySelectorAll('.score-input').forEach(inp => {
    inp.addEventListener('blur', () => {
      if (inp.value === '') return;
      const cat = inp.dataset.category;
      const val = parseInt(inp.value) || 0;
      const snapped = snapToValid(cat, val);
      if (snapped !== val) inp.value = snapped;
      ytzRecalc(inp.dataset.player);
    });
  });
});
