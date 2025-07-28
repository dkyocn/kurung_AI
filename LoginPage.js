import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import '../../styles/login/loginPage.css';

function LoginPage() {

  // === 상태 관리 및 네비게이션 ===
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // === 로그인 페이지 접속 시 만료된 토큰 제거 ===
  useEffect(() => {
    // 로그인 페이지에 접속할 때 기존 토큰 제거
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    console.log('로그인 페이지: 기존 토큰 제거됨');
  }, []);

  // 로그인용 axios 인스턴스 (baseURL 직접 지정)
  const loginApi = axios.create({
    baseURL: 'http://localhost:8081',
    headers: {
      'Content-Type': 'application/json',
    },
    withCredentials: true,
  });

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
          {/* === 폼에 상태 연결 === */}
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
          </form>
          {/* === 에러 메시지 표시 === */}
          {error && <div className="login-error">{error}</div>}
          <Link to="/passwordReset" className="login-bottom-text">비밀번호 재설정</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginPage; 