import React, { useState } from 'react';
import axios from 'axios';
import { 
  ShieldCheck, 
  FileText, 
  Image as ImageIcon, 
  Video as VideoIcon, 
  Volume2 as AudioIcon, 
  UploadCloud, 
  RefreshCw, 
  AlertCircle,
  HelpCircle,
  Activity,
  Layers
} from 'lucide-react';

interface Decision {
  is_manipulated: boolean;
  credibility_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface Metric {
  ai_generation_probability: number;
  editing_artifact_score: number;
  semantic_consistency_score: number;
}

interface Explanation {
  code: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  location: string;
}

interface ScanResult {
  target_file: string;
  media_type: 'text' | 'image' | 'video' | 'audio';
  decision: Decision;
  metrics: Metric;
  explanations: Explanation[];
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState('');
  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem('tg_api_key') || '';
  });

  const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setApiKey(value);
    localStorage.setItem('tg_api_key', value);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const startScan = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    if (transcript) {
      formData.append('transcript', transcript);
    }

    try {
      const headers: Record<string, string> = {};
      if (apiKey.trim()) {
        headers['X-API-Key'] = apiKey.trim();
      }
      const response = await axios.post<ScanResult>(
        'http://localhost:8000/api/v1/scan/media', 
        formData,
        { headers }
      );
      setResult(response.data);
    } catch (err: any) {
      if (err.response && err.response.status === 401) {
        alert('인증 실패: 유효하지 않은 API Key이거나 키가 입력되지 않았습니다.');
      } else {
        alert('분석을 시작하지 못했습니다. 백엔드 FastAPI 서버가 기동 중인지 확인하십시오.');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setTranscript('');
    setResult(null);
  };

  const getMediaIcon = (type: string) => {
    switch (type) {
      case 'text': return <FileText size={24} className="text-blue-400" />;
      case 'image': return <ImageIcon size={24} className="text-emerald-400" />;
      case 'video': return <VideoIcon size={24} className="text-purple-400" />;
      case 'audio': return <AudioIcon size={24} className="text-amber-400" />;
      default: return <HelpCircle size={24} className="text-gray-400" />;
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'LOW': return '#10b981'; // Green
      case 'MEDIUM': return '#f59e0b'; // Yellow
      case 'HIGH': return '#f97316'; // Orange
      case 'CRITICAL': return '#ef4444'; // Red
      default: return '#9ca3af';
    }
  };

  return (
    <div style={{
      fontFamily: 'Inter, sans-serif',
      minHeight: '100vh',
      backgroundColor: '#0f172a',
      color: '#f8fafc',
      padding: '40px 20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '40px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginBottom: '8px' }}>
          <ShieldCheck size={40} style={{ color: '#38bdf8', filter: 'drop-shadow(0 0 10px rgba(56, 189, 248, 0.4))' }} />
          <h1 style={{ fontSize: '32px', fontWeight: 800, letterSpacing: '-0.025em', margin: 0, background: 'linear-gradient(to right, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            TruthGuard SDK
          </h1>
        </div>
        <p style={{ color: '#94a3b8', fontSize: '15px', margin: 0 }}>
          AI 가짜뉴스, 딥페이크 변조 미디어 및 오디오 분석 종합 대시보드
        </p>
        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 600 }}>API Key:</label>
          <input 
            type="password" 
            value={apiKey} 
            onChange={handleApiKeyChange}
            placeholder="인증용 API Key 입력 (X-API-Key)" 
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '13px',
              color: '#f8fafc',
              width: '240px',
              outline: 'none',
              textAlign: 'center'
            }}
          />
        </div>
      </header>

      <main style={{ width: '100%', maxWidth: '850px' }}>
        {/* Step 1: Upload Panel */}
        {!result && (
          <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '16px',
            border: '1px style #334155',
            padding: '32px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
            transition: 'all 0.2s ease-in-out'
          }}>
            <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UploadCloud size={22} className="text-sky-400" /> 분석 대상 미디어 등록
            </h2>

            <div 
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              style={{
                border: `2px dashed ${dragActive ? '#38bdf8' : '#475569'}`,
                backgroundColor: dragActive ? 'rgba(56, 189, 248, 0.05)' : '#0f172a',
                borderRadius: '12px',
                padding: '40px 20px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input 
                id="file-input"
                type="file" 
                onChange={handleFileChange} 
                style={{ display: 'none' }}
                accept=".txt,.md,.jpg,.jpeg,.png,.webp,.mp4,.avi,.mov,.mkv,.wav,.mp3,.m4a,.flac"
              />
              <UploadCloud size={48} style={{ color: '#64748b', marginBottom: '16px' }} />
              {file ? (
                <div>
                  <p style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc', margin: '0 0 4px 0' }}>{file.name}</p>
                  <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p style={{ fontSize: '15px', fontWeight: 600, color: '#cbd5e1', margin: '0 0 8px 0' }}>
                    파일을 드래그하여 드롭하거나 클릭하여 선택하세요
                  </p>
                  <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
                    TXT, MD, JPG, PNG, WEBP, MP4, WAV, MP3 등 지원
                  </p>
                </div>
              )}
            </div>

            {/* Audio Transcript Option */}
            {file && (file.type.startsWith('audio/') || file.name.endsWith('.wav') || file.name.endsWith('.mp3')) && (
              <div style={{ marginTop: '20px' }}>
                <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, color: '#94a3b8', marginBottom: '8px' }}>
                  오디오 대화 텍스트 (보이스피싱 분석용)
                </label>
                <textarea 
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="예: 긴급 상황이니 빠르게 계좌번호로 송금 이체해 주세요."
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    height: '80px',
                    borderRadius: '8px',
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    color: '#f8fafc',
                    padding: '12px',
                    fontSize: '14px',
                    resize: 'none',
                    outline: 'none'
                  }}
                />
              </div>
            )}

            {file && (
              <button
                onClick={startScan}
                disabled={loading}
                style={{
                  width: '100%',
                  marginTop: '24px',
                  backgroundColor: '#0284c7',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '14px',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)',
                  transition: 'all 0.2s'
                }}
              >
                {loading ? (
                  <>
                    <RefreshCw size={18} style={{ animation: 'spin 1s linear infinite' }} />
                    스캐닝 엔진 분석 중...
                  </>
                ) : (
                  '신뢰도 및 AI 변조 검증 시작'
                )}
              </button>
            )}
          </div>
        )}

        {/* Step 2: Result Report */}
        {result && (
          <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '16px',
            border: '1px solid #334155',
            padding: '32px',
            boxShadow: '0 15px 35px -5px rgba(0, 0, 0, 0.4)'
          }}>
            {/* Header info */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'between', borderBottom: '1px solid #334155', paddingBottom: '20px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                {getMediaIcon(result.media_type)}
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{result.target_file}</h3>
                  <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>분석 모듈: {result.media_type.toUpperCase()}</p>
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  fontSize: '13px',
                  fontWeight: 700,
                  backgroundColor: result.decision.is_manipulated ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  color: result.decision.is_manipulated ? '#ef4444' : '#10b981',
                  border: `1px solid ${result.decision.is_manipulated ? '#ef4444' : '#10b981'}`
                }}>
                  {result.decision.is_manipulated ? '위조 및 변조 의심' : '정상 콘텐츠'}
                </span>
              </div>
            </div>

            {/* Credibility Circle and metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '30px', marginBottom: '32px' }}>
              {/* Score circle */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRight: '1px solid #334155', paddingRight: '20px' }}>
                <div style={{ position: 'relative', width: '130px', height: '130px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg style={{ transform: 'rotate(-90deg)', width: '100%', height: '100%' }}>
                    <circle cx="65" cy="65" r="55" fill="transparent" stroke="#334155" strokeWidth="8" />
                    <circle 
                      cx="65" cy="65" r="55" fill="transparent" 
                      stroke={getRiskColor(result.decision.risk_level)} 
                      strokeWidth="8" 
                      strokeDasharray={2 * Math.PI * 55}
                      strokeDashoffset={2 * Math.PI * 55 * (1.0 - result.decision.credibility_score)}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div style={{ position: 'absolute', textAlign: 'center' }}>
                    <span style={{ fontSize: '28px', fontWeight: 800 }}>{(result.decision.credibility_score * 100).toFixed(0)}</span>
                    <span style={{ fontSize: '14px', color: '#94a3b8' }}>%</span>
                    <p style={{ fontSize: '11px', color: '#94a3b8', margin: 0, textTransform: 'uppercase' }}>신뢰도</p>
                  </div>
                </div>
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                  <span style={{ fontSize: '12px', color: '#94a3b8' }}>위험 레벨: </span>
                  <span style={{ fontWeight: 800, color: getRiskColor(result.decision.risk_level) }}>{result.decision.risk_level}</span>
                </div>
              </div>

              {/* Metrics details */}
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '14px' }}>
                    <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}><Activity size={15} /> AI 생성/합성 확률</span>
                    <span style={{ fontWeight: 700 }}>{(result.metrics.ai_generation_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', backgroundColor: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${result.metrics.ai_generation_probability * 100}%`, height: '100%', backgroundColor: '#a855f7', borderRadius: '4px' }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '14px' }}>
                    <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}><Layers size={15} /> 아티팩트/조작 오차도</span>
                    <span style={{ fontWeight: 700 }}>{(result.metrics.editing_artifact_score * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', backgroundColor: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${result.metrics.editing_artifact_score * 100}%`, height: '100%', backgroundColor: '#f97316', borderRadius: '4px' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Explanations section */}
            <div style={{ borderTop: '1px solid #334155', paddingTop: '24px', marginBottom: '24px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={18} className="text-yellow-500" /> 탐지된 어노말리 분석 근거 (XAI)
              </h4>
              
              {result.explanations.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {result.explanations.map((exp, idx) => (
                    <div key={idx} style={{
                      backgroundColor: exp.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.05)' : 'rgba(245, 158, 11, 0.05)',
                      borderLeft: `4px solid ${exp.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b'}`,
                      padding: '12px 16px',
                      borderRadius: '0 8px 8px 0',
                      display: 'flex',
                      alignItems: 'start',
                      gap: '12px'
                    }}>
                      <div style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: exp.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b',
                        color: '#0f172a',
                        marginTop: '2px'
                      }}>
                        {exp.severity}
                      </div>
                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 4px 0', color: '#e2e8f0' }}>{exp.message}</p>
                        <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>코드: {exp.code} | 영역: {exp.location}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '20px 0', fontSize: '14px' }}>
                  검증된 신뢰성 어노말리 정보가 없습니다. (정합성 완벽)
                </div>
              )}
            </div>

            {/* Back button */}
            <button
              onClick={resetForm}
              style={{
                width: '100%',
                backgroundColor: '#334155',
                color: '#f8fafc',
                border: 'none',
                borderRadius: '8px',
                padding: '12px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#475569'}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#334155'}
            >
              새로운 파일 검사하기
            </button>
          </div>
        )}
      </main>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
