(function () {
  // State: ordered array of player objects {id, name}
  let playing = [];

  // HTML escape helper to prevent XSS
  function esc(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Collect all players from the available list as initial source of truth
  const availList = document.getElementById('availablePlayers');
  const selList = document.getElementById('selectedPlayers');
  const hiddenInput = document.getElementById('selectedPlayerIdsInput');
  const startBtn = document.getElementById('startGameBtn');
  const startCount = document.getElementById('startCount');
  const playingCount = document.getElementById('playingCount');
  const playingEmpty = document.getElementById('playingEmpty');
  const availEmpty = document.getElementById('availableEmpty');

  // Initial player data from rendered <li> elements
  const allPlayers = Array.from(availList.querySelectorAll('li')).map(li => ({
    id: li.dataset.playerId,
    name: li.dataset.playerName,
    color: li.querySelector('.sp-avatar').style.background,
    initial: li.querySelector('.sp-avatar').textContent.trim(),
  }));

  function render() {
    const playingIds = new Set(playing.map(p => p.id));

    // Render playing list
    selList.innerHTML = '';
    playing.forEach((p, i) => {
      const li = document.createElement('li');
      li.className = 'sp-item sp-item--playing';
      li.innerHTML = `
        <span class="sp-turn">${i + 1}</span>
        <span class="avatar sp-avatar" style="background:${p.color}">${esc(p.initial)}</span>
        <span class="sp-name">${esc(p.name)}</span>
        <button class="sp-reorder" data-id="${p.id}" data-dir="-1" ${i === 0 ? 'disabled' : ''} aria-label="Move up">↑</button>
        <button class="sp-reorder" data-id="${p.id}" data-dir="1" ${i === playing.length - 1 ? 'disabled' : ''} aria-label="Move down">↓</button>
        <button class="sp-remove" data-id="${p.id}" aria-label="Remove">×</button>
      `;
      selList.appendChild(li);
    });

    // Render available list
    availList.innerHTML = '';
    allPlayers.filter(p => !playingIds.has(p.id)).forEach(p => {
      const li = document.createElement('li');
      li.className = 'sp-item sp-item--avail';
      li.dataset.playerId = p.id;
      li.dataset.playerName = p.name;
      li.innerHTML = `
        <span class="avatar sp-avatar" style="background:${p.color}">${esc(p.initial)}</span>
        <span class="sp-name">${esc(p.name)}</span>
        <span class="sp-add-icon">+</span>
      `;
      availList.appendChild(li);
    });

    // Update counts and empty states
    const n = playing.length;
    playingCount.textContent = n;
    startCount.textContent = n;
    playingEmpty.style.display = n === 0 ? '' : 'none';
    availEmpty.style.display = playingIds.size === allPlayers.length ? '' : 'none';

    if (n === 0) {
      startBtn.disabled = true;
      startBtn.classList.add('disabled');
    } else {
      startBtn.disabled = false;
      startBtn.classList.remove('disabled');
    }

    hiddenInput.value = playing.map(p => p.id).join(',');
  }

  function addPlayer(id) {
    const p = allPlayers.find(x => x.id === id);
    if (p && !playing.find(x => x.id === id)) {
      playing.push(p);
      render();
    }
  }

  function removePlayer(id) {
    playing = playing.filter(p => p.id !== id);
    render();
  }

  function movePlayer(id, dir) {
    const i = playing.findIndex(p => p.id === id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= playing.length) return;
    const tmp = playing[i]; playing[i] = playing[j]; playing[j] = tmp;
    render();
  }

  // Event delegation on available list
  availList.addEventListener('click', e => {
    const li = e.target.closest('li[data-player-id]');
    if (li) addPlayer(li.dataset.playerId);
  });

  // Event delegation on playing list
  selList.addEventListener('click', e => {
    const removeBtn = e.target.closest('.sp-remove');
    if (removeBtn) { removePlayer(removeBtn.dataset.id); return; }
    const reorderBtn = e.target.closest('.sp-reorder');
    if (reorderBtn) { movePlayer(reorderBtn.dataset.id, parseInt(reorderBtn.dataset.dir)); }
  });

  // Guard form submission
  document.getElementById('selectPlayersForm').addEventListener('submit', e => {
    if (playing.length === 0) {
      e.preventDefault();
      alert('Please select at least one player.');
    }
  });

  render();
})();
