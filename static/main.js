(function () {
    var btn = document.getElementById('fullscreenToggle');
    if (!btn) {
        return;
    }

    var supportsFullscreen = !!(document.documentElement.requestFullscreen);
    if (!supportsFullscreen) {
        return;
    }

    btn.hidden = false;

    function isFullscreen() {
        return !!document.fullscreenElement;
    }

    function updateButtonState() {
        var active = isFullscreen();
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.setAttribute('aria-label', active ? 'Exit fullscreen' : 'Enter fullscreen');
    }

    btn.addEventListener('click', function () {
        if (isFullscreen()) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen().catch(function () {
                // User gesture requirement not met, or denied by browser — no-op.
            });
        }
    });

    document.addEventListener('fullscreenchange', updateButtonState);

    updateButtonState();
})();
