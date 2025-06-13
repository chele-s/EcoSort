import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import styles from './Login.module.css';
import React from 'react';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    // In a real app, you'd handle form data and API calls
    // For this demo, we'll just log in with a fake token.
    const fakeToken = 'ecosort-jwt-token-12345';

    auth.login(fakeToken, () => {
      navigate(from, { replace: true });
    });
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard}>
        <div className={styles.logo}>
          <h1>EcoSort</h1>
          <p>Industrial AI Waste Sorting</p>
        </div>
        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.inputGroup}>
            <label htmlFor="username">Username</label>
            <input type="text" id="username" defaultValue="operator" required />
          </div>
          <div className={styles.inputGroup}>
            <label htmlFor="password">Password</label>
            <input type="password" id="password" defaultValue="password" required />
          </div>
          <button type="submit" className="btn btn-primary">
            Secure Login
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login; 