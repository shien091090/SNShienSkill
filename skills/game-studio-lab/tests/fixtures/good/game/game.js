(function () {
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = Art.canvas.width;
  canvas.height = Art.canvas.height;
  const state = { x: 240, y: 560, hit: false, score: 0, time: 30, coins: [{ x: 100, y: 0 }] };
  // 新手教學: 階段 0 點一下移動, 階段 1 接到一枚金幣
  const tutorial = { stage: 0, done: 0, texts: ['點畫面移動', '接住金幣'] };
  let screen = 'title';
  let last = 0;

  canvas.addEventListener('mousedown', (e) => {
    Sound.init();
    if (screen === 'title') { screen = 'play'; return; }
    state.x = e.clientX;
    if (tutorial.stage === 0) tutorial.done = 0.01;
  });

  function update(dt) {
    if (screen !== 'play') return;
    if (tutorial.done > 0) {
      tutorial.done += dt * 2;
      if (tutorial.done >= 1) { tutorial.stage++; tutorial.done = 0; }
    }
    state.time = Math.max(0, state.time - dt);
    for (const c of state.coins) {
      c.y += 200 * dt;
      if (Math.abs(c.y - state.y) < 30 && Math.abs(c.x - state.x) < 30) {
        state.score++;
        c.y = 0;
        Sound.play('coin');
        if (tutorial.stage === 1 && !tutorial.done) tutorial.done = 0.01;
      }
      if (c.y > Art.canvas.height) c.y = 0;
    }
  }

  function draw(t) {
    Art.drawBackground(ctx);
    if (screen === 'title') { Art.drawTitle(ctx, { blink: Math.floor(t / 500) % 2 === 0 }); return; }
    state.coins.forEach((c) => Art.drawCoin(ctx, c));
    Art.drawPlayer(ctx, state);
    Art.drawHud(ctx, state);
    if (tutorial.stage < tutorial.texts.length) {
      Art.drawTutorial(ctx, { stage: tutorial.stage, text: tutorial.texts[tutorial.stage], keys: [], pressed: [],
        done: tutorial.done, x: 20, y: 80 });
    }
  }

  function loop(t) {
    const dt = Math.min(0.05, (t - last) / 1000 || 0);
    last = t;
    update(dt);
    draw(t);
    requestAnimationFrame(loop);
  }
  Sound.playMusic('main');
  requestAnimationFrame(loop);
})();
