
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export const useTimeout = (timeoutMinutes: number = 20) => {
  const navigate = useNavigate();
  const timeoutRef = useRef<NodeJS.Timeout>();
  const warningRef = useRef<NodeJS.Timeout>();

  const resetTimeout = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (warningRef.current) {
      clearTimeout(warningRef.current);
    }

    // Set warning at 18 minutes (2 minutes before timeout)
    warningRef.current = setTimeout(() => {
      const shouldStayLoggedIn = window.confirm(
        'Your session will expire in 2 minutes. Click OK to stay logged in.'
      );
      
      if (shouldStayLoggedIn) {
        resetTimeout();
      }
    }, (timeoutMinutes - 2) * 60 * 1000);

    // Set actual timeout
    timeoutRef.current = setTimeout(() => {
      alert('Your session has expired. You will be redirected to the login page.');
      navigate('/login');
    }, timeoutMinutes * 60 * 1000);
  };

  useEffect(() => {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    const resetTimeoutHandler = () => {
      resetTimeout();
    };

    // Set initial timeout
    resetTimeout();

    // Add event listeners
    events.forEach(event => {
      document.addEventListener(event, resetTimeoutHandler, true);
    });

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (warningRef.current) {
        clearTimeout(warningRef.current);
      }
      events.forEach(event => {
        document.removeEventListener(event, resetTimeoutHandler, true);
      });
    };
  }, [navigate, timeoutMinutes]);
};
