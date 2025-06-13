import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import styles from './Layout.module.css';
import { useAuth } from '../hooks/useAuth';

const Layout = () => {
  const auth = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    auth.logout(() => navigate('/login'));
  };

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h1 className={styles.logo}>EcoSort</h1>
        </div>
        <nav className={styles.nav}>
          <NavLink to="/" className={({isActive}) => isActive ? styles.activeLink : styles.navLink}>Dashboard</NavLink>
          <NavLink to="/analytics" className={({isActive}) => isActive ? styles.activeLink : styles.navLink}>Analytics</NavLink>
          <NavLink to="/control" className={({isActive}) => isActive ? styles.activeLink : styles.navLink}>System Control</NavLink>
        </nav>
        <div className={styles.sidebarFooter}>
            <button onClick={handleLogout} className={styles.logoutButton}>
                Logout
            </button>
        </div>
      </aside>
      <main className={styles.mainContent}>
        <Outlet />
      </main>
    </div>
  );
};

export default Layout; 