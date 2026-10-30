/* Keep each lesson player alive between modal opens. No playback history is stored. */
(() => {
  'use strict';
  const players = new WeakMap();
  function pause(state) {
    if (state.ready) state.player.pause();
    else if (state.frame.contentWindow) {
      // Also covers an SDK load failure. Player.js uses the iframe's exact origin.
      state.frame.contentWindow.postMessage(JSON.stringify({context: 'player.js', version: '0.0.11', method: 'pause'}), state.origin);
    }
  }
  document.addEventListener('show.bs.modal', event => {
    const modal = event.target;
    if (!modal.matches('.course-video-modal')) return;
    let state = players.get(modal);
    if (state) { state.visible = true; return; }
    const frame = modal.querySelector('iframe');
    const source = frame?.dataset.src || event.relatedTarget?.getAttribute('data-preview-src');
    if (!frame || !source) return;
    const url = new URL(source, window.location.origin);
    url.searchParams.set('autoplay', 'false');
    state = {frame, origin: url.origin, visible: true, ready: false, player: null};
    players.set(modal, state);
    frame.src = url.toString();
    if (window.playerjs?.Player) {
      state.player = new window.playerjs.Player(frame);
      state.player.on('ready', () => {
        state.ready = true;
        if (!state.visible) pause(state);
      });
    }
  });
  // Pause immediately, including when Escape is used; do not reset src or replace the iframe.
  document.addEventListener('hide.bs.modal', event => {
    const state = players.get(event.target);
    if (!state) return;
    state.visible = false;
    pause(state);
  });
})();
