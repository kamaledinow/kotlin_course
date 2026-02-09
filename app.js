const state = {
  watchId: null,
  watchProvider: null,
  startTime: null,
  elapsedSec: 0,
  distanceKm: 0,
  avgKmh: 0,
  currentKmh: 0,
  lastPos: null,
  timerId: null,
  voiceIntervalId: null,
  speedSamples: [],
};

const ui = {
  currentSpeed: document.getElementById('currentSpeed'),
  avgSpeed: document.getElementById('avgSpeed'),
  distance: document.getElementById('distance'),
  elapsed: document.getElementById('elapsed'),
  adviceText: document.getElementById('adviceText'),
  limitSpeed: document.getElementById('limitSpeed'),
  safeTarget: document.getElementById('safeTarget'),
  recoverySpeed: document.getElementById('recoverySpeed'),
  startBtn: document.getElementById('startBtn'),
  stopBtn: document.getElementById('stopBtn'),
  resetBtn: document.getElementById('resetBtn'),
};

function haversineKm(lat1, lon1, lat2, lon2) {
  const toRad = (v) => (v * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function formatTime(totalSec) {
  const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
  const s = String(totalSec % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function getAdvice() {
  const limit = Number(ui.limitSpeed.value);
  const safeTarget = Number(ui.safeTarget.value);
  const recovery = Number(ui.recoverySpeed.value);
  const tMin = state.elapsedSec / 60;
  const dist = state.distanceKm;

  if (state.elapsedSec < 60 || dist < 0.1) {
    return 'Собираю данные. Проедьте ещё немного для точного прогноза.';
  }

  if (state.avgKmh <= safeTarget) {
    if (state.currentKmh <= safeTarget) {
      return `Средняя ${state.avgKmh.toFixed(1)} км/ч — в безопасной зоне. Можно держать темп.`;
    }

    const numerator = safeTarget * tMin - dist * 60;
    const denominator = Math.max(state.currentKmh - safeTarget, 0.1);
    const minutesLeft = Math.max(numerator / denominator, 0);
    if (!Number.isFinite(minutesLeft) || minutesLeft > 120) {
      return `Средняя в норме (${state.avgKmh.toFixed(1)} км/ч). На текущей скорости запас большой.`;
    }

    return `Средняя в норме (${state.avgKmh.toFixed(1)} км/ч). На текущей скорости можно ехать ещё ~${minutesLeft.toFixed(1)} мин до цели ${safeTarget} км/ч.`;
  }

  const warnMinutes = ((dist * 60) - limit * tMin) / Math.max(limit - recovery, 0.1);
  const safeMinutes = ((dist * 60) - safeTarget * tMin) / Math.max(safeTarget - recovery, 0.1);
  const needMin = Math.max(safeMinutes, 0);

  if (state.avgKmh > limit) {
    return `Внимание: средняя ${state.avgKmh.toFixed(1)} км/ч выше лимита ${limit}. Снизьтесь до ${recovery} км/ч примерно на ${needMin.toFixed(1)} мин, чтобы вернуться к ${safeTarget} км/ч.`;
  }

  return `Средняя ${state.avgKmh.toFixed(1)} км/ч близко к лимиту ${limit}. Лучше ехать ${recovery} км/ч ещё около ${Math.max(warnMinutes, 0).toFixed(1)} мин.`;
}

function getSmoothedSpeed(nextKmh) {
  state.speedSamples.push(nextKmh);
  if (state.speedSamples.length > 5) {
    state.speedSamples.shift();
  }

  const sum = state.speedSamples.reduce((acc, item) => acc + item, 0);
  return sum / state.speedSamples.length;
}

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'ru-RU';
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
}

function render() {
  ui.currentSpeed.textContent = `${state.currentKmh.toFixed(1)} км/ч`;
  ui.avgSpeed.textContent = `${state.avgKmh.toFixed(1)} км/ч`;
  ui.distance.textContent = `${state.distanceKm.toFixed(2)} км`;
  ui.elapsed.textContent = formatTime(state.elapsedSec);
  ui.adviceText.textContent = getAdvice();
}

function onPosition(position) {
  const { latitude, longitude, speed, accuracy } = position.coords;
  const ts = position.timestamp;

  if (accuracy && accuracy > 50) {
    return;
  }

  if (state.lastPos) {
    const segmentKm = haversineKm(
      state.lastPos.coords.latitude,
      state.lastPos.coords.longitude,
      latitude,
      longitude,
    );
    state.distanceKm += segmentKm;

    const dtSec = (ts - state.lastPos.timestamp) / 1000;
    if (speed != null && speed >= 0) {
      state.currentKmh = getSmoothedSpeed(speed * 3.6);
    } else if (dtSec > 0) {
      const rawKmh = (segmentKm / dtSec) * 3600;
      if (rawKmh <= 220) {
        state.currentKmh = getSmoothedSpeed(rawKmh);
      }
    }
  }

  state.lastPos = position;
  const hours = state.elapsedSec / 3600;
  state.avgKmh = hours > 0 ? state.distanceKm / hours : 0;
  render();
}

function onError(err) {
  ui.adviceText.textContent = `Ошибка геолокации: ${err.message || 'нет доступа к геолокации'}`;
}

function getCapacitorGeolocationPlugin() {
  return window.Capacitor?.Plugins?.Geolocation || null;
}

async function startWebGeolocation() {
  if (!navigator.geolocation) {
    throw new Error('Геолокация не поддерживается в этом браузере.');
  }

  const watchId = navigator.geolocation.watchPosition(onPosition, onError, {
    enableHighAccuracy: true,
    maximumAge: 1000,
    timeout: 10000,
  });

  return { watchId, provider: 'web' };
}

async function startCapacitorGeolocation(plugin) {
  const permission = await plugin.requestPermissions();
  const granted = ['granted', 'prompt-with-rationale'];
  if (!granted.includes(permission.location)) {
    throw new Error('Нет разрешения на геолокацию в Android-приложении.');
  }

  const watchId = await plugin.watchPosition(
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 1000 },
    (pos, err) => {
      if (err) {
        onError(err);
        return;
      }
      if (!pos) return;
      onPosition({ coords: pos.coords, timestamp: pos.timestamp || Date.now() });
    },
  );

  return { watchId, provider: 'capacitor' };
}

function startCommonTimers() {
  state.timerId = setInterval(() => {
    state.elapsedSec = Math.floor((Date.now() - state.startTime) / 1000);
    const h = state.elapsedSec / 3600;
    state.avgKmh = h > 0 ? state.distanceKm / h : 0;
    render();
  }, 1000);

  state.voiceIntervalId = setInterval(() => {
    speak(getAdvice());
  }, 5 * 60 * 1000);
}

async function start() {
  try {
    const plugin = getCapacitorGeolocationPlugin();

    if (!state.startTime) {
      state.startTime = Date.now();
    } else {
      state.startTime = Date.now() - state.elapsedSec * 1000;
    }

    const tracking = plugin
      ? await startCapacitorGeolocation(plugin)
      : await startWebGeolocation();

    state.watchId = tracking.watchId;
    state.watchProvider = tracking.provider;
    startCommonTimers();
    speak('Мониторинг начат. Голосовые подсказки каждые 5 минут.');
    ui.startBtn.disabled = true;
    ui.stopBtn.disabled = false;
  } catch (error) {
    onError(error);
  }
}

async function stop() {
  try {
    if (state.watchId !== null) {
      if (state.watchProvider === 'capacitor') {
        const plugin = getCapacitorGeolocationPlugin();
        if (plugin) {
          await plugin.clearWatch({ id: state.watchId });
        }
      } else if (navigator.geolocation) {
        navigator.geolocation.clearWatch(state.watchId);
      }
    }
  } finally {
    clearInterval(state.timerId);
    clearInterval(state.voiceIntervalId);
    state.watchId = null;
    state.watchProvider = null;
    state.timerId = null;
    state.voiceIntervalId = null;
    ui.startBtn.disabled = false;
    ui.stopBtn.disabled = true;
  }
}

async function reset() {
  await stop();
  state.startTime = null;
  state.elapsedSec = 0;
  state.distanceKm = 0;
  state.avgKmh = 0;
  state.currentKmh = 0;
  state.lastPos = null;
  state.speedSamples = [];
  render();
}

ui.startBtn.addEventListener('click', () => {
  start();
});
ui.stopBtn.addEventListener('click', () => {
  stop();
});
ui.resetBtn.addEventListener('click', () => {
  reset();
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('service-worker.js').catch(() => {
    // no-op for local/dev limitations
  });
}

render();
