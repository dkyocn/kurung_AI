import React, { useState, useEffect, useRef } from 'react';
import '../../styles/login/loginSelect.css';
import '../../styles/login/faceLogin.css';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import kakaologo from '../../images/login/kakaologo.png';
import naverlogo from '../../images/login/naverlogo.png';
import faceLogo from '../../images/login/FaceLogin.png';

function LoginSelect() {
  const navigate = useNavigate();
  
  // === Face ID 관련 상태 ===
  const [isFaceLogin, setIsFaceLogin] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState('');
  
  // === 카메라 관련 ref ===
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // === 카메라 정리 ===
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  // Face ID 로그인용 axios 인스턴스
  const faceLoginApi = axios.create({
    baseURL: 'http://localhost:8000', // FastAPI 서버
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
          localStorage.setItem('refreshToken', response.data.access_token); 
          
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
        formData.append('username', 'default_user');
        formData.append('password', 'default_password');
        formData.append('face_image', blob, 'face.jpg');

        try {
          const response = await faceLoginApi.post('/register-face', formData);
          console.log('Face ID 등록 성공:', response.data);
          setError(''); // 에러 메시지 제거
          alert('Face ID 등록이 완료되었습니다!'); // 성공 메시지
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

  // === Face ID 로그인 핸들러 ===
  const handleFaceLogin = () => {
    setIsFaceLogin(true);
    // 약간의 지연 후 카메라 시작
    setTimeout(() => {
      startCamera();
    }, 500);
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
            /* === 기존 로그인 버튼들 (디자인 유지) === */
            <div className="login-buttons">
              <button className="login-btn kakao">
                <img src={kakaologo} alt="Kakao" className="login-icon" />
              </button>
              <button className="login-btn naver">
                <img src={naverlogo} alt="Naver" className="login-icon" />
              </button>
              <button className="login-btn school" onClick={handleFaceLogin}>
                <img src={faceLogo} alt="Face Login" className="login-icon" />
              </button>
              <Link to="/loginPage" className="login-btn mail">
                <span className="btn-text">Mail</span>
              </Link>
            </div>
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
          
          <Link to="/signupPage" className="login-bottom-text">이메일로 회원가입</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginSelect; 