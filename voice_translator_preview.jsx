import React, { useState, useEffect, useRef } from 'react';

// Цветовая схема приложения
const COLORS = {
  bgPrimary: '#1a1a2e',
  bgSecondary: '#16213e',
  bgTertiary: '#0f3460',
  textPrimary: '#e8e8e8',
  textSecondary: '#a0a0a0',
  textMuted: '#606060',
  accentPrimary: '#00d4ff',
  accentSuccess: '#00ff88',
  accentWarning: '#ffaa00',
  accentError: '#ff4444',
  buttonBg: '#2d2d44',
  border: '#3d3d54',
};

// Компонент Toggle для выбора движка
const EngineToggle = ({ value, onChange }) => {
  const options = ['Vosk (Быстро)', 'Whisper (Точно)'];
  
  return (
    <div className="relative flex bg-opacity-50 rounded-full p-1" style={{ backgroundColor: COLORS.bgTertiary }}>
      <div
        className="absolute h-8 rounded-full transition-all duration-300"
        style={{
          width: '50%',
          backgroundColor: COLORS.accentPrimary,
          left: value === 0 ? '2px' : '50%',
          top: '2px',
          bottom: '2px',
        }}
      />
      {options.map((option, idx) => (
        <button
          key={idx}
          onClick={() => onChange(idx)}
          className="relative z-10 px-4 py-1.5 text-sm font-medium transition-colors"
          style={{
            color: value === idx ? COLORS.bgPrimary : COLORS.textSecondary,
            width: '50%',
          }}
        >
          {option}
        </button>
      ))}
    </div>
  );
};

// Компонент кнопки записи
const RecordButton = ({ isRecording, onClick }) => {
  const [pulse, setPulse] = useState(0);
  
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setPulse(p => (p + 0.1) % 1);
      }, 50);
      return () => clearInterval(interval);
    }
    setPulse(0);
  }, [isRecording]);

  return (
    <button
      onClick={onClick}
      className="relative w-20 h-20 rounded-full transition-transform hover:scale-105 active:scale-95"
      style={{
        backgroundColor: COLORS.bgTertiary,
        border: `3px solid ${isRecording ? COLORS.accentError : COLORS.border}`,
        boxShadow: isRecording ? `0 0 ${20 + pulse * 10}px ${COLORS.accentError}40` : 'none',
      }}
    >
      <div
        className="absolute inset-3 rounded-full transition-all duration-200"
        style={{
          backgroundColor: COLORS.accentError,
          borderRadius: isRecording ? '4px' : '50%',
          transform: isRecording ? 'scale(0.6)' : 'scale(1)',
        }}
      />
    </button>
  );
};

// Компонент индикатора уровня
const LevelMeter = ({ level }) => {
  const segments = 30;
  
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: segments }).map((_, i) => {
        const segmentPos = i / segments;
        const isActive = segmentPos < level;
        let color = COLORS.bgTertiary;
        
        if (isActive) {
          if (segmentPos < 0.6) color = COLORS.accentSuccess;
          else if (segmentPos < 0.85) color = COLORS.accentWarning;
          else color = COLORS.accentError;
        }
        
        return (
          <div
            key={i}
            className="h-3 rounded-sm transition-colors"
            style={{
              width: `${100 / segments}%`,
              backgroundColor: color,
            }}
          />
        );
      })}
    </div>
  );
};

// Компонент слайдера
const Slider = ({ label, value, onChange, min, max }) => (
  <div className="flex-1">
    <div className="text-xs mb-1" style={{ color: COLORS.textSecondary }}>{label}</div>
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 h-2 rounded-full appearance-none cursor-pointer"
        style={{ backgroundColor: COLORS.bgTertiary }}
      />
      <span className="text-sm w-12 text-right" style={{ color: COLORS.accentPrimary }}>{value}</span>
    </div>
  </div>
);

// Запись транскрипта
const TranscriptEntry = ({ entry }) => (
  <div className="mb-4">
    <div className="flex items-start gap-2">
      <span className="text-xs" style={{ color: COLORS.textMuted }}>[{entry.time}]</span>
      <span style={{ color: COLORS.textPrimary }}>{entry.original}</span>
    </div>
    {entry.translated && (
      <div className="ml-12 mt-1" style={{ color: COLORS.accentPrimary }}>
        → {entry.translated}
      </div>
    )}
  </div>
);

// Главное приложение
export default function VoiceTranslatorPreview() {
  const [engine, setEngine] = useState(1);
  const [isRecording, setIsRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [sensitivity, setSensitivity] = useState(1000);
  const [vad, setVad] = useState(500);
  const [transcript, setTranscript] = useState([
    { time: '10:32:15', original: 'Привет, как дела сегодня?', translated: 'Hello, how are you today?' },
    { time: '10:32:22', original: 'Я хочу заказать кофе', translated: 'I want to order coffee' },
    { time: '10:32:30', original: 'Где находится ближайшая станция метро?', translated: 'Where is the nearest metro station?' },
  ]);
  const [partialText, setPartialText] = useState('');

  // Симуляция уровня звука и распознавания
  useEffect(() => {
    if (isRecording) {
      const levelInterval = setInterval(() => {
        setLevel(Math.random() * 0.7 + 0.1);
      }, 100);

      const textInterval = setInterval(() => {
        const phrases = [
          'Это тестовое сообщение...',
          'Распознавание речи работает...',
          'Говорю по-русски...',
        ];
        setPartialText(phrases[Math.floor(Math.random() * phrases.length)]);
      }, 2000);

      return () => {
        clearInterval(levelInterval);
        clearInterval(textInterval);
      };
    }
    setLevel(0);
    setPartialText('');
  }, [isRecording]);

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bgPrimary }}>
      <div className="max-w-4xl mx-auto">
        {/* Заголовок */}
        <h1 className="text-2xl font-bold mb-6" style={{ color: COLORS.textPrimary }}>
          🎤 Голосовой Переводчик
        </h1>

        {/* Панель управления */}
        <div className="rounded-xl p-4 mb-4" style={{ backgroundColor: COLORS.bgSecondary }}>
          {/* Верхняя строка */}
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="text-xs mb-2" style={{ color: COLORS.textSecondary }}>
                Движок распознавания:
              </div>
              <EngineToggle value={engine} onChange={setEngine} />
            </div>
            
            <div>
              <div className="text-xs mb-2" style={{ color: COLORS.textSecondary }}>
                Микрофон:
              </div>
              <select
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: COLORS.bgTertiary,
                  color: COLORS.textPrimary,
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                <option>MacBook Pro Microphone</option>
                <option>External USB Microphone</option>
              </select>
            </div>
          </div>

          {/* Слайдеры */}
          <div className="flex gap-8">
            <Slider
              label="Чувствительность микрофона:"
              value={sensitivity}
              onChange={setSensitivity}
              min={100}
              max={2000}
            />
            <Slider
              label="Порог голоса (VAD):"
              value={vad}
              onChange={setVad}
              min={200}
              max={1000}
            />
          </div>
        </div>

        {/* Центральная панель */}
        <div className="flex items-center gap-6 mb-4">
          <RecordButton
            isRecording={isRecording}
            onClick={() => setIsRecording(!isRecording)}
          />
          
          <div className="flex-1">
            <div className="text-sm mb-2" style={{ color: isRecording ? COLORS.accentError : COLORS.textSecondary }}>
              {isRecording ? '🔴 Запись...' : 'Нажмите кнопку для начала записи'}
            </div>
            <LevelMeter level={level} />
          </div>

          <div className="flex gap-2">
            {['TXT', 'JSON', 'SRT'].map(format => (
              <button
                key={format}
                className="px-3 py-1.5 rounded text-sm transition-colors hover:opacity-80"
                style={{
                  backgroundColor: COLORS.buttonBg,
                  color: COLORS.textPrimary,
                }}
              >
                {format}
              </button>
            ))}
          </div>
        </div>

        {/* Область транскрипции */}
        <div className="rounded-xl overflow-hidden" style={{ backgroundColor: COLORS.bgSecondary }}>
          <div className="flex justify-between items-center px-4 py-3" style={{ borderBottom: `1px solid ${COLORS.border}` }}>
            <span className="font-medium" style={{ color: COLORS.textPrimary }}>
              📝 Транскрипция и перевод
            </span>
            <button
              className="text-sm px-3 py-1 rounded transition-colors hover:opacity-80"
              style={{ backgroundColor: COLORS.buttonBg, color: COLORS.textSecondary }}
            >
              Очистить
            </button>
          </div>
          
          <div className="p-4 h-64 overflow-y-auto" style={{ backgroundColor: COLORS.bgTertiary }}>
            {transcript.map((entry, i) => (
              <TranscriptEntry key={i} entry={entry} />
            ))}
            
            {partialText && (
              <div className="italic" style={{ color: COLORS.textSecondary }}>
                ⏳ {partialText}
              </div>
            )}
          </div>
        </div>

        {/* Статус бар */}
        <div className="flex justify-between mt-4 text-xs" style={{ color: COLORS.textMuted }}>
          <div className="flex gap-4">
            <span style={{ color: COLORS.accentSuccess }}>
              ● Движок: {engine === 0 ? 'Vosk' : 'Whisper'}
            </span>
            <span>Модель: {engine === 0 ? 'Russian 0.42' : 'small'}</span>
          </div>
          <div className="flex gap-4">
            <span>Кэш: 67%</span>
            <span>CPU: 12%</span>
          </div>
        </div>

        {/* Инструкция */}
        <div className="mt-6 p-4 rounded-lg text-sm" style={{ backgroundColor: COLORS.bgSecondary, color: COLORS.textSecondary }}>
          <strong style={{ color: COLORS.textPrimary }}>Горячие клавиши:</strong>
          <span className="ml-4">Cmd+R — Запись</span>
          <span className="ml-4">Cmd+S — Экспорт</span>
          <span className="ml-4">Esc — Стоп</span>
        </div>
      </div>
    </div>
  );
}
