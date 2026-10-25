let audioCtx: AudioContext | null = null;

export function getAudioContext(): AudioContext {
  if (!audioCtx && typeof window !== "undefined") {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audioCtx = new AudioCtx();
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx!;
}

export function playTone(freq: number, type: OscillatorType, duration: number, delay = 0, soundEnabled = true) {
  if (!soundEnabled || typeof window === "undefined") return;
  try {
    const ctx = getAudioContext();
    setTimeout(() => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    }, delay * 1000);
  } catch {
    // Ignore audio errors on autoplay-restricted devices
  }
}

export function playMessageChime(soundEnabled = true) {
  playTone(523.25, "sine", 0.25, 0, soundEnabled);    // C5
  playTone(659.25, "sine", 0.35, 0.08, soundEnabled); // E5
  playTone(783.99, "sine", 0.45, 0.16, soundEnabled); // G5
}

export function playLoveNudgeChime(soundEnabled = true) {
  playTone(440, "triangle", 0.3, 0, soundEnabled);      // A4
  playTone(554.37, "triangle", 0.3, 0.1, soundEnabled); // C#5
  playTone(659.25, "triangle", 0.3, 0.2, soundEnabled); // E5
  playTone(880, "triangle", 0.6, 0.3, soundEnabled);    // A5
}

export function burstHearts(count = 24) {
  if (typeof document === "undefined") return;
  const icons = ["💖", "💕", "❤️", "🥰", "🌸", "✨", "💋", "💌", "🌷", "💗", "💘", "🌹"];

  for (let i = 0; i < count; i++) {
    const delayMs = Math.random() * 750;
    setTimeout(() => {
      const h = document.createElement("div");
      h.className = "floating-heart";
      h.textContent = icons[Math.floor(Math.random() * icons.length)];

      const startX = Math.random() * 84 + 8;
      h.style.left = `${startX}vw`;

      const duration = (Math.random() * 1.2 + 2.6).toFixed(2);
      const sway = (Math.random() * 80 - 40).toFixed(0);
      const rot = (Math.random() * 50 - 25).toFixed(0);
      const size = (Math.random() * 1.1 + 1.4).toFixed(2);

      h.style.setProperty("--anim-dur", `${duration}s`);
      h.style.setProperty("--sway-x", `${sway}px`);
      h.style.setProperty("--rot", `${rot}deg`);
      h.style.fontSize = `${size}rem`;

      document.body.appendChild(h);
      setTimeout(() => h.remove(), parseFloat(duration) * 1000 + 100);
    }, delayMs);
  }
}
