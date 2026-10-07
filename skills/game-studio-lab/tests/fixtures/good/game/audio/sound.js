window.Sound = {
  ctx: null,
  init() { if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)(); },
  play(name) { if (this.ctx) this.ctx.resume(); return name; },
  playMusic(name) { return name; },
};
