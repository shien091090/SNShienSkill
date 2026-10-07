(function () {
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = Art.canvas.width;
  canvas.height = Art.canvas.height;
  const state = { x: 240, y: 560, hit: false, score: 0, time: 30, coins: [{ x: 100, y: 0 }], guide: 0 };
  let last = 0;
  let started = false;

  canvas.addEventListener('mousedown', (e) => {
    Sound.init();
    if (state.guide < 2) { state.guide++; return; }
    started = true;
    state.x = e.clientX;
  });

  function update(dt) {
    if (!started) return;
    state.time = Math.max(0, state.time - dt);
    for (const c of state.coins) {
      c.y += 200 * dt;
      if (Math.abs(c.y - state.y) < 30 && Math.abs(c.x - state.x) < 30) {
        state.score++;
        c.y = 0;
        Sound.play('coin');
      }
      if (c.y > Art.canvas.height) c.y = 0;
    }
  }

  function draw() {
    Art.drawBackground(ctx);
    if (state.guide < 2) { Art.drawGuidePage(ctx, { page: state.guide }); return; }
    state.coins.forEach((c) => Art.drawCoin(ctx, c));
    Art.drawPlayer(ctx, state);
    Art.drawHud(ctx, state);
  }

  function loop(t) {
    const dt = Math.min(0.05, (t - last) / 1000 || 0);
    last = t;
    update(dt);
    draw();
    requestAnimationFrame(loop);
  }
  Sound.playMusic('main');
  requestAnimationFrame(loop);
})();
