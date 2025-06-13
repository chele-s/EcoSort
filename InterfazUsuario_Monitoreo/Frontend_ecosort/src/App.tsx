import { Route, Routes } from 'react-router-dom';
import Dashboard from './pages/Dashboard.tsx';
import Analytics from './pages/Analytics.tsx';
import Control from './pages/Control.tsx';
import Login from './pages/Login.tsx';
import Layout from './components/Layout';
import { AuthProvider, RequireAuth } from './hooks/useAuth';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route 
          path="/" 
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="control" element={<Control />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;
