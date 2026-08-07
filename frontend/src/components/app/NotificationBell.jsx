"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useAlertCenter } from "../../context/AlertCenterContext.jsx";
import AppIcon from "./AppIcon.jsx";

function recency(value) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Recently";
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return new Date(value).toLocaleDateString("en-AU", { day: "numeric", month: "short" });
}

function NotificationContent({ alert }) {
  return (
    <>
      <span className="notification-item__heading"><strong>{alert.title}</strong><span className={`severity-badge severity-badge--${String(alert.severity || "unavailable").toLowerCase()}`}>{alert.severity || "Unavailable"}</span></span>
      <span className="notification-item__area">{alert.area || "Melbourne CBD"}</span>
      {alert.type === "predictive" && alert.confidence ? <span>Confidence: {alert.confidence}</span> : null}
      <small>{recency(alert.timestamp)}</small>
    </>
  );
}

export default function NotificationBell() {
  const { notifications, markAllRead, selectAlert } = useAlertCenter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);
  const unread = notifications.filter((notification) => !notification.read).length;

  useEffect(() => {
    if (!open) return undefined;
    function closeOnOutsideClick(event) {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    }
    function closeOnEscape(event) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  function chooseAlert(alert) {
    selectAlert(alert.id);
    setOpen(false);
    if (alert.active && alert.affectsCurrentRoute) {
      window.dispatchEvent(new globalThis.CustomEvent("escape:select-alert", { detail: { alertId: alert.id } }));
    }
  }

  return (
    <div className="notification-center" ref={containerRef}>
      <button
        type="button"
        className="notification-bell"
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        aria-controls="notification-dropdown"
        onClick={() => setOpen((current) => !current)}
        ref={buttonRef}
      >
        <AppIcon name="bell" size={24} />
        {unread ? <span className="notification-badge">{unread > 9 ? "9+" : unread}</span> : null}
      </button>
      {open ? (
        <section className="notification-dropdown" id="notification-dropdown" aria-labelledby="notification-heading">
          <header><h2 id="notification-heading">Notifications</h2>{unread ? <button type="button" onClick={markAllRead}>Mark all as read</button> : null}</header>
          {notifications.length ? (
            <div className="notification-list">
              {notifications.slice(0, 8).map((alert) => {
                const actionable = alert.active && alert.affectsCurrentRoute;
                const className = `notification-item ${alert.read ? "notification-item--read" : ""}`;
                return actionable ? (
                  <Link key={alert.id} className={className} href={`/plan?view=trip&alert=${encodeURIComponent(alert.id)}`} onClick={() => chooseAlert(alert)}>
                    <NotificationContent alert={alert} />
                  </Link>
                ) : (
                  <button key={alert.id} type="button" className={className} onClick={() => chooseAlert(alert)}>
                    <NotificationContent alert={alert} />
                  </button>
                );
              })}
            </div>
          ) : <p className="notification-empty">No notifications yet.</p>}
        </section>
      ) : null}
    </div>
  );
}
