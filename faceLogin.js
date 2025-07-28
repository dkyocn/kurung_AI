import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import '../../styles/login/loginPage.css';

function LoginPage() {

  // === 상태 관리 및 네비게이션 ===
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isFaceLogin, setIsFaceLogin] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const navigate = useNavigate();
  
  // === 카메라 관련 ref ===
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // === 로그인 페이지 접속 시 만료된 토큰 제거 ===
  useEffect(() => {
    // 로그인 페이지에 접속할 때 기존 토큰 제거
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    console.log('로그인 페이지: 기존 토큰 제거됨');
  }, []);

  // === 카메라 정리 ===
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  // 로그인용 axios 인스턴스 (baseURL 직접 지정)
  const loginApi = axios.create({
    baseURL: 'http://localhost:8081',
    headers: {
      'Content-Type': 'application/json',
    },
    withCredentials: true,
  });

  // Face ID 로그인용 axios 인스턴스
  const faceLoginApi = axios.create({
    baseURL: 'http://localhost:8000', // FastAPI 서버
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  // === 카메라 시작 ===
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: 640, 
          height: 480,
          facingMode: 'user' // 전면 카메라 사용
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setIsCameraOn(true);
      }
    } catch (err) {
      console.error('카메라 접근 오류:', err);
      setError('카메라에 접근할 수 없습니다. 카메라 권한을 확인해주세요.');
    }
  };

  // === 카메라 중지 ===
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraOn(false);
    setIsFaceLogin(false);
  };

  // === 얼굴 촬영 및 로그인 ===
  const captureAndLogin = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    setIsCapturing(true);
    setError('');

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      // 비디오 크기에 맞춰 캔버스 설정
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // 현재 비디오 프레임을 캔버스에 그리기
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // 캔버스에서 이미지 데이터를 Blob으로 변환
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setError('이미지 캡처에 실패했습니다.');
          setIsCapturing(false);
          return;
        }

        // FormData 생성
        const formData = new FormData();
        formData.append('face_image', blob, 'face.jpg');

        // Face ID 로그인 API 호출
        try {
          const response = await faceLoginApi.post('/login-face', formData);
          
          // JWT 토큰 저장
          localStorage.setItem('accessToken', response.data.access_token);
          localStorage.setItem('refreshToken', response.data.access_token); // 임시로 같은 토큰 사용
          
          console.log('Face ID 로그인 성공:', response.data);
          stopCamera();
          navigate('/main');
          
        } catch (err) {
          console.error('Face ID 로그인 오류:', err);
          
          let errorMessage = 'Face ID 로그인에 실패했습니다.';
          
          if (err.response?.data?.detail) {
            const serverError = err.response.data.detail;
            if (serverError.includes('얼굴을 찾을 수 없습니다')) {
              errorMessage = '얼굴이 감지되지 않았습니다. 카메라를 정면으로 바라보세요.';
            } else if (serverError.includes('등록되지 않은 얼굴입니다')) {
              errorMessage = '등록되지 않은 얼굴입니다. 먼저 Face ID를 등록해주세요.';
            } else {
              errorMessage = serverError;
            }
          } else if (err.response?.status === 401) {
            errorMessage = '등록되지 않은 얼굴입니다. 먼저 Face ID를 등록해주세요.';
          } else if (err.response?.status === 500) {
            errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
          } else if (err.code === 'ERR_NETWORK') {
            errorMessage = 'Face ID 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
          }
          
          setError(errorMessage);
        }
        
        setIsCapturing(false);
      }, 'image/jpeg', 0.8);

    } catch (err) {
      console.error('이미지 캡처 오류:', err);
      setError('이미지 캡처 중 오류가 발생했습니다.');
      setIsCapturing(false);
    }
  };

  // === Face ID 등록 ===
  const registerFaceId = async () => {
    if (!videoRef.current || !canvasRef.current) return;

    setIsCapturing(true);
    setError('');

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(async (blob) => {
        if (!blob) {
          setError('이미지 캡처에 실패했습니다.');
          setIsCapturing(false);
          return;
        }

        const formData = new FormData();
        formData.append('username', email || 'default_user');
        formData.append('password', password || 'default_password');
        formData.append('face_image', blob, 'face.jpg');

        try {
          const response = await faceLoginApi.post('/register-face', formData);
          console.log('Face ID 등록 성공:', response.data);
          setError('Face ID 등록이 완료되었습니다!');
          stopCamera();
          
        } catch (err) {
          console.error('Face ID 등록 오류:', err);
          
          let errorMessage = 'Face ID 등록에 실패했습니다.';
          
          if (err.response?.data?.detail) {
            errorMessage = err.response.data.detail;
          } else if (err.code === 'ERR_NETWORK') {
            errorMessage = 'Face ID 서버에 연결할 수 없습니다.';
          }
          
          setError(errorMessage);
        }
        
        setIsCapturing(false);
      }, 'image/jpeg', 0.8);

    } catch (err) {
      console.error('Face ID 등록 오류:', err);
      setError('Face ID 등록 중 오류가 발생했습니다.');
      setIsCapturing(false);
    }
  };

  // === 기존 로그인 요청 처리 ===
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await loginApi.post('/api/v1/kurung/user/login', {
        userId: email,
        userPwd: password
      });
      localStorage.setItem('accessToken', res.data.accessToken);
      localStorage.setItem('refreshToken', res.data.refreshToken);
      navigate('/main'); // 성공 시 이동할 경로
    } catch (err) {
      console.error('로그인 오류:', err);
      
      // 더 구체적인 오류 메시지 처리
      let errorMessage = '로그인에 실패했습니다.';
      
      if (err.response?.data?.error) {
        const serverError = err.response.data.error;
        if (serverError.includes('password cannot be null')) {
          errorMessage = '비밀번호가 설정되지 않았습니다. 비밀번호 재설정을 다시 시도해주세요.';
        } else if (serverError.includes('Bad credentials')) {
          errorMessage = '아이디와 비밀번호를 다시 확인해 주세요.';
        } else if (serverError.includes('사용자를 찾을 수 없습니다')) {
          errorMessage = '존재하지 않는 사용자입니다.';
        } else {
          errorMessage = serverError;
        }
      } else if (err.response?.status === 401) {
        errorMessage = '아이디와 비밀번호를 다시 확인해 주세요.';
      } else if (err.response?.status === 500) {
        errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else if (err.code === 'ERR_NETWORK') {
        errorMessage = '서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.';
      }
      
      setError(errorMessage);
    }
  };

  return (
    <div className="page-outer">
      <div className="page-inner">
        <div className="login-box">
          <h1 className="login-title">KURUNG</h1>
          <p className="login-subtitle">Welcome to Wellbeing Hub</p>
          
          {/* === Face ID 로그인 섹션 === */}
          {isFaceLogin ? (
            <div className="face-login-section">
              <div className="camera-container">
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted
                  className="camera-video"
                />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
              </div>
              
              <div className="face-login-buttons">
                {!isCameraOn ? (
                  <button 
                    className="face-login-btn" 
                    onClick={startCamera}
                  >
                    카메라 시작
                  </button>
                ) : (
                  <>
                    <button 
                      className="face-login-btn primary" 
                      onClick={captureAndLogin}
                      disabled={isCapturing}
                    >
                      {isCapturing ? '인식 중...' : 'Face ID 로그인'}
                    </button>
                    <button 
                      className="face-login-btn secondary" 
                      onClick={registerFaceId}
                      disabled={isCapturing}
                    >
                      Face ID 등록
                    </button>
                    <button 
                      className="face-login-btn cancel" 
                      onClick={stopCamera}
                    >
                      취소
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            /* === 기존 로그인 폼 === */
            <form className="login-form" onSubmit={handleSubmit}>
              <input
                className="login-input"
                type="text"
                placeholder="Email"
                autoComplete="username"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
              <input
                className="login-input"
                type="password"
                placeholder="Password"
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <button className="login-btn-submit" type="submit">Log In</button>
              
              {/* === Face ID 로그인 버튼 === */}
              <button 
                type="button"
                className="face-login-toggle-btn"
                onClick={() => setIsFaceLogin(true)}
              >
                Face ID로 로그인
              </button>
            </form>
          )}
          
          {/* === 에러 메시지 표시 === */}
          {error && <div className="login-error">{error}</div>}
          
          {/* === 일반 로그인으로 돌아가기 === */}
          {isFaceLogin && (
            <button 
              className="back-to-login-btn"
              onClick={() => {
                stopCamera();
                setIsFaceLogin(false);
                setError('');
              }}
            >
              일반 로그인으로 돌아가기
            </button>
          )}
          
          <Link to="/passwordReset" className="login-bottom-text">비밀번호 재설정</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginPage; 