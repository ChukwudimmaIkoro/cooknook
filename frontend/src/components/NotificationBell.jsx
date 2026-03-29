import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Bell, X, Check, CheckCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import {
  getNotifications, markNotificationRead,
  markAllNotificationsRead, dismissNotification,
} from '../services/api';

const NotificationBell = () => {
  const { isAuthenticated, token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  const load = useCallback(async () => {
    if (!isAuthenticated || !token) return;
    try { setNotifications(await getNotifications(token)); }
    catch { /* silent */ }
  }, [isAuthenticated, token]);

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [load]);

  // FIX: close on outside click
  useEffect(() => {
    const handler = e => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!isAuthenticated) return null;

  const unread = notifications.filter(n => !n.read).length;

  const handleMarkRead = async (id) => {
    await markNotificationRead(token, id);
    setNotifications(prev => prev.map(n => n.id === id ? {...n, read: true} : n));
  };

  const handleDismiss = async (id) => {
    await dismissNotification(token, id);
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleMarkAll = async () => {
    await markAllNotificationsRead(token);
    setNotifications(prev => prev.map(n => ({...n, read: true})));
  };

  return (
    <div className="notification-bell-wrapper" ref={wrapperRef}>
      <button className="notification-bell-btn" onClick={() => { setOpen(v => !v); }}
        aria-label="Notifications">
        <Bell size={22}/>
        {unread > 0 && <span className="notification-dot"/>}
      </button>

      {open && (
        <div className="notification-dropdown">
          <div className="notification-dropdown-header">
            <strong>Notifications</strong>
            {unread > 0 && (
              <button className="mark-all-btn" onClick={handleMarkAll}>
                <CheckCheck size={14}/> Mark all read
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <p className="notification-empty">No notifications yet</p>
          ) : (
            notifications.map(n => (
              <div key={n.id} className={`notification-item ${n.read ? 'read' : 'unread'}`}>
                <div className="notification-body">
                  <p className="notification-title">{n.title}</p>
                  <p className="notification-message">{n.message}</p>
                </div>
                <div className="notification-item-actions">
                  {!n.read && (
                    <button className="icon-btn confirm" onClick={() => handleMarkRead(n.id)}
                      title="Mark as read"><Check size={13}/></button>
                  )}
                  <button className="icon-btn delete" onClick={() => handleDismiss(n.id)}
                    title="Dismiss"><X size={13}/></button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;