window.Art = {
  canvas: { width: 480, height: 640 },
  drawBackground(ctx) {
    ctx.save();
    ctx.fillStyle = '#123';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.restore();
  },
  drawPlayer(ctx, state) {
    ctx.save();
    ctx.fillStyle = state.hit ? '#f44' : '#4cf';
    ctx.fillRect(state.x - 20, state.y - 20, 40, 40);
    ctx.restore();
  },
  drawCoin(ctx, state) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(state.x, state.y, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  },
  drawHud(ctx, state) {
    ctx.save();
    ctx.fillText('分數 ' + state.score + ' 時間 ' + Math.ceil(state.time), 10, 20);
    ctx.restore();
  },
  drawGuidePage(ctx, state) {
    ctx.save();
    ctx.fillText('說明 ' + (state.page + 1), 10, 20);
    ctx.restore();
  },
};
